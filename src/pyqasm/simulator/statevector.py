from typing import Optional

import numpy as np
from openqasm3.ast import QuantumGate
from scipy import sparse

from pyqasm.modules.base import QasmModule

GATES: dict[str, np.ndarray] = {
    "x": np.array([[0, 1], [1, 0]], dtype=complex),
    "y": np.array([[0, -1j], [1j, 0]], dtype=complex),
    "z": np.array([[1, 0], [0, -1]], dtype=complex),
    "h": np.array([[1, 1], [1, -1]], dtype=complex) / np.sqrt(2),
    "id": np.array([[1, 0], [0, 1]], dtype=complex),
    "cx": np.array([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1], [0, 0, 1, 0]], dtype=complex),
    "swap": np.array([[1, 0, 0, 0], [0, 0, 1, 0], [0, 1, 0, 0], [0, 0, 0, 1]], dtype=complex),
}


class StatevectorSimulator:
    def __init__(self, module: QasmModule):
        module.unroll()
        module.remove_idle_qubits()
        self.module = module
        self.num_qubits = module.num_qubits
        self.reset_statevector()

    def reset_statevector(self):
        self.statevector = sparse.lil_matrix((1, 2**self.num_qubits), dtype=complex)
        self.statevector[0, 0] = 1.0
        self.statevector = self.statevector.tocsr()

    def apply_gate(self, gate_name: str, target_qubit: int, control_qubit: Optional[int] = None):
        if gate_name not in GATES:
            raise ValueError(f"Gate {gate_name} not supported")
        gate = GATES[gate_name]

        if target_qubit < 0 or target_qubit >= self.num_qubits:
            raise ValueError(f"Invalid target qubit: {target_qubit}")

        full_operator = sparse.lil_matrix((2**self.num_qubits, 2**self.num_qubits), dtype=complex)

        if control_qubit is not None:
            if control_qubit < 0 or control_qubit >= self.num_qubits:
                raise ValueError(f"Invalid control qubit: {control_qubit}")

            # Handle two-qubit gates (CNOT and SWAP)
            for i in range(2 ** (self.num_qubits - 2)):
                i0 = i + (
                    i >> min(control_qubit, target_qubit) << (min(control_qubit, target_qubit) + 1)
                )
                i1 = i0 + (1 << min(control_qubit, target_qubit))
                i2 = i0 + (1 << max(control_qubit, target_qubit))
                i3 = i2 + (1 << min(control_qubit, target_qubit))

                if gate_name == "cx":
                    full_operator[i0, i0] = gate[0, 0]
                    full_operator[i1, i1] = gate[1, 1]
                    full_operator[i2, i2] = gate[2, 2]
                    full_operator[i3, i3] = gate[3, 3]
                    if control_qubit < target_qubit:
                        full_operator[i2, i3] = gate[2, 3]
                        full_operator[i3, i2] = gate[3, 2]
                    else:
                        full_operator[i1, i3] = gate[1, 3]
                        full_operator[i3, i1] = gate[3, 1]
                elif gate_name == "swap":
                    full_operator[i0, i0] = gate[0, 0]
                    full_operator[i1, i2] = gate[1, 2]
                    full_operator[i2, i1] = gate[2, 1]
                    full_operator[i3, i3] = gate[3, 3]
        else:
            # Single-qubit gate
            for i in range(2**self.num_qubits):
                if (i & (1 << target_qubit)) != 0:
                    i1 = i
                    i0 = i1 ^ (1 << target_qubit)
                    full_operator[i0, i0] = gate[0, 0]
                    full_operator[i0, i1] = gate[0, 1]
                    full_operator[i1, i0] = gate[1, 0]
                    full_operator[i1, i1] = gate[1, 1]
        # Convert to CSR format for efficient multiplication
        full_operator = full_operator.tocsr()
        self.statevector = self.statevector.dot(full_operator)

    def simulate(self) -> np.ndarray:
        self.reset_statevector()

        for statement in self.module._unrolled_ast.statements:
            if isinstance(statement, QuantumGate):
                if len(statement.qubits) == 1:
                    self.apply_gate(statement.name.name, statement.qubits[0].indices[0][0].value)
                elif len(statement.qubits) == 2:
                    self.apply_gate(
                        statement.name.name,
                        statement.qubits[1].indices[0][0].value,
                        statement.qubits[0].indices[0][0].value,
                    )

        return self.statevector.toarray()[0]

    def get_probabilities(self) -> np.ndarray:
        return np.abs(self.statevector.toarray()[0]) ** 2


from pyqasm import loads

qasm = """
OPENQASM 3;
include "stdgates.inc";
qubit[2] q;
h q[0];
swap q[0], q[1];
cx q[0], q[1];
"""

program = loads(qasm)

simulator = StatevectorSimulator(program)

print(simulator.simulate())
print(simulator.get_probabilities())
