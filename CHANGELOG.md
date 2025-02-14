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
- Added support for classical declarations with measurement ([#120](https://github.com/qBraid/pyqasm/pull/120)). Usage example -

```python
In [1]: from pyqasm import loads, dumps

In [2]: module = loads(
   ...: """OPENQASM 3.0;
   ...: qubit q;
   ...: bit b = measure q;
   ...: """)

In [3]: module.unroll()

In [4]: dumps(module).splitlines()
Out[4]: ['OPENQASM 3.0;', 'qubit[1] q;', 'bit[1] b;', 'b[0] = measure q[0];']
```

- Added support for `gphase`, `toffoli`, `not`, `c3sx` and `c4x` gates ([#86](https://github.com/qBraid/pyqasm/pull/86))
- Added a `remove_includes` method to `QasmModule` to remove include statements from the generated QASM code ([#100](https://github.com/qBraid/pyqasm/pull/100)). Usage example - 

```python
In [1]: from pyqasm import loads

In [2]: module = loads(
   ...: """OPENQASM 3.0;
   ...: include "stdgates.inc";
   ...: include "random.qasm";
   ...: 
   ...: qubit[2] q;
   ...: h q;
   ...: """)

In [3]: module.remove_includes()
Out[3]: <pyqasm.modules.qasm3.Qasm3Module at 0x10442b190>

In [4]: from pyqasm import dumps

In [5]: dumps(module).splitlines()
Out[5]: ['OPENQASM 3.0;', 'qubit[2] q;', 'h q;']
```
- Added support for unrolling multi-bit branching with `==`, `>=`, `<=`, `>`, and `<` ([#112](https://github.com/qBraid/pyqasm/pull/112)). Usage example -
```python
In [1]: from pyqasm import loads

In [2]: module = loads(
   ...: """OPENQASM 3.0;
   ...: include "stdgates.inc";
   ...: qubit[1] q;
   ...: bit[4] c;
   ...: if(c == 3){
   ...:     h q[0];
   ...: }
   ...: """)

In [3]: module.unroll()

In [4]: dumps(module)
OPENQASM 3.0;
include "stdgates.inc";
qubit[1] q;
bit[4] c;
if (c[0] == false) {
  if (c[1] == false) {
    if (c[2] == true) {
      if (c[3] == true) {
        h q[0];
      }
    }
  }
}
```
- Add formatting check for Unix style line endings i.e. `\n`. For any other line endings, errors are raised. ([#130](https://github.com/qBraid/pyqasm/pull/130))
- Add `rebase` method to the `QasmModule`. Users now have the ability to rebase the quantum programs to any of the available `pyqasm.elements.BasisSet` ([#123](https://github.com/qBraid/pyqasm/pull/123)). Usage example - 

```python
In [9] : import pyqasm

In [10]: qasm_input = """ OPENQASM 3.0;
    ...: include "stdgates.inc";
    ...: qubit[2] q;
    ...: bit[2] c;
    ...: 
    ...: h q;
    ...: x q;
    ...: cz q[0], q[1];
    ...: 
    ...: c = measure q; 
    ...: """

In [11]: module = pyqasm.loads(qasm_input)

In [12]: from pyqasm.elements import BasisSet

In [13]: module.rebase(target_basis_set=BasisSet.ROTATIONAL_CX)
Out[13]: <pyqasm.modules.qasm3.Qasm3Module at 0x103744e10>

In [14]: print(pyqasm.dumps(module))
OPENQASM 3.0;
include "stdgates.inc";
qubit[2] q;
bit[2] c;
ry(1.5707963267948966) q[0];
rx(3.141592653589793) q[0];
ry(1.5707963267948966) q[1];
rx(3.141592653589793) q[1];
rx(3.141592653589793) q[0];
rx(3.141592653589793) q[1];
ry(1.5707963267948966) q[1];
rx(3.141592653589793) q[1];
cx q[0], q[1];
ry(1.5707963267948966) q[1];
rx(3.141592653589793) q[1];
c[0] = measure q[0];
c[1] = measure q[1];
```

Current support for `BasisSet.CLIFFORD_T` decompositions is limited to non-parameterized gates only. 
- Added `.gitattributes` file to specify unix-style line endings(`\n`) for all files ([#123](https://github.com/qBraid/pyqasm/pull/123))
- Added support for `ctrl` modifiers. QASM3 programs with `ctrl @` modifiers can now be loaded as `QasmModule` objects ([#121](https://github.com/qBraid/pyqasm/pull/121)). Usage example - 

```python
In [18]: import pyqasm

In [19]: qasm3_string = """
    ...:     OPENQASM 3.0;
    ...:     include "stdgates.inc";
    ...:     qubit[3] q;
    ...:     gate custom a, b, c {
    ...:         ctrl @ x a, b;
    ...:         ctrl(2) @ x a, b, c;
    ...:     }
    ...:     custom q[0], q[1], q[2];
    ...:     """

In [20]: module = pyqasm.loads(qasm3_string)

In [21]: module.unroll()

In [22]: print(pyqasm.dumps(module))
OPENQASM 3.0;
include "stdgates.inc";
qubit[3] q;
cx q[0], q[1];
ccx q[0], q[1], q[2];
```

### Improved / Modified
 - Refactored the initialization of `QasmModule` to remove default include statements. Only user supplied include statements are now added to the generated QASM code ([#86](https://github.com/qBraid/pyqasm/pull/86))
- Update the `pre-release.yml` workflow to multi-platform builds. Added the pre-release version bump to the `pre_build.sh` script. ([#99](https://github.com/qBraid/pyqasm/pull/99))
- Bumped qBraid-CLI dep in `tox.ini` to fix `qbraid headers` command formatting bug ([#129](https://github.com/qBraid/pyqasm/pull/129))

### Deprecated

### Removed
- Unix-style line endings check in GitHub actions was removed in lieu of the `.gitattributes` file ([#123](https://github.com/qBraid/pyqasm/pull/123))

### Fixed
- Fixed bugs in implementations of `gpi2` and `prx` gates ([#86](https://github.com/qBraid/pyqasm/pull/86))

### Dependencies
- Update sphinx-autodoc-typehints requirement from <2.6,>=1.24 to >=1.24,<3.1 ([#119](https://github.com/qBraid/pyqasm/pull/119))

## Past Release Notes

Archive of changelog entries from previous releases:

- [v0.1.0](https://github.com/qBraid/pyqasm/releases/tag/v0.1.0)
- [v0.1.0-alpha](https://github.com/qBraid/pyqasm/releases/tag/v0.1.0-alpha)
- [v0.0.3](https://github.com/qBraid/pyqasm/releases/tag/v0.0.3)
- [v0.0.2](https://github.com/qBraid/pyqasm/releases/tag/v0.0.2)
- [v0.0.1](https://github.com/qBraid/pyqasm/releases/tag/v0.0.1)
