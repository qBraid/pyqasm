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
| Pragma                         | 📋          | Planned                |
| Annotation                     | 📋          | Planned                |
| DurationType                   | ✅          | Planned                |
| StretchType                    | ✅          | Planned                |
| DelayInstruction               | ✅          | Planned                |
| Box                            | ✅          | Planned                |
| CalibrationStatement           | 📋          | Planned                |
| CalibrationDefinition          | 📋          | Planned                |
| ComplexType                    | 📋          | Planned                |
| AngleType                      | 📋          | Planned                |
| ExternDeclaration              | 📋          | Planned                |
