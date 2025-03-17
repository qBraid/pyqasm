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

## Unreleased

### Added
- Added logic to `bump-version.yml` workflow that automatically updates `CITATION.cff` upon new release ([#147](https://github.com/qBraid/pyqasm/pull/147))
- Added `pyqasm.draw()` function that draws quantum circuit ([#122](https://github.com/qBraid/pyqasm/pull/122)):

```python
from pyqasm import draw

qasm = """
OPENQASM 3.0;
include "stdgates.inc";

qubit[3] q;
bit[3] b;

h q[0];
z q[1];
rz(pi/1.1) q[0];
cx q[0], q[1];
swap q[0], q[1];
ccx q[0], q[1], q[2];
b = measure q;
"""

draw(qasm, output='mpl')
```

![Screenshot 2025-03-17 at 2 23 14 PM](https://github.com/user-attachments/assets/9f7cdf35-997e-4858-8f79-016b449c68a4)

\- Currently, only the `mpl` (matplotlib) output format is supported.

\- Use `draw(..., idle_wires=False)` to draw circuit without empty qubit/classical bit registers.

\- Save the visualization to a file by specifying `output='mpl'` and a `filename`:
  ```python
  draw(..., output='mpl', filename='/path/to/circuit.png')
  ```

\- The draw method accepts either a `str` (QASM source) or a `QasmModule`. The following are equivalent:

```python
from pyqasm import loads, draw
from pyqasm.printer import mpl_draw

module = loads(qasm_str)

draw(module, output='mpl')
draw(qasm_str, output='mpl')

draw(module)
draw(qasm_str)
```

### Improved / Modified

### Deprecated

### Removed

### Fixed
- Fixed bug in release workflow(s) that caused discrepancy between `pyqasm.__version__` and `importlib.metadata.version` ([#147](https://github.com/qBraid/pyqasm/pull/147))
- Fixed a bug in broadcast operation for duplicate qubits so that the following  - 

```qasm
OPENQASM 3.0;
include "stdgates.inc";
qubit[3] q;
qubit[2] q2;
cx q[0], q[1], q[1], q[2];
cx q2, q2;
```

will unroll correctly to - 

```qasm
OPENQASM 3.0;
include "stdgates.inc";
qubit[3] q;
qubit[2] q2;
// cx q[0], q[1], q[1], q[2];
cx q[0], q[1];
cx q[1], q[2];

// cx q2, q2;
cx q2[0], q2[1];
cx q2[0], q2[1];
```

The logic for duplicate qubit detection is moved out of the `QasmVisitor._get_op_bits` into `Qasm3Analyzer` class and is executed post gate broadcast operation ([#155](https://github.com/qBraid/pyqasm/pull/155)).

### Dependencies

### Other
- Updated license from [GPL-3.0](https://www.gnu.org/licenses/gpl-3.0.html) to [Apache-2.0](https://www.apache.org/licenses/LICENSE-2.0) ([#158](https://github.com/qBraid/pyqasm/pull/158))
- Added GitHub actions for publishing to GitHub pages, and updated docs pages from Readthedocs to GitHub pages links. ([#158](https://github.com/qBraid/pyqasm/pull/158))

## Past Release Notes

Archive of changelog entries from previous releases:

- [v0.2.1](https://github.com/qBraid/pyqasm/releases/tag/v0.2.1)
- [v0.2.0](https://github.com/qBraid/pyqasm/releases/tag/v0.2.0)
- [v0.1.0](https://github.com/qBraid/pyqasm/releases/tag/v0.1.0)
- [v0.1.0-alpha](https://github.com/qBraid/pyqasm/releases/tag/v0.1.0-alpha)
- [v0.0.3](https://github.com/qBraid/pyqasm/releases/tag/v0.0.3)
- [v0.0.2](https://github.com/qBraid/pyqasm/releases/tag/v0.0.2)
- [v0.0.1](https://github.com/qBraid/pyqasm/releases/tag/v0.0.1)
