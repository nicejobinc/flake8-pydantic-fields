import ast
import inspect

from flake8_pydantic_fields import Plugin


def test_fields_with_descriptions_no_errors() -> None:
    source = inspect.cleandoc(
        """
        class MyModel(BaseModel):
            foo: str = Field(..., description="foo")
            bar: str = Field(..., description="bar")
        """
    )
    plugin = Plugin(ast.parse(source))
    result = list(plugin.run())

    assert result == []


def test_field_with_no_default_errors() -> None:
    source = inspect.cleandoc(
        """
        class MyModel(BaseModel):
            foo: str = Field(..., description="foo")
            bar: str
        """
    )
    plugin = Plugin(ast.parse(source))
    result = list(plugin.run())

    assert result == [
        (
            3,
            4,
            "PYD001 Found a Pydantic field which has no default",
            "",
        ),
    ]


def test_field_with_non_field_default_errors() -> None:
    source = inspect.cleandoc(
        """
        class MyModel(BaseModel):
            foo: str = Field(..., description="foo")
            bar: str = "bar"
        """
    )
    plugin = Plugin(ast.parse(source))
    result = list(plugin.run())

    assert result == [
        (
            3,
            4,
            "PYD002 Found a Pydantic field which has a default that is not a Field",
            "",
        ),
    ]


def test_field_with_missing_description_errors() -> None:
    source = inspect.cleandoc(
        """
        class MyModel(BaseModel):
            foo: str = Field(..., description="foo")
            bar: str = Field(...)
        """
    )
    plugin = Plugin(ast.parse(source))
    result = list(plugin.run())

    assert result == [
        (
            3,
            4,
            "PYD003 Found a Pydantic field which has a Field default with no description",
            "",
        ),
    ]


def test_field_with_empty_description_errors() -> None:
    source = inspect.cleandoc(
        """
        class MyModel(BaseModel):
            foo: str = Field(..., description="foo")
            bar: str = Field(..., description="")
        """
    )
    plugin = Plugin(ast.parse(source))
    result = list(plugin.run())

    assert result == [
        (
            3,
            4,
            "PYD004 Found a Pydantic field which has a Field default with an empty description",
            "",
        ),
    ]


def test_generic_model_identified() -> None:
    source = inspect.cleandoc(
        """
        class MyModel(GenericModel):
            foo: str = Field(..., description="foo")
            bar: str
        """
    )
    plugin = Plugin(ast.parse(source))
    result = list(plugin.run())

    assert result == [
        (
            3,
            4,
            "PYD001 Found a Pydantic field which has no default",
            "",
        ),
    ]


def test_no_base_class_disregarded() -> None:
    source = inspect.cleandoc(
        """
        class MyModel:
            foo: str = Field(..., description="foo")
            bar: str
        """
    )
    plugin = Plugin(ast.parse(source))
    result = list(plugin.run())

    assert result == []


def test_dataclass_disregarded() -> None:
    source = inspect.cleandoc(
        """
        @dataclass
        class MyModel:
            foo: str = Field(..., description="foo")
            bar: str
        """
    )
    plugin = Plugin(ast.parse(source))
    result = list(plugin.run())

    assert result == []


def test_custom_base_class_no_methods_identified() -> None:
    source = inspect.cleandoc(
        """
        class MyModel(MyBase):
            foo: str = Field(..., description="foo")
            bar: str
        """
    )
    plugin = Plugin(ast.parse(source))
    result = list(plugin.run())

    assert result == [
        (
            3,
            4,
            "PYD001 Found a Pydantic field which has no default",
            "",
        ),
    ]


def test_custom_base_class_with_validators_identified() -> None:
    source = inspect.cleandoc(
        """
        class MyModel(MyBase):
            foo: str = Field(..., description="foo")
            bar: str

            @validator("foo")
            def f(cls, v):
                return v
        """
    )
    plugin = Plugin(ast.parse(source))
    result = list(plugin.run())

    assert result == [
        (
            3,
            4,
            "PYD001 Found a Pydantic field which has no default",
            "",
        ),
    ]


def test_custom_base_class_with_pydantic_validators_identified() -> None:
    source = inspect.cleandoc(
        """
        class MyModel(MyBase):
            foo: str = Field(..., description="foo")
            bar: str

            @pydantic.validator("foo")
            def f(cls, v):
                return v
        """
    )
    plugin = Plugin(ast.parse(source))
    result = list(plugin.run())

    assert result == [
        (
            3,
            4,
            "PYD001 Found a Pydantic field which has no default",
            "",
        ),
    ]


def test_custom_base_class_with_config_class_identified() -> None:
    source = inspect.cleandoc(
        """
        class MyModel(MyBase):
            foo: str = Field(..., description="foo")
            bar: str

            class Config:
                pass
        """
    )
    plugin = Plugin(ast.parse(source))
    result = list(plugin.run())

    assert result == [
        (
            3,
            4,
            "PYD001 Found a Pydantic field which has no default",
            "",
        ),
    ]


def test_custom_base_class_with_config_class_identified() -> None:
    source = inspect.cleandoc(
        """
        class MyModel(MyBase):
            foo: str = Field(..., description="foo")
            bar: str

            class Config:
                pass
        """
    )
    plugin = Plugin(ast.parse(source))
    result = list(plugin.run())

    assert result == [
        (
            3,
            4,
            "PYD001 Found a Pydantic field which has no default",
            "",
        ),
    ]
