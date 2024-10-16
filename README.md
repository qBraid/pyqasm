# pyqasm

<img align="right" width="100" src="https://qbraid-static.s3.amazonaws.com/pyqasm.svg"/>

[![CI](https://github.com/qBraid/pyqasm/actions/workflows/main.yml/badge.svg?branch=main)](https://github.com/qBraid/pyqasm/actions/workflows/main.yml)
[![Documentation Status](https://readthedocs.com/projects/qbraid-pyqasm/badge/?version=latest&token=d5432c6f40d942b391982fc88183389938a0e930ae5e588cf579e9ab1e3319a0)](https://qbraid-pyqasm.readthedocs-hosted.com/en/latest/?badge=latest)
[![PyPI version](https://img.shields.io/pypi/v/pyqasm.svg?color=blue)](https://pypi.org/project/pyqasm/)
[![Python verions](https://img.shields.io/pypi/pyversions/pyqasm.svg?color=blue)](https://pypi.org/project/pyqasm/)
[![License](https://img.shields.io/github/license/qBraid/pyqasm.svg?color=purple)](https://www.gnu.org/licenses/gpl-3.0.html)
[![QCSE](https://img.shields.io/badge/QCSE-pyqasm-orange?logo=stackexchange)](https://quantumcomputing.stackexchange.com/questions/tagged/pyqasm)
<!-- [![GitHub](https://img.shields.io/badge/issue_tracking-github-black?logo=github)](https://github.com/qBraid/pyqasm/issues) -->

Python toolkit providing an OpenQASM 3 semantic analyzer and utilities for program analysis and compilation.


>[!WARNING]
> **This project is "pre-alpha", and is not yet stable or fully realized. Use with caution, as the API and functionality are subject to significant changes.**

## Motivation 
The current [OpenQASM 3 standard](https://openqasm.com/index.html) is a powerful language for expressing hybrid quantum-classical programs, but it lacks a comprehensive tool supporting the full capabilities of the language. Pyqasm aims to fill this gap by building upon the [openqasm parser](https://github.com/openqasm/openqasm/tree/main/source/openqasm), and providing support for semantic analysis and utilities for program compilation.

## Installation

pyqasm requires Python 3.10 or greater, and can be installed with pip as follows:

```bash
pip install pyqasm
```

## Install from source 

You can also install from source by cloning this repository and running a pip install command
in the root directory of the repository:

```shell
git clone https://github.com/qBraid/pyqasm.git
cd pyqasm
pip install .
```

## Check version

You can view the version of pyqasm you have installed within a Python shell as follows:

```python
import pyqasm
print(pyqasm.__version__)
```

## Usage Examples

### Unrolling OpenQASM 3 program 

```python
from pyqasm.unroller import unroll

program = """
OPENQASM 3;
include "stdgates.inc";

qubit[2] q;
bit[2] c;

h q[0];
cx q[0], q[1];

measure q->c;
"""

unrolled_qasm = unroll(program).unrolled_qasm
print(unrolled_qasm)
```

For a more complex example, see the [Deutsch Josza program unrolling](examples/unroll_example.py) 

### Validating OpenQASM 3 program 

```python
from pyqasm.validate import validate

program = """
OPENQASM 3;
include "stdgates.inc";
qubit[2] q;
bit[2] c;
// create a Bell state
h q[0];
cx q[0], q[1];

// measure the qubits
measure q -> c;
"""

assert validate(program) is None
```
`validate` returns None if the program is semantically valid, otherwise raises an Exception. See the [validation example](examples/validate_example.py) for more insight into the capabilities of our analyser.



## Contributing 

- Interested in contributing code, or making a PR? See
  [CONTRIBUTING.md](CONTRIBUTING.md)
- For feature requests and bug reports:
  [Submit an issue](https://github.com/qBraid/pyqasm/issues)
- For discussions, and specific questions about pyqasm, or
  other topics, [join our discord community](https://discord.gg/TPBU2sa8Et)
- For questions that are more suited for a forum, post to
  [QCSE](https://quantumcomputing.stackexchange.com/)
  with the [`qbraid`](https://quantumcomputing.stackexchange.com/questions/tagged/qbraid) tag.
- By participating, you are expected to uphold our [code of conduct](CODE_OF_CONDUCT).


