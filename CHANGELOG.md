# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Types of changes:
- `Added`: for new features.
- `Improved`: for improvements to existing functionality.
- `Deprecated`: for soon-to-be removed features.
- `Removed`: for now removed features.
- `Fixed`: for any bug fixes.
- `Dependencies`: for updates to external libraries or packages.

## [Unreleased]

### Added
- Sphinx docs and examples added for pyqasm ([#20](https://github.com/qBraid/pyqasm/pull/20))
- qBraid header check enabled in format action([#29](https://github.com/qBraid/pyqasm/pull/29))
- Integrated code coverage with codecov ([#30](https://github.com/qBraid/pyqasm/pull/30))

### Improved / Modified
- Housekeeping updates involving codeowners, workflows, pyproject, and readme ([#16](https://github.com/qBraid/pyqasm/pull/16))
- Fixed parsing of compile-time constants for register sizes. Statements like `const int[32] N = 3; qubit[N] q;` are now supported ([#21](https://github.com/qBraid/pyqasm/pull/21)).
- Update project `README.md` ([#22](https://github.com/qBraid/pyqasm/pull/22))
- Updated sphinx docs page ([#26](https://github.com/qBraid/pyqasm/pull/26))
- **Major Change**: The default type for `pyqasm.unroller.unroll` has been changed from `pyqasm.elements.Qasm3Module` to `str`. This change is backward-incompatible and will require users to update their code. The following code snippet demonstrates the change - 

```python
from pyqasm.unroller import unroll
qasm_str = """
OPENQASM 3;
qubit[3] q;
h q;
"""

# Old way : The default type for unroll was pyqasm.elements.Qasm3Module
program = unroll(qasm_str, as_module=True)
unrolled_qasm_old = program.unrolled_qasm

# New way : The default type for unroll is now str
unrolled_qasm_new = unroll(qasm_str)
```
To force the return type to be `pyqasm.elements.Qasm3Module`, users can set the `as_module` parameter to `True` as shown above to update their code.

### Deprecated

### Removed

### Fixed
- Issue with aliasing of qubits was fixed where aliased qubits were referenced with non-aliased qubits in a quantum gate ([#14](https://github.com/qBraid/pyqasm/pull/14)). The following program is now supported - 

```python
OPENQASM 3;
include "stdgates.inc";
qubit[4] q;
let alias = q[0:2];
cx alias[1], q[2];
```

- Issue with subroutines, when `return` keyword was absent, was fixed in ([#21](https://github.com/qBraid/pyqasm/pull/21))

### Dependencies

## References
[Changelog for release v0.0.1](https://github.com/qBraid/pyqasm/releases/tag/v0.0.1)
