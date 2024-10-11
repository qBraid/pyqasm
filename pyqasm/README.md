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
| BranchingStatement             | 🔜          | In progress            |
| SubroutineDefinition           | 🔜          | In progress            |
| Looping statements(eg. for)    | 🔜          | In progress            |
| RangeDefinition                | 🔜          | In progress            |
| IODeclaration                  | 📋          | Planned                |
| Pragma                         | ❓          | Unsure                 |
| Annotations                    | ❓          | Unsure                 |
| Pulse-level ops (e.g. delay)   | ❌          | Not supported by QIR   |
| Calibration ops                | ❌          | Not supported by QIR   |
| Duration literals              | ❌          | Not supported by QIR   |
| ComplexType                    | ❌          | Not supported by QIR   |
