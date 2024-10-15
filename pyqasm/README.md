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
| Looping statements(eg. for)    | ✅          | Completed              |
| RangeDefinition                | ✅          | Completed              |
| QuantumGate                    | ✅          | Completed              |
| QuantumGateModifier (ctrl)     | 📋          | Planned                |
| IODeclaration                  | 📋          | Planned                |
| Pragma                         | 📋          | Planned                |
| Annotations                    | 📋          | Planned                |
| Pulse-level ops (e.g. delay)   | 📋          | Planned                |
| Calibration ops                | 📋          | Planned                |
| Duration literals              | 📋          | Planned                |
| ComplexType                    | 📋          | Planned                |
