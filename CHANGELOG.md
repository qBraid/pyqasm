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
- Introduced a new environment variable called `PYQASM_EXPAND_TRACEBACK`. This variable can be set to `true` / `false` to enable / disable the expansion of traceback information in the error messages. The default is set as `false`. ([#171](https://github.com/qBraid/pyqasm/issues/171)) Eg. - 

**Script** - 
```python
import pyqasm

qasm = """
    OPENQASM 3;
    include "stdgates.inc";
    qubit[2] q1;
    rx(a) q1;
    """

program = pyqasm.loads(qasm)
program.unroll()
``` 

**Execution** - 
```bash
>>> python3 test-traceback.py
```

```bash
ERROR:pyqasm: Error at line 5, column 7 in QASM file

 >>>>>> a

ERROR:pyqasm: Error at line 5, column 4 in QASM file

 >>>>>> rx(a) q1[0], q1[1];


pyqasm.exceptions.ValidationError: Undefined identifier 'a' in expression

The above exception was the direct cause of the following exception:

pyqasm.exceptions.ValidationError: Invalid parameter 'a' for gate 'rx'
```
```bash
>>> export PYQASM_EXPAND_TRACEBACK=true
```

```bash
>>> python3 test-traceback.py
```

```bash
ERROR:pyqasm: Error at line 5, column 7 in QASM file

 >>>>>> a

ERROR:pyqasm: Error at line 5, column 4 in QASM file

 >>>>>> rx(a) q1[0], q1[1];


Traceback (most recent call last):
  .....

  File "/Users/thegupta/Desktop/qBraid/repos/pyqasm/src/pyqasm/expressions.py", line 69, in _check_var_in_scope
    raise_qasm3_error(
  File "/Users/thegupta/Desktop/qBraid/repos/pyqasm/src/pyqasm/exceptions.py", line 103, in raise_qasm3_error
    raise err_type(message)

pyqasm.exceptions.ValidationError: Undefined identifier 'a' in expression

The above exception was the direct cause of the following exception:


Traceback (most recent call last):
  .....

  File "/Users/thegupta/Desktop/qBraid/repos/pyqasm/src/pyqasm/visitor.py", line 2208, in visit_basic_block
    result.extend(self.visit_statement(stmt))
                  ^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/thegupta/Desktop/qBraid/repos/pyqasm/src/pyqasm/visitor.py", line 2188, in visit_statement
    result.extend(visitor_function(statement))  # type: ignore[operator]
                  ^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/thegupta/Desktop/qBraid/repos/pyqasm/src/pyqasm/visitor.py", line 1201, in _visit_generic_gate_operation
    result.extend(self._visit_basic_gate_operation(operation, inverse_value, ctrls))
                  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/thegupta/Desktop/qBraid/repos/pyqasm/src/pyqasm/visitor.py", line 820, in _visit_basic_gate_operation
    op_parameters = self._get_op_parameters(operation)
                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/thegupta/Desktop/qBraid/repos/pyqasm/src/pyqasm/visitor.py", line 660, in _get_op_parameters
    raise_qasm3_error(
  File "/Users/thegupta/Desktop/qBraid/repos/pyqasm/src/pyqasm/exceptions.py", line 102, in raise_qasm3_error
    raise err_type(message) from raised_from

pyqasm.exceptions.ValidationError: Invalid parameter 'a' for gate 'rx'
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

- Enhanced the verbosity and clarity of `pyqasm` validation error messages. The new error format logs the line and column number of the error, the line where the error occurred, and the specific error message, making it easier to identify and fix issues in the QASM code. ([#171](https://github.com/qBraid/pyqasm/issues/171)) Eg. - 

```python
import pyqasm

qasm = """
    OPENQASM 3;
    include "stdgates.inc";
    qubit[2] q1;
    rx(a) q1;
    """

program = pyqasm.loads(qasm)
program.unroll()
``` 

```bash
ERROR:pyqasm: Error at line 5, column 7 in QASM file

 >>>>>> a

ERROR:pyqasm: Error at line 5, column 4 in QASM file

 >>>>>> rx(a) q1[0], q1[1];


pyqasm.exceptions.ValidationError: Undefined identifier 'a' in expression

The above exception was the direct cause of the following exception:

pyqasm.exceptions.ValidationError: Invalid parameter 'a' for gate 'rx'
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
