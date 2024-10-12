# OpenQASM 3 to QIR

## Supported conversions status table

| openqasm3.ast Object Type      | Supported   | Comment                |
| -------------------------------| ----------- | ---------------------- |
| QuantumMeasurementStatement    | ✅          | Complete               |
| QuantumReset                   | ✅          | Complete               |
| QuantumBarrier                 | ✅          | Complete               |
| QuantumGateDefinition          | ✅          | Complete               |
| QuantumGate                    | ✅          | Complete               |
| QuantumGateModifier            | ✅          | Complete (pow, inv)    |
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
| QuantumGate                    | ✅          | Complete               |
| QuantumGateModifier (ctrl)     | 📋          | Planned                |
| IODeclaration                  | 📋          | Planned                |
| Pragma                         | 📋          | Planned                |
| Annotations                    | 📋          | Planned                |
| Pulse-level ops (e.g. delay)   | 📋          | Planned                |
| Calibration ops                | 📋          | Planned                |
| Duration literals              | 📋          | Planned                |
| ComplexType                    | 📋          | Planned                |
