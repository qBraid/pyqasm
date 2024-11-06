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
- Dependabot configuration file ([#37](https://github.com/qBraid/pyqasm/pull/37))
- Added support for QASM2 program validation and unrolling ([#46](https://github.com/qBraid/pyqasm/pull/46))
- Added better typing to linalg module + some tests ([#47](https://github.com/qBraid/pyqasm/pull/47))
- Added a `remove_idle_qubits` method to the `QasmModule` class which can be used to remove idle qubits from a quantum program ([#58](https://github.com/qBraid/pyqasm/pull/58)). Usage is as follows - 

```python
In [3]: import pyqasm
   ...: qasm_str = """OPENQASM 3.0;
   ...:      gate custom q1, q2, q3{
   ...:          x q1;
   ...:          y q2;
   ...:          z q3;
   ...:      }
   ...:      qreg q1[2];
   ...:      qubit[2] q2;
   ...:      qubit[3] q3;
   ...:      qubit q4;
   ...:      qubit[5]   q5;
   ...:
   ...:      x q1[0];
   ...:      y q2[1];
   ...:      z q3;"""
   ...: module = pyqasm.load(qasm_str)
   ...: module.validate()
   ...:

In [4]: module.num_qubits
Out[4]: 13

In [5]: module.remove_idle_qubits()
Out[5]: <pyqasm.modules.Qasm3Module at 0x1052364b0>

In [6]: module.num_qubits
Out[6]: 5

In [7]: module.unrolled_qasm.splitlines()
Out[7]:
['OPENQASM 3.0;',
 'include "stdgates.inc";',
 'qubit[1] q1;',
 'qubit[1] q2;',
 'qubit[3] q3;',
 'x q1[0];',
 'y q2[0];',
 'z q3[0];',
 'z q3[1];',
 'z q3[2];']
```

- Implemented the `reverse_qubit_order` method to the `QasmModule` class which can be used to reverse the order of qubits in a quantum program ([#60](https://github.com/qBraid/pyqasm/pull/60)). Usage is as follows - 

```python
In [3]: import pyqasm

In [4]: qasm3_str = """
   ...:     OPENQASM 3.0;
   ...:     include "stdgates.inc";
   ...:     qubit[2] q;
   ...:     qubit[4] q2;
   ...:     qubit q3;
   ...:     bit[1] c;
   ...:
   ...:     cnot q[0], q[1];
   ...:     cnot q2[0], q2[1];
   ...:     x q2[3];
   ...:     cnot q2[0], q2[2];
   ...:     x q3;
   ...:     c[0] = measure q2[0];
   ...:     """

In [5]: module = pyqasm.load(qasm3_str)

In [6]: module.reverse_qubit_order()
Out[6]: <pyqasm.modules.Qasm3Module at 0x105bc9ac0>

In [7]: module.unrolled_qasm.splitlines()
Out[7]:
['OPENQASM 3.0;',
 'include "stdgates.inc";',
 'qubit[2] q;',
 'qubit[4] q2;',
 'qubit[1] q3;',
 'bit[1] c;',
 'cx q[1], q[0];',
 'cx q2[3], q2[2];',
 'x q2[0];',
 'cx q2[3], q2[1];',
 'x q3[0];',
 'c[0] = measure q2[3];']
 ```
 - Added the `to_qasm3()` method to the `Qasm2Module` class which can be used to convert a QASM2 program to QASM3 ([#62](https://github.com/qBraid/pyqasm/pull/62)). Usage is as follows - 
 
 ```python
 In [7]: import pyqasm

In [8]: qasm2_str = """
   ...:      OPENQASM 2.0;
   ...:      include "qelib1.inc";
   ...:      qreg q[2];
   ...:      creg c[2];
   ...:      h q[0];
   ...:      cx q[0], q[1];
   ...:      measure q -> c;
   ...:      """

In [9]: module = pyqasm.load(qasm2_str)

In [10]: module.to_qasm3(as_str = True).splitlines()
Out[10]:
['OPENQASM 3.0;',
 'include "stdgates.inc";',
 'qubit[2] q;',
 'bit[2] c;',
 'h q[0];',
 'cx q[0], q[1];',
 'c = measure q;']

In [11]: qasm3_mod = module.to_qasm3()

In [12]: qasm3_mod
Out[12]: <pyqasm.modules.qasm3.Qasm3Module at 0x107854ad0>
 ```


### Improved / Modified
- Improved qubit declaration semantics by adding check for quantum registers being declared as predefined constants ([#44](https://github.com/qBraid/pyqasm/pull/44))
- Updated pre-release scripts + workflow ([#47](https://github.com/qBraid/pyqasm/pull/47))
- Moved pylint config from pyproject to rcfile, reduced disabled list, and moved disable flags to specific areas where applicable instead of over entire files ([#47](https://github.com/qBraid/pyqasm/pull/47))
- Consolidated duplicate code from `pyqasm.unroller.py` and `pyqasm.validate.py` into `pyqasm.entrypoint.py` with new `pyqasm.load()` function which returns a `Qasm3Module` ([#47](https://github.com/qBraid/pyqasm/pull/47))
- Updated examples in `README.md` to show outputs and explain in more detail what's happening in each example ([#47](https://github.com/qBraid/pyqasm/pull/47))
- Updated the handling of qasm version string by forcing it to be `x.0` ([#48](https://github.com/qBraid/pyqasm/pull/48))
- **Major Update**: Changed the API for the `unroll` and `validate` functions. Introduced a new `load` function that returns a `QasmModule` object, which can be used to then call `unroll` and `validate`. Also added methods like `remove_measurements`, `remove_barriers`, `has_measurements` and `depth` to the `QasmModule` class ([#49](https://github.com/qBraid/pyqasm/pull/49)). Usage is as follows - 

```python
In [1]: import pyqasm

In [2]: qasm_str = """OPENQASM 3.0;
   ...:     gate custom q1, q2, q3{
   ...:         x q1;
   ...:         y q2;
   ...:         z q3;
   ...:     }
   ...:     qreg q1[2];
   ...:     qubit[2] q2;
   ...:     qubit[3] q3;
   ...:     qubit q4;
   ...:     qubit[5]   q5;
   ...:     qreg qr[3];
   ...:
   ...:     x q1[0];
   ...:     y q2[1];
   ...:     z q3;
   ...:
   ...:
   ...:     qubit[3] q6;
   ...:
   ...:     cx q6[1], q6[2];"""

In [3]: module = pyqasm.load(qasm_str)

In [4]: module.num_qubits
Out[4]: 19

In [5]: module.num_clbits
Out[5]: 0

In [6]: module.validate()

In [7]: module.unroll()

In [8]: module.unrolled_qasm.splitlines()
Out[8]:
['OPENQASM 3.0;',
 'include "stdgates.inc";',
 'qubit[2] q1;',
 'qubit[2] q2;',
 'qubit[3] q3;',
 'qubit[1] q4;',
 'qubit[5] q5;',
 'qubit[3] qr;',
 'x q1[0];',
 'y q2[1];',
 'z q3[0];',
 'z q3[1];',
 'z q3[2];',
 'qubit[3] q6;',
 'cx q6[1], q6[2];']

In [9]: module.has_measurements()
Out[9]: False

In [10]: module.remove_measurements()
Out[10]: <pyqasm.modules.Qasm3Module at 0x107406540>

In [11]: module.depth()
Out[11]: 1

```

Users can also choose to pass an `in_place=False` argument to the methods above and get a new `QasmModule` object with the applied changes - 

```python
In [1]: import pyqasm

In [2]: qasm_str = """OPENQASM 3.0;
   ...:     gate custom q1, q2, q3{
   ...:         x q1;
   ...:         y q2;
   ...:         z q3;
   ...:     }
   ...:     qreg q1[2];
   ...:     qubit[2] q2;
   ...:     qubit[3] q3;
   ...:     qubit q4;
   ...:     qubit[5]   q5;
   ...:     qreg qr[3];
   ...:
   ...:     x q1[0];
   ...:     y q2[1];
   ...:     z q3;"""

In [3]: module = pyqasm.load(qasm_str)

In [4]: module.validate()

In [5]: module_copy = module.remove_measurements(in_place=False)
```
- Restructured the `pyqasm` package to have a `modules` subpackage which contains the `QasmModule`, `Qasm2Module` and `Qasm3Module` classes ([#62](https://github.com/qBraid/pyqasm/pull/62))

### Deprecated

### Removed

### Fixed
- Bug in initial sizes of classical registers. `bit c;` was being initialized with size `32` instead of `1` ([#43](https://github.com/qBraid/pyqasm/pull/43))
- Fixed bug in the handling of classical register type. Whenever a `bit` was referenced in an expression, it was treated as a scalar when it should be treated as an element of a 1D array with type `bit` ([#44](https://github.com/qBraid/pyqasm/pull/44))

### Dependencies
- Update sphinx-autodoc-typehints requirement from <2.5,>=1.24 to >=1.24,<2.6 ([#38](https://github.com/qBraid/pyqasm/pull/38))
- Update sphinx requirement from <8.1.0,>=7.3.7 to >=7.3.7,<8.2.0 ([#39](https://github.com/qBraid/pyqasm/pull/39))
- Update sphinx-rtd-theme requirement from <3.0.0,>=2.0.0 to >=2.0.0,<4.0.0 ([#40](https://github.com/qBraid/pyqasm/pull/40))

## Past Release Notes

Archive of changelog entries from previous releases:

- [v0.0.1](https://github.com/qBraid/pyqasm/releases/tag/v0.0.1)
