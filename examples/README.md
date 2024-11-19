## PyQASM Usage Examples

### Program Unrolling

```python
from pyqasm import loads, dumps

qasm = """
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

module = loads(qasm)
module.unroll()
print(dumps(module))
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

`pyqasm.QasmModule.unroll()` simplifies a quantum program by expanding custom gate definitions and flattening complex constructs like subroutines, loops, and conditionals into basic operations. This process, also called **program flattening** or **inlining**, transforms the program into a linear sequence of qubit and classical bit declarations, gate operations, and measurements, making it easier to transpile or compile for execution on a quantum device. See the extended [Deutsch Josza program unrolling example](unroll_example.py) for more details about the OpenQASM 3 language features being "unrolled" in the above program.

### Program Validation

```python
from pyqasm import loads

program = """
OPENQASM 3;
include "stdgates.inc";

qubit[1] q;
bit[1] c;

// bad code
h q[2];

c = measure q;
"""

module = loads(program)

module.validate()
```

```text
pyqasm.exceptions.ValidationError: Index 2 out of range for register of size 1 in qubit
```

`pyqasm.QasmModule.validate()` returns `None` if the program is semantically valid, otherwise raises an Exception. Check out a more detailed [validation example](validate_example.py) for a deeper look into the capabilities of our semantic analyzer.