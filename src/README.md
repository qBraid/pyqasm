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
| opaque (OpenQASM 2 only)       | ✅          | Emitted as written     |

## Opaque gates

`opaque NAME(params) qubits;` is OpenQASM 2 syntax that was removed in OpenQASM 3. It
declares a hardware primitive: a gate with a name and an arity and no decomposition.
Quantinuum's `hqslib1.inc` opens with six of them.

pyqasm rewrites the declaration before parsing and records the name, so `validate()`,
`depth()`, `has_measurements()` and the qubit-renumbering passes all work. A call to an
opaque gate is emitted as written rather than unrolled, and counts as one layer of depth,
exactly as an external gate does. `unroll()` never drops that treatment: unlike
`external_gates`, which the caller sets per call, an opaque gate is a property of the
program and has no decomposition to fall back on.

Two things to know:

- **The declaration is not re-emitted.** Unrolling drops it, the same way it drops the
  `gate` definition of an external gate, so the output carries calls to a gate it does
  not declare and does not load back into pyqasm on its own.
- **`opaque` in an OpenQASM 3 program is still a parse error.** The rewrite is gated on
  the `OPENQASM 2` header, because the keyword is not OpenQASM 3 syntax.
- **`rebase()` reports it as unsupported.** An opaque primitive has no decomposition, so
  it cannot be rewritten onto a standard basis set; it reaches the existing
  unsupported-gate path and is named there.
- **`to_qasm3()` refuses a program that declares one.** OpenQASM 3 removed `opaque` and
  has no equivalent for a gate with no decomposition, and a body-less `gate` in
  OpenQASM 3 means the identity — so converting would silently turn each hardware
  primitive into a no-op.

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
