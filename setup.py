#! /usr/bin/env python3

# Core
from setuptools import setup, find_packages

setup(
    name="canonicalwebteam.http",
    version="1.0.3",
    author="Canonical webteam",
    author_email="webteam@canonical.com",
    url="https://github.com/canonical-webteam/http",
    packages=find_packages(),
    description=(
        "For making HTTP requests "
        "with helpful defaults for Canonical's webteam."
    ),
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    install_requires=[
        "CacheControl>=0.12.5",
        "freezegun>=0.3.11",
        "HTTPretty>=1.0.2",
        "lockfile>=0.12.2",
        "mockredispy>=2.9.3",
        "redis>=3.0.1",
        "requests>=2.21.0",
    ],
    test_suite="tests",
)
