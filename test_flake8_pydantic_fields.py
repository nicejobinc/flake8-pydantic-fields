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
            bar: str
        """
    )
    plugin = Plugin(ast.parse(source))
    result = list(plugin.run())

    assert result == [
        (
            2,
            4,
            "PF001 Found a Pydantic field which has no default",
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
            "PF002 Found a Pydantic field which has a default that is not a Field",
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
            "PF003 Found a Pydantic field which has a Field default with no description",
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
            "PF004 Found a Pydantic field which has a Field default with an empty description",
            "",
        ),
    ]


def test_classvar_skipped() -> None:
    source = inspect.cleandoc(
        """
        class MyModel(BaseModel):
            foo: ClassVar[str]
            bar: str = Field(..., description="description")
        """
    )
    plugin = Plugin(ast.parse(source))
    result = list(plugin.run())

    assert result == []


def test_privateattr_skipped() -> None:
    source = inspect.cleandoc(
        """
        class MyModel(BaseModel):
            foo: str = PrivateAttr(default=None)
            bar: str = Field(..., description="description")
        """
    )
    plugin = Plugin(ast.parse(source))
    result = list(plugin.run())

    assert result == []


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
            "PF001 Found a Pydantic field which has no default",
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


def test_typeddict_disregarded() -> None:
    source = inspect.cleandoc(
        """
        class MyModel(TypedDict):
            foo: str
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
            "PF001 Found a Pydantic field which has no default",
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
            "PF001 Found a Pydantic field which has no default",
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
            "PF001 Found a Pydantic field which has no default",
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
            "PF001 Found a Pydantic field which has no default",
            "",
        ),
    ]


def test_custom_base_class_with_config_class_with_validators_identified() -> None:
    source = inspect.cleandoc(
        """
        class MyModel(MyBase):
            foo: str = Field(..., description="foo")
            bar: str

            class Config:
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
            "PF001 Found a Pydantic field which has no default",
            "",
        ),
    ]


def test_custom_base_class_with_uninitialized_classvar_identified() -> None:
    source = inspect.cleandoc(
        """
        class MyModel(MyBase):
            baz: ClassVar[str]
            foo: str = Field(..., description="foo")
            bar: str

            def method(self) -> None:
                ...

            @property
            def myprop(self) -> str:
                return "myprop"
        """
    )
    plugin = Plugin(ast.parse(source))
    result = list(plugin.run())

    assert result == [
        (
            4,
            4,
            "PF001 Found a Pydantic field which has no default",
            "",
        ),
    ]


def test_custom_base_class_with_initialized_classvar_identified() -> None:
    source = inspect.cleandoc(
        """
        class MyModel(MyBase):
            baz: ClassVar[str] = "baz"
            foo: str = Field(..., description="foo")
            bar: str

            def method(self) -> None:
                ...

            @property
            def myprop(self) -> str:
                return "myprop"

            class Config:
                baz = "baz"
        """
    )
    plugin = Plugin(ast.parse(source))
    result = list(plugin.run())

    assert result == [
        (
            4,
            4,
            "PF001 Found a Pydantic field which has no default",
            "",
        ),
    ]


def test_custom_base_class_with_only_bare_methods_identified() -> None:
    source = inspect.cleandoc(
        """
        class MyModel(MyBase):
            foo: str = Field(..., description="foo")
            bar: str

            def method(self) -> None:
                ...

            def method2(self) -> None:
                ...
        """
    )
    plugin = Plugin(ast.parse(source))
    result = list(plugin.run())

    assert result == [
        (
            3,
            4,
            "PF001 Found a Pydantic field which has no default",
            "",
        ),
    ]


def test_annassigns_within_method_ignored() -> None:
    source = inspect.cleandoc(
        """
        class MyModel(BaseModel):
            foo: str = Field(..., description="foo")

            def method(self) -> None:
                foo: str = "foo"
                bar: str = "bar"
        """
    )
    plugin = Plugin(ast.parse(source))
    result = list(plugin.run())

    assert result == []


def test_relationship_default_disqualifies() -> None:
    source = inspect.cleandoc(
        """
        class MyModel(BaseModel):
            foo: str = Relationship()
            bar: str
        """
    )
    plugin = Plugin(ast.parse(source))
    result = list(plugin.run())

    assert result == []
