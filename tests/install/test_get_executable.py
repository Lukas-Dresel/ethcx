#!/usr/bin/python3


import pytest

import ethcx
from ethcx.exceptions import CompilerNotInstalled, UnsupportedVersionError


def test_get_executable():
    assert ethcx.install.get_executable() == ethcx.install._default_solc_binary


def test_no_default_set(nosolc):
    with pytest.raises(CompilerNotInstalled):
        ethcx.install.get_executable()


def test_unsupported_version():
    with pytest.raises(UnsupportedVersionError):
        ethcx.install.get_executable("0.4.0")


def test_version_not_installed():
    with pytest.raises(CompilerNotInstalled):
        ethcx.install.get_executable("999.999.999")
