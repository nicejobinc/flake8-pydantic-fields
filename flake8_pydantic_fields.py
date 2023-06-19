import ast
from typing import Any, Iterable

VERSION = "0.1.9"
PYDANTIC_MODEL_BASES = ["BaseModel", "GenericModel"]
VALIDATOR_DECORATOR_NAMES = ["validator", "root_validator"]
ERRORS = {
    "PF001": "PF001 Found a Pydantic field which has no default",
    "PF002": "PF002 Found a Pydantic field which has a default that is not a Field",
    "PF003": "PF003 Found a Pydantic field which has a Field default with no description",
    "PF004": "PF004 Found a Pydantic field which has a Field default with an empty description",
}


def has_dataclass_decorator(*, classdef: ast.ClassDef) -> bool:
    for decorator in classdef.decorator_list:
        if isinstance(decorator, ast.Name):
            if decorator.id == "dataclass":
                return True
        elif isinstance(decorator, ast.Attribute):
            if decorator.attr == "dataclass":
                return True

    return False


def has_base_class(*, classdef: ast.ClassDef) -> bool:
    """Must have at least a base class to be a candidate to be a data model."""
    return len(classdef.bases) > 0


def base_class_indicates_pydantic(*, classdef: ast.ClassDef) -> bool:
    """If the base class is obviously from Pydantic, it is."""
    return any(
        pydantic_model_base in base.id
        for pydantic_model_base in PYDANTIC_MODEL_BASES
        for base in classdef.bases
        if isinstance(base, ast.Name)
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


def no_methods_have_arguments(*, classdef: ast.ClassDef) -> bool:
    """If a class has no methods with arguments, it must be a data model."""
    for attribute in classdef.body:
        if isinstance(attribute, (ast.FunctionDef, ast.AsyncFunctionDef)):
            non_self_args = [
                arg for arg in attribute.args.args if arg.arg != "self"
            ]
            if len(non_self_args) > 0:
                return False

    return True


def has_classvar_attribute(*, classdef: ast.ClassDef) -> bool:
    """If a class has a ClassVar attribute, it must be Pydantic."""
    return any(
        isinstance(attribute, ast.AnnAssign)
        and isinstance(attribute.annotation, ast.Subscript)
        and isinstance(attribute.annotation.value, ast.Name)
        and attribute.annotation.value.id.startswith("ClassVar")
        or isinstance(attribute, ast.AnnAssign)
        and isinstance(attribute.annotation, ast.Name)
        and attribute.annotation.id.startswith("ClassVar")
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


def has_relationship_default(*, classdef: ast.ClassDef) -> bool:
    """If a class has an attribute whose default is a Relationship, then it is likely SQLAlchemy."""
    for attribute in classdef.body:
        if (
            isinstance(attribute, ast.AnnAssign)
            and isinstance(attribute.value, ast.Call)
            and isinstance(attribute.value.func, ast.Name)
            and attribute.value.func.id == "Relationship"
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


def is_typeddict(*, classdef: ast.ClassDef) -> bool:
    """If a class has a TypedDict base class, it is not a data model."""
    return any(
        isinstance(base, ast.Name) and base.id == "TypedDict"
        for base in classdef.bases
    )


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
                or has_classvar_attribute(classdef=node)
                or no_methods_have_arguments(classdef=node)
            )
            and not (
                has_init(classdef=node)
                or has_dataclass_decorator(classdef=node)
                or has_relationship_default(classdef=node)
                or is_typeddict(classdef=node)
            )
        )
        self.generic_visit(node)
        self.current_class_is_candidate = False

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.current_class_is_candidate = False

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.current_class_is_candidate = False

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        is_classvar = (
            isinstance(node.annotation, ast.Subscript)
            and isinstance(node.annotation.value, ast.Name)
            and node.annotation.value.id.startswith("ClassVar")
        ) or (isinstance(node.annotation, ast.Name) and node.annotation.id == "ClassVar")

        is_privateattr = (
            isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Name)
            and node.value.func.id == "PrivateAttr"
        )

        if self.current_class_is_candidate and not is_classvar and not is_privateattr:
            if node.value is None:
                self.errors.append(
                    (
                        node.lineno,
                        node.col_offset,
                        ERRORS["PF001"],
                    )
                )
            elif (
                isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Name)
                and node.value.func.id.lower() != "field"
            ) or not isinstance(node.value, ast.Call):
                self.errors.append(
                    (
                        node.lineno,
                        node.col_offset,
                        ERRORS["PF002"],
                    )
                )
            elif (
                isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Name)
                and node.value.func.id.lower() == "field"
                and not any(
                    keyword.arg == "description" for keyword in node.value.keywords
                )
            ):
                self.errors.append(
                    (
                        node.lineno,
                        node.col_offset,
                        ERRORS["PF003"],
                    )
                )
            elif (
                isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Name)
                and node.value.func.id.lower() == "field"
                and any(
                    keyword.arg == "description"
                    and isinstance(keyword.value, ast.Constant)
                    and keyword.value.value == ""
                    for keyword in node.value.keywords
                )
            ):
                self.errors.append(
                    (
                        node.lineno,
                        node.col_offset,
                        ERRORS["PF004"],
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
