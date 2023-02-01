import ast
from typing import Any, Iterable

VERSION = "0.1.0"
PYDANTIC_MODEL_BASES = ["BaseModel", "GenericModel"]
VALIDATOR_DECORATOR_NAMES = ["validator", "root_validator"]
ERRORS = {
    "PYD001": "PYD001 Found a Pydantic field which has no default",
    "PYD002": "PYD002 Found a Pydantic field which has a default that is not a Field",
    "PYD003": "PYD003 Found a Pydantic field which has a Field default with no description",
    "PYD004": "PYD004 Found a Pydantic field which has a Field default with an empty description",
}


def has_dataclass_decorator(*, classdef: ast.ClassDef) -> bool:
    return any(
        decorator.name == "dataclass"
        if isinstance(decorator, ast.Name)
        else decorator.attr == "dataclass"
        for decorator in classdef.decorator_list
    )


def has_base_class(*, classdef: ast.ClassDef) -> bool:
    """Must have at least a base class to be a candidate to be a data model."""
    return len(classdef.bases) > 0


def base_class_indicates_pydantic(*, classdef: ast.ClassDef) -> bool:
    """If the base class is obviously from Pydantic, it is."""
    return any(
        pydantic_model_base in base.id
        for pydantic_model_base in PYDANTIC_MODEL_BASES
        for base in classdef.bases
    )


def class_contains_only_annassign(*, classdef: ast.ClassDef) -> bool:
    """If a class has no methods, it must be a data model."""
    return all(isinstance(node, ast.AnnAssign) for node in classdef.body)


def has_inner_config_class(*, classdef: ast.ClassDef) -> bool:
    """If a class has an inner Config class, it must be Pydantic."""
    return any(
        isinstance(attribute, ast.ClassDef) and attribute.name == "Config"
        for attribute in classdef.body
    )


def has_validator_method(*, classdef: ast.ClassDef) -> bool:
    """If a class has a method which is decorated
    with @validator or @root_validator, it must be Pydantic.
    """
    for attribute in classdef.body:
        if not isinstance(attribute, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in attribute.decorator_list:
            if (
                isinstance(decorator, ast.Name)
                and decorator.id in VALIDATOR_DECORATOR_NAMES
            ):
                return True
            if (
                isinstance(decorator, ast.Attribute)
                and decorator.attr in VALIDATOR_DECORATOR_NAMES
            ):
                return True
            if (
                isinstance(decorator, ast.Call)
                and isinstance(decorator.func, ast.Attribute)
                and decorator.func.attr in VALIDATOR_DECORATOR_NAMES
            ):
                return True
            if (
                isinstance(decorator, ast.Call)
                and isinstance(decorator.func, ast.Name)
                and decorator.func.id in VALIDATOR_DECORATOR_NAMES
            ):
                return True

    return False


def has_init(*, classdef: ast.ClassDef) -> bool:
    """If a class has an __init__ method, it is not a data model."""
    for attribute in classdef.body:
        if (
            isinstance(attribute, (ast.FunctionDef, ast.AsyncFunctionDef))
            and attribute.name == "__init__"
        ):
            return True

    return False


class PydanticFieldChecker(ast.NodeVisitor):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.current_class_is_candidate = False
        self.errors: list[tuple[int, int, str]] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.current_class_is_candidate = (
            has_base_class(classdef=node)
            and (
                base_class_indicates_pydantic(classdef=node)
                or class_contains_only_annassign(classdef=node)
                or has_validator_method(classdef=node)
                or has_inner_config_class(classdef=node)
            )
            and not (has_init(classdef=node) or has_dataclass_decorator(classdef=node))
        )
        self.generic_visit(node)
        self.current_class_is_candidate = False

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if self.current_class_is_candidate:
            if node.value is None:
                self.errors.append(
                    (
                        node.lineno,
                        node.col_offset,
                        ERRORS["PYD001"],
                    )
                )
            elif (
                isinstance(node.value, ast.Call)
                and node.value.func.id.lower() != "field"
            ) or not isinstance(node.value, ast.Call):
                self.errors.append(
                    (
                        node.lineno,
                        node.col_offset,
                        ERRORS["PYD002"],
                    )
                )
            elif (
                isinstance(node.value, ast.Call)
                and node.value.func.id.lower() == "field"
                and not any(
                    keyword.arg == "description" for keyword in node.value.keywords
                )
            ):
                self.errors.append(
                    (
                        node.lineno,
                        node.col_offset,
                        ERRORS["PYD003"],
                    )
                )
            elif (
                isinstance(node.value, ast.Call)
                and node.value.func.id.lower() == "field"
                and any(
                    keyword.arg == "description" and keyword.value.value == ""
                    for keyword in node.value.keywords
                )
            ):
                self.errors.append(
                    (
                        node.lineno,
                        node.col_offset,
                        ERRORS["PYD004"],
                    )
                )

        self.generic_visit(node)


class Plugin:
    name = "flake8-has-docstring"
    version = VERSION

    def __init__(self, tree: ast.Module) -> None:
        self.tree = tree

    def run(self) -> Iterable[tuple[int, int, str, str]]:
        visitor = PydanticFieldChecker()
        visitor.visit(self.tree)

        for line, col, msg in visitor.errors:
            yield line, col, msg, ""
