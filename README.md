# pyqasm

<img align="right" width="100" src="https://qbraid-static.s3.amazonaws.com/pyqasm.svg"/>

[![CI](https://github.com/qBraid/pyqasm/actions/workflows/main.yml/badge.svg?branch=main)](https://github.com/qBraid/pyqasm/actions/workflows/main.yml)
[![codecov](https://codecov.io/gh/qBraid/pyqasm/graph/badge.svg?token=92YURMR8T8)](https://codecov.io/gh/qBraid/pyqasm)
[![GitHub Pages](https://img.shields.io/github/actions/workflow/status/qBraid/pyqasm/gh-pages.yml?label=docs)](https://sdk.qbraid.com/pyqasm/)
[![PyPI version](https://img.shields.io/pypi/v/pyqasm.svg?color=blue)](https://pypi.org/project/pyqasm/)
[![Python verions](https://img.shields.io/pypi/pyversions/pyqasm.svg?color=blue)](https://pypi.org/project/pyqasm/)
[![License](https://img.shields.io/github/license/qBraid/pyqasm.svg?color=purple)](https://www.apache.org/licenses/LICENSE-2.0)

Python toolkit providing an OpenQASM 3 semantic analyzer and utilities for program analysis and compilation.


[![Env Badge](https://img.shields.io/endpoint?url=https://api.qbraid.com/api/environments/valid?envSlug=pyqasm_l9qauu&label=Launch+on+qBraid&labelColor=white&logo=rocket&logoSize=auto&style=for-the-badge)](http://account.qbraid.com?gitHubUrl=https://github.com/qBraid/pyqasm.git&envId=pyqasm_l9qauu)


## Motivation
[OpenQASM](https://openqasm.com/) is a powerful language for expressing hybrid quantum-classical programs, but it lacks a comprehensive tool supporting the full capabilities of the language. PyQASM aims to fill this gap by building upon the [`openqasm3.parser`](https://github.com/openqasm/openqasm/blob/ast-py/v1.0.1/source/openqasm/openqasm3/parser.py), and providing support for semantic analysis and utilities for program compilation.

## Installation

PyQASM requires Python 3.10 or greater, and can be installed with pip as follows:

```bash
pip install pyqasm
```

### Install from source 

You can also install from source by cloning this repository and running a pip install command
in the root directory of the repository:

```bash
git clone https://github.com/qBraid/pyqasm.git
cd pyqasm
pip install .
```

## Check version

You can view the version of pyqasm you have installed within a Python shell as follows:

```python
>>> import pyqasm
>>> pyqasm.__version__
```

## Resources

- [API Reference](https://qbraid.github.io/pyqasm/api/pyqasm.html): Developer documentation.
- [Usage Examples](examples): Scripts and Markdown examples demonstrating core functionality.
- [Supported Operations](pyqasm/README.md#supported-operations): OpenQASM language features supported, in progress, and planned for future support.

## Contributing

[![GitHub](https://img.shields.io/badge/issue_tracking-github-black?logo=github)](https://github.com/qBraid/pyqasm/issues)
[![QCSE](https://img.shields.io/badge/QCSE-pyqasm-orange?logo=stackexchange)](https://quantumcomputing.stackexchange.com/questions/tagged/pyqasm)
[![Discord](https://img.shields.io/badge/Discord-%235865F2.svg?logo=discord&logoColor=white)](https://discord.gg/TPBU2sa8Et)

- Interested in contributing code, or making a PR? See
  [CONTRIBUTING.md](CONTRIBUTING.md)
- For feature requests and bug reports:
  [Submit an issue](https://github.com/qBraid/pyqasm/issues)
- For discussions, and specific questions about pyqasm, or
  other topics, [join our discord community](https://discord.gg/TPBU2sa8Et)
- For questions that are more suited for a forum, post to
  [QCSE](https://quantumcomputing.stackexchange.com/)
  with the [`pyqasm`](https://quantumcomputing.stackexchange.com/questions/tagged/pyqasm) tag.
- By participating, you are expected to uphold our [code of conduct](CODE_OF_CONDUCT).

## License

[Apache-2.0 License](LICENSE)
