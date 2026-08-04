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
