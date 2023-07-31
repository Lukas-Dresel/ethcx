#!/usr/bin/env python

from setuptools import find_packages, setup

with open("README.md") as readme_file:
    readme = readme_file.read()
setup(
    name="ethcx",
    version="0.0.1",  # don't change this manually, use bumpversion instead
    description="Python wrapper and version management tool for ethereum-targeting compilers.",
    long_description=readme,
    author="Lukas Dresel (forked from py-solc-x by Ben Hause)",
    author_email="Lukas-Dresel@users.noreply.github.com",
    url="https://github.com/ethpwn/ethcx",
    include_package_data=True,
    py_modules=["ethcx"],
    setup_requires=["setuptools-markdown"],
    python_requires=">=3.6, <4",
    install_requires=["requests>=2.19.0,<3", "semantic_version>=2.8.1,<3"],
    license="MIT",
    zip_safe=False,
    keywords="ethereum solidity solc vyper",
    packages=find_packages(exclude=["tests", "tests.*"]),
    classifiers=[
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ],
)
