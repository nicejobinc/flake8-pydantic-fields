from setuptools import setup

with open("requirements.txt") as f:
    install_requires = f.read().splitlines()

with open("README.md") as f:
    long_description = f.read().strip()

setup(
    name="flake8-pydantic-fields",
    version="0.1.2",
    python_requires=">=3.10,<3.11",
    install_requires=install_requires,
    py_modules=["flake8_pydantic_fields"],
    entry_points={"flake8.extension": "PF00 = flake8_pydantic_fields:Plugin"},
    long_description=long_description,
    long_description_content_type="text/markdown",
)
