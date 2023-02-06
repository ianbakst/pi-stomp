from setuptools import find_namespace_packages, setup


setup(
    name="pistomp",
    version="0.1.0",
    author="Ian Bakst",
    author_email="ianbakst@gmail.com",
    description="",
    long_description_content_type="text/markdown",
    packages=find_namespace_packages(),
    include_package_data=True,
    package_data={'': ['static/images/*.csv']},
    python_requires=">=3.9",
)
