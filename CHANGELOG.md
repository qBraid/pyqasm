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
- Added the `pulse` extra dependency to the `pyproject.toml` file, which includes the `openpulse` package. This allows users to install pulse-related functionality when needed. ([#195](https://github.com/qBraid/pyqasm/pull/195))
- Added support for unrolling `while` loops with compile time condition evaluation. Users can now use `unroll` on while loops which do not have conditions depending on quantum measurements. ([#206](https://github.com/qBraid/pyqasm/pull/206)) Eg. - 

```python
import pyqasm 

qasm_str = """
    OPENQASM 3.0;
    qubit[4] q;
    int i = 0;
    while (i < 3) {
        h q[i];
        cx q[i], q[i+1];
        i += 1;
    }

    """
result = pyqasm.loads(qasm_str)
result.unroll()
print(result)

# **Output**

# OPENQASM 3.0;
# qubit[4] q;
# h q[0];
# cx q[0], q[1];
# h q[1];
# cx q[1], q[2];
# h q[2];
# cx q[2], q[3];

```

### Improved / Modified

- Refactored `analyze_classical_indices` method to use `@staticmethod` instead of `@classmethod`. ([#194](https://github.com/qBraid/pyqasm/pull/194))
- Optimized `_visit_generic_gate_operation` in `QasmVisitor` class by using shallow copy instead of deep copy for better performance when processing gate operations. ([#180](https://github.com/qBraid/pyqasm/pull/180))

### Deprecated

### Removed

### Fixed

- Fixed the way how depth is calculated when external gates are defined with unrolling a QASM module. ([#198](https://github.com/qBraid/pyqasm/pull/198))
- Added separate depth calculation for gates inside branching statements. ([#200](https://github.com/qBraid/pyqasm/pull/200)) 
  - **Example:**
  ```python
  OPENQASM 3.0;
  include "stdgates.inc";
  qubit[4] q;
  bit[4] c;
  bit[4] c0;
  if (c[0]){
    x q[0];
    h q[0]
    }
  else {
    h q[1];
  }
  ```
  ```text
  Depth = 1
  ```
  - Previously, each gate inside an `if`/`else` block would advance only its own wire depth. Now, when any branching statement is encountered, all qubit‐ and clbit‐depths used inside that block are first incremented by one, then set to the maximum of those new values. This ensures the entire conditional block counts as single “depth” increment, rather than letting individual gates within the same branch float ahead independently.
  - In the above snippet, c[0], q[0], and q[1] all jump together to a single new depth for that branch.
- Added initial support to explicit casting by converting the declarations into implicit casting logic. ([#205](https://github.com/qBraid/pyqasm/pull/205))
### Dependencies

### Other

## Past Release Notes

Archive of changelog entries from previous releases:

- [v0.3.1](https://github.com/qBraid/pyqasm/releases/tag/v0.3.1)
- [v0.3.0](https://github.com/qBraid/pyqasm/releases/tag/v0.3.0)
- [v0.2.1](https://github.com/qBraid/pyqasm/releases/tag/v0.2.1)
- [v0.2.0](https://github.com/qBraid/pyqasm/releases/tag/v0.2.0)
- [v0.1.0](https://github.com/qBraid/pyqasm/releases/tag/v0.1.0)
- [v0.1.0-alpha](https://github.com/qBraid/pyqasm/releases/tag/v0.1.0-alpha)
- [v0.0.3](https://github.com/qBraid/pyqasm/releases/tag/v0.0.3)
- [v0.0.2](https://github.com/qBraid/pyqasm/releases/tag/v0.0.2)
- [v0.0.1](https://github.com/qBraid/pyqasm/releases/tag/v0.0.1)
