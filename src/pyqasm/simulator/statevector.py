from collections import Counter

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


class Result:

    def __init__(self, sv: np.ndarray, counts: Counter[str] | None):
        self.sv = sv
        self.counts = counts

    def probabilities(self) -> np.ndarray:
        return np.abs(self.sv) ** 2

    def get_counts(self) -> Counter:
        return self.counts or Counter()


class Simulator:

    def __init__(self, seed: int | None = None):
        self._rng = np.random.default_rng(seed)

    def _create_statevector(self, num_qubits: int) -> sparse.csr_matrix:
        statevector = sparse.lil_matrix((1, 2**num_qubits), dtype=complex)
        statevector[0, 0] = 1.0
        return statevector.tocsr()

    def _apply_gate(
        self,
        gate_name: str,
        target_qubit: int,
        control_qubit: int | None,
        num_qubits: int,
        statevector: sparse.csr_matrix,
    ) -> sparse.csr_matrix:
        if gate_name not in GATES:
            raise ValueError(f"Gate {gate_name} not supported")
        gate = GATES[gate_name]

        if target_qubit < 0 or target_qubit >= num_qubits:
            raise ValueError(f"Invalid target qubit: {target_qubit}")

        full_operator = sparse.lil_matrix((2**num_qubits, 2**num_qubits), dtype=complex)

        if control_qubit is not None:
            if control_qubit < 0 or control_qubit >= num_qubits:
                raise ValueError(f"Invalid control qubit: {control_qubit}")

            # Handle two-qubit gates (CNOT and SWAP)
            for i in range(2 ** (num_qubits - 2)):
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
            for i in range(2**num_qubits):
                if (i & (1 << target_qubit)) != 0:
                    i1 = i
                    i0 = i1 ^ (1 << target_qubit)
                    full_operator[i0, i0] = gate[0, 0]
                    full_operator[i0, i1] = gate[0, 1]
                    full_operator[i1, i0] = gate[1, 0]
                    full_operator[i1, i1] = gate[1, 1]

        # Convert to CSR format for efficient multiplication
        full_operator = full_operator.tocsr()
        return statevector.dot(full_operator)

    def run(self, module: QasmModule, shots: int | None = None) -> Result:
        module.unroll()
        module.remove_idle_qubits()

        num_qubits = module.num_qubits
        statevector = self._create_statevector(num_qubits)

        for statement in module._unrolled_ast.statements:
            if isinstance(statement, QuantumGate):
                if len(statement.qubits) == 1:
                    statevector = self._apply_gate(
                        statement.name.name,
                        statement.qubits[0].indices[0][0].value,
                        None,
                        num_qubits,
                        statevector,
                    )
                elif len(statement.qubits) == 2:
                    statevector = self._apply_gate(
                        statement.name.name,
                        statement.qubits[1].indices[0][0].value,
                        statement.qubits[0].indices[0][0].value,
                        num_qubits,
                        statevector,
                    )

        sv = statevector.toarray()[0]

        counts = None
        if shots is not None:
            if shots > 0:
                probabilities = np.abs(sv) ** 2
                samples = self._rng.choice(len(probabilities), size=shots, p=probabilities)
                counts = Counter(format(s, f"0{num_qubits}b") for s in samples)
            elif shots < 0:
                raise ValueError("Shots must be non-negative")

        return Result(statevector, counts)


from pyqasm import loads

qasm = """
OPENQASM 3;
include "stdgates.inc";
qubit[2] q;
h q[0];
cx q[0], q[1];
"""

program = loads(qasm)

simulator = Simulator()

result = simulator.run(program, shots=1000)

print(result.get_counts())
