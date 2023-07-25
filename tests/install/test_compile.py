#!/usr/bin/python3

import os

import pytest

import ethcx
from ethcx.exceptions import CompilerInstallationError


@pytest.mark.skipif("sys.platform != 'win32'")
def test_fails_on_windows():
    with pytest.raises(OSError):
        ethcx.compile_solc("latest")


@pytest.mark.skipif("sys.platform == 'win32'")
def test_compile_already_installed():
    version = ethcx.get_installed_solc_versions()[0]
    assert ethcx.compile_solc("latest") == version


@pytest.mark.skipif("sys.platform == 'win32'")
def test_compile(compile_mock, solc_binary, cwd):
    version = ethcx.wrapper._get_solc_version(solc_binary)
    ethcx.compile_solc(version)

    assert os.getcwd() == cwd
    assert ethcx.get_installed_solc_versions() == [version]


@pytest.mark.skipif("sys.platform == 'win32'")
def test_compile_install_deps_fails(compile_mock, solc_binary, cwd):
    version = ethcx.wrapper._get_solc_version(solc_binary)
    compile_mock.raise_on("sh")
    ethcx.compile_solc(version)

    assert os.getcwd() == cwd
    assert ethcx.get_installed_solc_versions() == [version]


@pytest.mark.skipif("sys.platform == 'win32'")
def test_compile_install_cmake_fails(compile_mock, solc_binary, cwd):
    compile_mock.raise_on("cmake")
    with pytest.raises(CompilerInstallationError):
        ethcx.compile_solc("latest")

    assert os.getcwd() == cwd


@pytest.mark.skipif("sys.platform == 'win32'")
def test_compile_install_make_fails(compile_mock, solc_binary, cwd):
    compile_mock.raise_on("make")
    with pytest.raises(CompilerInstallationError):
        ethcx.compile_solc("latest")

    assert os.getcwd() == cwd
