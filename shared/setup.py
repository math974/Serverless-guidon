"""Setup script for shared package."""
from setuptools import setup, find_packages

setup(
    name="discord-shared",
    version="1.0.0",
    description="Shared code for Discord bot services",
    packages=find_packages(),
    python_requires=">=3.8",
)

