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
}


class StatevectorSimulator:
    def __init__(self, module: QasmModule):
        self.module = module
        self.num_qubits = module.num_qubits
        self.reset_statevector()

    def reset_statevector(self):
        self.statevector = sparse.csr_matrix((1, 2**self.num_qubits), dtype=complex)
        self.statevector[0, 0] = 1.0

    def apply_gate(
        self, gate_name: str, target_qubit: int, control_qubits: Optional[list[int]] = None
    ):
        if gate_name not in GATES:
            raise ValueError(f"Gate {gate_name} not supported")
        gate = GATES[gate_name]

        if target_qubit < 0 or target_qubit >= self.num_qubits:
            raise ValueError(f"Invalid target qubit: {target_qubit}")

        if control_qubits:
            # Implement controlled gates here
            pass
        else:
            full_operator = sparse.eye(2**self.num_qubits, dtype=complex)
            full_operator = full_operator.tolil()
            for i in range(2 ** (self.num_qubits - 1)):
                i0 = i + (i >> target_qubit << (target_qubit + 1))
                i1 = i0 + (1 << target_qubit)
                full_operator[i0, i0] = gate[0, 0]
                full_operator[i0, i1] = gate[0, 1]
                full_operator[i1, i0] = gate[1, 0]
                full_operator[i1, i1] = gate[1, 1]
            full_operator = full_operator.tocsr()

            self.statevector = self.statevector.dot(full_operator)

    def simulate(self) -> np.ndarray:
        self.reset_statevector()
        self.module.unroll()

        for statement in self.module._unrolled_ast.statements:
            if isinstance(statement, QuantumGate):
                try:
                    self.apply_gate(
                        statement.name.name, statement.qubits[0].indices[0][0].value + 1
                    )
                except ValueError as e:
                    raise e

        return self.statevector.toarray()[0]

    def get_probabilities(self) -> np.ndarray:
        return np.abs(self.statevector.toarray()[0]) ** 2


from pyqasm import loads

qasm = """
OPENQASM 3;
include "stdgates.inc";
qubit[2] q;
h q[0];
"""

program = loads(qasm)

simulator = StatevectorSimulator(program)

print(simulator.simulate())  # [1.+0.j 0.+0.j 0.+0.j 0.+0.j]
print(simulator.get_probabilities())  # [1. 0. 0. 0.]
