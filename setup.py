from setuptools import find_namespace_packages, setup


setup(
    name="pistomp",
    version="0.1.0",
    author="Ian Bakst",
    author_email="",
    description="Custom client for MBTA subway route API.",
    long_description_content_type="text/markdown",
    packages=find_namespace_packages(),
    python_requires=">=3.8",
)
