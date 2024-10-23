# pyqasm

<img align="right" width="100" src="https://qbraid-static.s3.amazonaws.com/pyqasm.svg"/>

[![CI](https://github.com/qBraid/pyqasm/actions/workflows/main.yml/badge.svg?branch=main)](https://github.com/qBraid/pyqasm/actions/workflows/main.yml)
[![codecov](https://codecov.io/gh/qBraid/pyqasm/graph/badge.svg?token=92YURMR8T8)](https://codecov.io/gh/qBraid/pyqasm)
[![Documentation Status](https://readthedocs.com/projects/qbraid-pyqasm/badge/?version=latest&token=d5432c6f40d942b391982fc88183389938a0e930ae5e588cf579e9ab1e3319a0)](https://qbraid-pyqasm.readthedocs-hosted.com/en/latest/?badge=latest)
[![PyPI version](https://img.shields.io/pypi/v/pyqasm.svg?color=blue)](https://pypi.org/project/pyqasm/)
[![Python verions](https://img.shields.io/pypi/pyversions/pyqasm.svg?color=blue)](https://pypi.org/project/pyqasm/)
[![License](https://img.shields.io/github/license/qBraid/pyqasm.svg?color=purple)](https://www.gnu.org/licenses/gpl-3.0.html)

Python toolkit providing an OpenQASM 3 semantic analyzer and utilities for program analysis and compilation. You can find the complete list of OpenQASM language features supported, in progress, and planned for future support by PyQASM [here](pyqasm/README.md#supported-operations).

>[!WARNING]
> **This project is "pre-alpha", and is not yet stable or fully realized. Use with caution, as the API and functionality are subject to significant changes.**

## Motivation
[OpenQASM](https://openqasm.com/) is a powerful language for expressing hybrid quantum-classical programs, but it lacks a comprehensive tool supporting the full capabilities of the language. PyQASM aims to fill this gap by building upon the [`openqasm3.parser`](https://github.com/openqasm/openqasm/blob/ast-py/v1.0.0/source/openqasm/openqasm3/parser.py), and providing support for semantic analysis and utilities for program compilation.

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
import pyqasm

pyqasm.__version__
```

## Usage Examples

### Program Unrolling

```python
import pyqasm 

program = """
OPENQASM 3;
include "stdgates.inc";

gate hgate q { h q; }
gate xgate q { x q; }

const int[32] N = 4;
qubit[4] q;
qubit ancilla;

def deutsch_jozsa(qubit[N] q_func, qubit[1] ancilla_q) {
  xgate ancilla_q;
  for int i in [0:N-1] { hgate q_func[i]; }
  hgate ancilla_q;
  for int i in [0:N-1] { cx q_func[i], ancilla_q; }
  for int i in [0:N-1] { hgate q_func[i]; }
}

deutsch_jozsa(q, ancilla);

bit[4] result;
result = measure q;
"""

unrolled = pyqasm.unroll(program)

print(unrolled)
```

```text
OPENQASM 3;
include "stdgates.inc";
qubit[4] q;
qubit[1] ancilla;
x ancilla[0];
h q[0];
h q[1];
h q[2];
h q[3];
h ancilla[0];
cx q[0], ancilla[0];
cx q[1], ancilla[0];
cx q[2], ancilla[0];
cx q[3], ancilla[0];
h q[0];
h q[1];
h q[2];
h q[3];
bit[4] result;
result[0] = measure q[0];
result[1] = measure q[1];
result[2] = measure q[2];
result[3] = measure q[3];
```

`pyqasm.unroll()` simplifies a quantum program by expanding custom gate definitions and flattening complex constructs like subroutines, loops, and conditionals into basic operations. This process, also called **program flattening** or **inlining**, transforms the program into a linear sequence of qubit and classical bit declarations, gate operations, and measurements, making it easier to transpile or compile for execution on a quantum device. See the extended [Deutsch Josza program unrolling example](examples/unroll_example.py) for more details about the OpenQASM 3 language features being "unrolled" in the above program.

### Program Validation

```python
import pyqasm

program = """
OPENQASM 3;
include "stdgates.inc";

qubit[1] q;
bit[1] c;

// bad code
h q[2];

c = measure q;
"""

pyqasm.validate(program)
```

```text
pyqasm.exceptions.ValidationError: Index 2 out of range for register of size 1 in qubit
```

`pyqasm.validate()` returns `None` if the program is semantically valid, otherwise raises an Exception. Check out a more detailed [validation example](examples/validate_example.py) for a deeper look into the capabilities of our semantic analyzer.

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


