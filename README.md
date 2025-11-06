# pyqasm

<img align="right" width="100" src="https://qbraid-static.s3.amazonaws.com/pyqasm.svg"/>

[![CI](https://github.com/qBraid/pyqasm/actions/workflows/main.yml/badge.svg?branch=main)](https://github.com/qBraid/pyqasm/actions/workflows/main.yml)
[![codecov](https://codecov.io/gh/qBraid/pyqasm/graph/badge.svg?token=92YURMR8T8)](https://codecov.io/gh/qBraid/pyqasm)
[![GitHub Pages](https://img.shields.io/github/actions/workflow/status/qBraid/pyqasm/gh-pages.yml?label=docs)](https://sdk.qbraid.com/pyqasm/)
[![PyPI version](https://img.shields.io/pypi/v/pyqasm.svg?color=blue)](https://pypi.org/project/pyqasm/)
[![PyPI Downloads](https://static.pepy.tech/badge/pyqasm)](https://pepy.tech/projects/pyqasm)
[![Python verions](https://img.shields.io/pypi/pyversions/pyqasm.svg?color=blue)](https://pypi.org/project/pyqasm/)
[![License](https://img.shields.io/github/license/qBraid/pyqasm.svg?color=purple)](https://www.apache.org/licenses/LICENSE-2.0)

Python toolkit providing an OpenQASM 3 semantic analyzer and utilities for program analysis and compilation.

[![Env Badge](https://img.shields.io/endpoint?url=https://api.qbraid.com/api/environments/valid?envSlug=pyqasm_l9qauu&label=Launch+on+qBraid&labelColor=lightgrey&logo=rocket&logoSize=auto&style=for-the-badge)](http://account.qbraid.com?gitHubUrl=https://github.com/qBraid/pyqasm.git&envId=pyqasm_l9qauu)

## Motivation
[OpenQASM](https://openqasm.com/) is a powerful language for expressing hybrid quantum-classical programs, but it lacks a comprehensive tool supporting the _full capabilities of the language_. PyQASM aims to fill this gap by building upon the [`openqasm3.parser`](https://github.com/openqasm/openqasm/blob/ast-py/v1.0.1/source/openqasm/openqasm3/parser.py), and providing support for semantic analysis and utilities for program compilation.

## Installation

PyQASM requires Python 3.10 or greater, and can be installed with pip as follows:

```bash
pip install pyqasm
```

### Optional Dependencies
PyQASM offers optional extras such as - 
1. `cli` : command-line interface (CLI) functionality
2. `visualization`: for program visualization 
3. `pulse` : pulse/calibration features (in progress)

To install these features along with the core package, you can use the following command:
```bash
pip install 'pyqasm[cli,pulse,visualization]'
```

You can also install them individually. For example, to install the CLI features only, you can run:
```bash
pip install 'pyqasm[cli]'      
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

## Key Features: Unroll & Validate OpenQASM 3 Programs

PyQASM offers robust support for the **extensive grammar of OpenQASM 3**, including custom gates, subroutines, loops, conditionals, classical control, and more. Its core utilities allow you to **validate** programs for semantic correctness and **unroll** (flatten) all high-level constructs into a linear sequence of basic quantum operations, ready for execution or further compilation.

### Highlights

- **[Comprehensive Grammar Support](src/README.md)**: PyQASM supports the full breadth of OpenQASM 3 operations, and backward compatibility with OpenQASM 2, including:
  - Classical and quantum registers
  - Loops (`for`, `while`)
  - Conditionals (`if`, `else`)
  - Parameterized and custom gates
  - Subroutine inlining
  - Switch statements
  - Classical expressions and assignments
  - Variables and arrays
  - Type casting and conversions
  - Built-in and user-defined constants
  - Quantum-classical interaction (`measurement`, `reset`, etc.)
  - Inclusion of standard libraries (`stdgates.inc`, etc.)

- **[Unrolling](https://docs.qbraid.com/pyqasm/user-guide/examples#inlining-%26-unrolling):**  
  Expands all custom gates, loops, subroutines, branches, etc. into a flat, hardware-ready sequence of instructions.

- **[Validation](https://docs.qbraid.com/pyqasm/user-guide/overview#the-qasmmodule-object):**  
  Performs semantic analysis to ensure programs are correct and conform to the OpenQASM 3 specification.

---

### Example: Unroll and Validate a Complex QASM Program

Below is an example demonstrating PyQASM's efficacy on a non-trivial OpenQASM 3 program. This program uses custom gates, loops, and classical control, and is fully unrolled and validated by PyQASM:

```python
from pyqasm import loads, dumps

qasm = """
OPENQASM 3;
include "stdgates.inc";

gate h2 a, b { h a; h b; }
def parity_flip(qubit[4] q) {
    for int i in [0:3] {
        if (i % 2 == 0) {
            x q[i];
        }
    }
}

qubit[4] q;
bit[4] c;

h2 q[0], q[1];
parity_flip(q);

for int i in [0:3] {
    measure q[i] -> c[i];
}
"""

module = loads(qasm)      # Parse and build the program
module.validate()         # Check for semantic errors
module.unroll()           # Flatten all gates, loops, and subroutines

print(dumps(module))      # Output the fully unrolled QASM
```

**Output (fully unrolled QASM):**
```qasm
OPENQASM 3.0;
include "stdgates.inc";
qubit[4] q;
bit[4] c;
h q[0];
h q[1];
x q[0];
x q[2];
c[0] = measure q[0];
c[1] = measure q[1];
c[2] = measure q[2];
c[3] = measure q[3];
```

PyQASM ensures your OpenQASM programs are **semantically correct** and **hardware-ready**, supporting the language's most advanced features with ease.
## Resources

- [API Reference](https://qbraid.github.io/pyqasm/api/pyqasm.html): Developer documentation.
- [Usage Examples](examples): Scripts and Markdown examples demonstrating core functionality.
- [Supported Operations](pyqasm/README.md#supported-operations): OpenQASM language features supported, in progress, and planned for future support.
- [Gate Decompositions](docs/gate_decompositions.md): Detailed decomposition diagrams and explanations for quantum gates.

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
