# ethcx

[![Pypi Status](https://img.shields.io/pypi/v/ethcx.svg)](https://pypi.org/project/ethcx/) [![Build Status](https://img.shields.io/github/workflow/status/ethpwn/ethcx/ethcx%20workflow)](https://github.com/ethpwn/ethcx/actions) [![Coverage Status](https://img.shields.io/codecov/c/github/ethpwn/ethcx)](https://codecov.io/gh/ethpwn/ethcx)

Python wrapper and version management tool for compilers targetting the ethereum platform.

Currently supports the `solc` Solidity compiler and the `vyper` compiler.

Forked from [`py-solc-x`](https://github.com/iamdefinitelyahuman/py-solc-x).

## Features

* Full support for Solidity `>=0.4.11` and Vyper
* Install Solidity and Vyper on Linux, OSX and Windows
* Compile Solidity from source on Linux and OSX

## Dependencies

`ethcx` allows the use of multiple versions of solc, and can install or compile them as needed. If you wish to compile from source you must first insall the required [solc dependencies](https://solidity.readthedocs.io/en/latest/installing-solidity.html#building-from-source).

For Vyper, `ethcx` can download and install all released versions of the `vyper` compiler binaries from [Github Releases](https://github.com/vyperlang/vyper/releases).


## Installation

### From `pypi`

```bash
pip install ethcx
```

### Local (editable) install

```bash
git clone https://github.com/ethpwn/ethcx.git
cd ethcx
pip install -e .
```

## Documentation

Documentation is hosted at [Read the Docs](https://ethcx.readthedocs.io/en/latest/).

## Testing

ethcx is tested on Linux, OSX and Windows with solc versions ``>=0.4.11``.

To run the test suite:

```bash
pytest tests/
```

By default, the test suite installs all available `solc` versions for your OS. If you only wish to test against already installed versions, include the `--no-install` flag.

## Contributing

Help is always appreciated! Feel free to open an issue if you find a problem, or a pull request if you've solved an issue.

Please check out our [Contribution Guide](CONTRIBUTING.md) prior to opening a pull request.

## License

This project is licensed under the [MIT license](LICENSE).
