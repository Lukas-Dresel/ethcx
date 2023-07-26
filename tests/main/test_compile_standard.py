#!/usr/bin/python3

from pathlib import Path

import pytest

import ethcx
from ethcx.exceptions import ContractsNotFound, CompilationError


@pytest.fixture
def input_json(all_versions):
    json = {
        "language": "Solidity",
        "sources": {},
        "settings": {"outputSelection": {"*": {"*": ["evm.bytecode.object"]}}},
    }
    yield json


def _compile_assertions(output_json, *contract_names):
    assert isinstance(output_json, dict)
    assert "contracts" in output_json
    contracts = output_json["contracts"]
    for key in contract_names:
        assert int(contracts[f"contracts/{key}.sol"][key]["evm"]["bytecode"]["object"], 16)


def test_compile_standard(input_json, foo_source):
    input_json["sources"] = {"contracts/Foo.sol": {"content": foo_source}}
    result = ethcx.compile_solidity_standard(input_json)

    _compile_assertions(result, "Foo")


def test_compile_standard_invalid_source(input_json, invalid_source):
    input_json["sources"] = {"contracts/Foo.sol": {"content": invalid_source}}
    with pytest.raises(CompilationError):
        ethcx.compile_solidity_standard(input_json)


def test_compile_standard_with_dependency(input_json, foo_source, bar_source):
    input_json["sources"] = {
        "contracts/Foo.sol": {"content": foo_source},
        "contracts/Bar.sol": {"content": bar_source},
    }
    result = ethcx.compile_solidity_standard(input_json)

    _compile_assertions(result, "Foo", "Bar")


def test_compile_standard_with_file_paths(input_json, foo_path):
    input_json["sources"] = {"contracts/Foo.sol": {"urls": [str(foo_path)]}}
    result = ethcx.compile_solidity_standard(input_json, allow_paths=[foo_path.parent])

    _compile_assertions(result, "Foo")


def test_compile_standard_empty():
    with pytest.raises(ContractsNotFound):
        ethcx.compile_solidity_standard({"language": "Solidity", "sources": {}})


def test_solc_binary(wrapper_mock, foo_source):
    wrapper_mock.expect(solc_binary=Path("path/to/solc"))
    ethcx.compile_solidity_standard({}, solc_binary=Path("path/to/solc"), allow_empty=True)


def test_solc_version(wrapper_mock, all_versions, foo_source):
    solc_binary = ethcx.install.get_executable(all_versions)
    wrapper_mock.expect(solc_binary=solc_binary)
    ethcx.compile_solidity_standard({}, solc_version=all_versions, allow_empty=True)
