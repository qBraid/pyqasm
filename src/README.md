# pyqasm

Source code for OpenQASM 3 program validator and semantic analyzer

## Supported Operations

| `openqasm3.ast` Object Type    | Supported   | Comment                |
| -------------------------------| ----------- | ---------------------- |
| QuantumMeasurementStatement    | ✅          | Completed              |
| QuantumReset                   | ✅          | Completed              |
| QuantumBarrier                 | ✅          | Completed              |
| QuantumGateDefinition          | ✅          | Completed              |
| QuantumGate                    | ✅          | Completed              |
| QuantumGateModifier            | ✅          | Completed (pow, inv)   |
| QubitDeclaration               | ✅          | Completed              |
| Clbit Declarations             | ✅          | Completed              |
| BinaryExpression               | ✅          | Completed              | 
| UnaryExpression                | ✅          | Completed              |
| ClassicalDeclaration           | ✅          | Completed              |
| ConstantDeclaration            | ✅          | Completed              |
| ClassicalAssignment            | ✅          | Completed              |
| AliasStatement                 | ✅          | Completed              |
| SwitchStatement                | ✅          | Completed              |
| BranchingStatement             | ✅          | Completed              |
| SubroutineDefinition           | ✅          | Completed              |
| ForLoops                       | ✅          | Completed              |
| RangeDefinition                | ✅          | Completed              |
| QuantumGate                    | ✅          | Completed              |
| Cast                           | ✅          | Completed              |
| QuantumGateModifier (ctrl)     | ✅          | Completed              |
| WhileLoop                      | ✅          | Completed              |
| IODeclaration                  | 📋          | Planned                |
| Pragma                         | ✅          | Preserved as-is        |
| Annotation                     | 📋          | Planned                |
| DurationType                   | ✅          | Completed              |
| StretchType                    | ✅          | Completed              |
| DelayInstruction               | ✅          | Completed              |
| Box                            | ✅          | Completed              |
| CalibrationStatement           | ✅          | Completed              |
| CalibrationDefinition          | ✅          | Completed              |
| ComplexType                    | ✅          | Completed              |
| AngleType                      | ✅          | Completed              |
| ExternDeclaration              | ✅          | Completed              |

## Pragmas

A pragma body is opaque text. pyqasm copies it to the output unchanged and never parses
it, with one exception: `#pragma braket verbatim` marks the `box` that immediately
follows it, and gates inside that box are emitted as written rather than decomposed.

Two consequences worth knowing before relying on them:

- **Qubit-renumbering passes do not rewrite pragmas.** `remove_idle_qubits()`,
  `reverse_qubit_order()` and `unroll(consolidate_qubits=True)` renumber qubits in the
  program but not inside pragma text, so a pragma naming qubits by index — say
  `#pragma braket noise bit_flip(0.1) q[3]` — can end up on a different qubit than the
  one it was written for, or outside the declared register. The output is still valid
  QASM, so nothing raises.
- **A verbatim box should contain only device-native gates.** That is what Braket
  verbatim boxes are for, and pyqasm does not enforce it: a user-defined gate inside a
  verbatim box is emitted as a call while unrolling drops its `gate` definition, so the
  output does not load back into pyqasm.
