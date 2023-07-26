=========
ethcx
=========

Python wrapper and version management tool for ethereum compilers.
Currently supported:
    - ``solc`` `Solidity <https://github.com/ethereum/solidity>`_ compiler
    - ``vyper`` `Solidity <https://github.com/vyperlang/vyper>`_ compiler

Features
========

* Full support for Solidity versions ``>=0.4.11``
* Full support for mainline Vyper versions (not beta)
* Installs on Linux, OSX and Windows
* Compiles Solidity from source on Linux and OSX

Credit
======

`ethcx <https://github.com/ethpwn/ethcx>`_ is forked from `py-solc-x <https://github.com/iamdefinitelyahuman/py-solc-x>`_, which is forked from `py-solc <https://github.com/ethereum/py-solc>`_ which was written by `Piper Merriam <https://github.com/pipermerriam>`_.

Dependencies
============

`ethcx`` allows the use of multiple versions of solc, and can install or compile them as needed. If you wish to compile from source you must first install the required `solc dependencies <https://solidity.readthedocs.io/en/latest/installing-solidity.html#building-from-source>`_.
For vyper, `ethcx` currently only supports binary installation.