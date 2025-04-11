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
- Added support for conditionally unrolling barrier statements in the `unroll` method with the `unroll_barriers` flag. ([#166](https://github.com/qBraid/pyqasm/pull/166)) - 

```python
In [1]: import pyqasm

In [2]: qasm_str = """
   ...:     OPENQASM 3.0;
   ...:     include "stdgates.inc";
   ...: 
   ...:     qubit[2] q1;
   ...:     qubit[3] q2;
   ...:     qubit q3;
   ...: 
   ...:     // barriers
   ...:     barrier q1, q2, q3;
   ...:     barrier q2[:3];
   ...:     barrier q3[0];
   ...: """

In [3]: module = pyqasm.loads(qasm_str)

In [4]: module.unroll(unroll_barriers = False)

In [5]: print(module)
OPENQASM 3.0;
include "stdgates.inc";
qubit[2] q1;
qubit[3] q2;
qubit[1] q3;
barrier q1, q2, q3;
barrier q2[:3];
barrier q3[0];
```

### Improved / Modified
- Improved the error messages for the parameter mismatch errors in basic quantum gates ([#169](https://github.com/qBraid/pyqasm/issues/169)). Following error is raised on parameter count mismatch - 

```python
In [1]: import pyqasm
   ...: 
   ...: qasm = """
   ...: OPENQASM 3;
   ...: include "stdgates.inc";
   ...: qubit[2] q;
   ...: rx(0.5, 1) q[1];
   ...: """
   ...: program = pyqasm.loads(qasm)
   ...: program.validate()

......
ValidationError: Expected 1 parameter for gate 'rx', but got 2  
```
### Deprecated

### Removed
- Removed the dependency on `Union` for typing by replacing it with `|` ([#170](https://github.com/qBraid/pyqasm/pull/170)).

### Fixed
- Resolved the inconsistency in `pyqasm.printer.draw` and `pyqasm.printer.mpl_draw` behaviour for multiple function calls. See issue [#165](https://github.com/qBraid/pyqasm/issues/165) for bug details. ([#168](https://github.com/qBraid/pyqasm/pull/168))

### Dependencies

### Other

## Past Release Notes

Archive of changelog entries from previous releases:

- [v0.3.0](https://github.com/qBraid/pyqasm/releases/tag/v0.3.0)
- [v0.2.1](https://github.com/qBraid/pyqasm/releases/tag/v0.2.1)
- [v0.2.0](https://github.com/qBraid/pyqasm/releases/tag/v0.2.0)
- [v0.1.0](https://github.com/qBraid/pyqasm/releases/tag/v0.1.0)
- [v0.1.0-alpha](https://github.com/qBraid/pyqasm/releases/tag/v0.1.0-alpha)
- [v0.0.3](https://github.com/qBraid/pyqasm/releases/tag/v0.0.3)
- [v0.0.2](https://github.com/qBraid/pyqasm/releases/tag/v0.0.2)
- [v0.0.1](https://github.com/qBraid/pyqasm/releases/tag/v0.0.1)
