#!/usr/bin/python3

import pytest

import ethcx
from ethcx.exceptions import CompilerInstallationError


@pytest.mark.skipif("'--no-install' in sys.argv")
def test_install_latest():
    version = ethcx.get_installable_solc_versions()[0]
    assert ethcx.install_solc("latest") == version


def test_unknown_platform(monkeypatch):
    monkeypatch.setattr("sys.platform", "potatoOS")
    with pytest.raises(OSError):
        ethcx.install_solc()


def test_install_unknown_version():
    with pytest.raises(CompilerInstallationError):
        ethcx.install_solc("0.4.99")


@pytest.mark.skipif("'--no-install' in sys.argv")
def test_progress_bar(nosolc):
    ethcx.install_solc("0.6.9", show_progress=True)


def test_environment_var_path(monkeypatch, tmp_path):
    install_folder = ethcx.get_install_folder()
    monkeypatch.setenv("SOLCX_BINARY_PATH", tmp_path.as_posix())
    assert ethcx.get_install_folder() != install_folder

    monkeypatch.undo()
    assert ethcx.get_install_folder() == install_folder


def test_environment_var_versions(monkeypatch, tmp_path):
    versions = ethcx.get_installed_solc_versions()
    monkeypatch.setenv("SOLCX_BINARY_PATH", tmp_path.as_posix())
    assert ethcx.get_installed_solc_versions() != versions

    monkeypatch.undo()
    assert ethcx.get_installed_solc_versions() == versions


@pytest.mark.skipif("'--no-install' in sys.argv")
def test_environment_var_install(monkeypatch, tmp_path):
    assert not tmp_path.joinpath("solc-v0.6.9").exists()

    monkeypatch.setenv("SOLCX_BINARY_PATH", tmp_path.as_posix())

    ethcx.install_solc("0.6.9")
    assert tmp_path.joinpath("solc-v0.6.9").exists()
