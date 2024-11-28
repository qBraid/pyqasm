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
- Added a `dumps` and `formatted_qasm` method to the `QasmModule` class to allow for the conversion of a `QasmModule` object to a string representation of the QASM code ([#71](https://github.com/qBraid/pyqasm/pull/71))
- Added the `populate_idle_qubits` method to the `QasmModule` class to populate idle qubits with an `id` gate ([#72](https://github.com/qBraid/pyqasm/pull/72))
- Added gate definitions for "c3sqrtx", "u1", "rxx", "cu3", "csx", "rccx" , "ch" , "cry", "cp", "cu", "cu1", "rzz" in `maps.py` ([#74](https://github.com/qBraid/pyqasm/pull/74))
- Added support for skipping the unrolling for externally linked gates. The `QasmModule.unroll()` method now accepts an `external_gates` parameter which is a list of gate names that should not be unrolled ([#59](https://github.com/qBraid/pyqasm/pull/59)). Usage - 

```python
In [30]: import pyqasm

In [31]: qasm_str = """OPENQASM 3.0;
    ...:     include "stdgates.inc";
    ...:     gate custom q1, q2, q3{
    ...:         x q1;
    ...:         y q2;
    ...:         z q3;
    ...:     }
    ...:
    ...:     qubit[4] q;
    ...:     custom q[0], q[1], q[2];
    ...:     cx q[1], q[2];"""

In [32]: module = pyqasm.loads(qasm_str)

In [33]: module.unroll(external_gates= ["custom"])

In [34]: pyqasm.dumps(module).splitlines()
Out[34]:
['OPENQASM 3.0;',
 'include "stdgates.inc";',
 'qubit[4] q;',
 'custom q[0], q[1], q[2];',
 'cx q[1], q[2];']
```
- **Major Change**: Added the `load`, `loads`, `dump`, and `dumps` functions to the `pyqasm` module to allow for the loading and dumping of QASM code ([#76](https://github.com/qBraid/pyqasm/pull/76)). Usage - 

```python
In [18]: import pyqasm

In [19]: qasm_str = """OPENQASM 3.0;
    ...:     include "stdgates.inc";
    ...:     qreg q1[2];
    ...:     qubit[2] q2;"""

In [20]: module = pyqasm.loads(qasm_str)

In [21]: print(pyqasm.dumps(module))
OPENQASM 3.0;
include "stdgates.inc";
qubit[2] q1;
qubit[2] q2;


In [22]: file_path = "test.qasm"

In [23]: pyqasm.dump(module, file_path)

In [24]: module = pyqasm.load(file_path)

In [25]: print(pyqasm.dumps(module))
OPENQASM 3.0;
include "stdgates.inc";
qubit[2] q1;
qubit[2] q2;
```
- Added definitions for various gates in `maps.py` and tests for qasm formatting functions of the qbraid-sdk ([#82](https://github.com/qBraid/pyqasm/pull/82), [#84](https://github.com/qBraid/pyqasm/pull/84))
- Added `pyqasm.accelerate` module to hold `.pyx` files with Cython-based optimizations for computationally intensive functions  ([#83](https://github.com/qBraid/pyqasm/pull/83))
- Added `has_barriers` method for checking if a `QasmModule` object contains barriers ([#85](https://github.com/qBraid/pyqasm/pull/85))
- Added `pyqasm.cli` module with `typer` integration to enable using pyqasm as a command-line tool ([#87](https://github.com/qBraid/pyqasm/pull/87))

```bash
$ pip install 'pyqasm[cli]'
$ pyqasm --help
Usage: pyqasm [OPTIONS] COMMAND [ARGS]...
$ pyqasm --version
pyqasm/0.1.0a1
$ pyqasm validate tests/cli/resources
tests/cli/resources/invalid1.qasm: error: Index 2 out of range for register of size 1 in qubit [validation]
Found errors in 1 file (checked 3 source files)
$ pyqasm validate tests/cli/resources --skip tests/cli/resources/invalid1.qasm
Success: no issues found in 2 source files
```

### Improved / Modified
- Changed the `__init__` method for the `QasmModule` class to only accept an `openqasm3.ast.Program` object as input ([#71](https://github.com/qBraid/pyqasm/pull/71))
- Changed `DepthNode`, `QubitDepthNode`, `ClbitDepthNode`, and `Variable` to dataclasses. `__repr__` method is therefore handled automatically and you don't need all of the redundant private / public attribute and setters ([#79](https://github.com/qBraid/pyqasm/pull/79))
- Simplified `map_qasm_op_to_callable` redundant `KeyError` handling with loop ([#79](https://github.com/qBraid/pyqasm/pull/79))
- The `load` function has been renamed to `loads` and `load` is now used to load a QASM file. `QasmModule.dumps()` has been replaced with `__str__` method ([#76](https://github.com/qBraid/pyqasm/pull/76))
- Experimental Cython integration:  ([#83](https://github.com/qBraid/pyqasm/pull/83))
    - Migrated `pyqasm.linalg._kronecker_factor` to `pyqasm.linalg_cy` with ~60% speedup
    - Migrated `pyqasm.linalg._so4_to_so2()` to to `pyqasm.linalg_cy` with ~5% speedup
- Changed source code directory from `./pyqasm` to `./src/pyqasm` to prevents conflicts between the local source directory and the installed package in site-packages, ensuring Python's module resolution prioritizes the correct version. Required for local testing with new Cython build step ([#83](https://github.com/qBraid/pyqasm/pull/83))
- Updated the build process for `pyqasm` due to Cython integration. Wheels are now built for each platform and uploaded to PyPI along with the source distributions ([#88](https://github.com/qBraid/pyqasm/pull/88))

### Deprecated

### Removed
- Removed the `from_program` method from the `QasmModule` class ([#71](https://github.com/qBraid/pyqasm/pull/71))
- `QasmModule.formatted_qasm()` method has been removed ([#76](https://github.com/qBraid/pyqasm/pull/76))

### Fixed
- Updated docs custom CSS used for sphinx to make version stable/latest drop-down visible. Previously was set white so blended into background and wasn't visible. ([#78](https://github.com/qBraid/pyqasm/pull/78))
- Fixed bug in `pyqasm.linalg.so_bidiagonalize()` in final dot product order ([#83](https://github.com/qBraid/pyqasm/pull/83))

### Dependencies

## Past Release Notes

Archive of changelog entries from previous releases:

- [v0.0.3](https://github.com/qBraid/pyqasm/releases/tag/v0.0.3)
- [v0.0.2](https://github.com/qBraid/pyqasm/releases/tag/v0.0.2)
- [v0.0.1](https://github.com/qBraid/pyqasm/releases/tag/v0.0.1)
