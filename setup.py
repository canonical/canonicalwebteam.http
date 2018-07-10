#! /usr/bin/env python3

# Core
from setuptools import setup, find_packages

setup(
    name='canonicalwebteam.http',
    version='0.1.4',
    author='Canonical webteam',
    author_email='webteam@canonical.com',
    url='https://github.com/canonicalwebteam/http',
    packages=find_packages(),
    description=(
        "For making HTTP requests "
        "with helpful defaults for Canonical's webteam."
    ),
    long_description=open('README.rst').read(),
    install_requires=[
        "requests>=2.10.0",
    ],
)
