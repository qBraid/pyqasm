from collections import Counter

import numpy as np
from openqasm3.ast import QuantumGate
from scipy import sparse

from pyqasm.modules.base import QasmModule


def rz(theta: float) -> np.ndarray:
    """Parameterized Rz gate."""
    return np.array([[np.exp(-1j * theta / 2), 0], [0, np.exp(1j * theta / 2)]], dtype=complex)


def ry(theta: float) -> np.ndarray:
    """Parameterized Ry gate."""
    return np.array(
        [[np.cos(theta / 2), -np.sin(theta / 2)], [np.sin(theta / 2), np.cos(theta / 2)]],
        dtype=complex,
    )


def rx(theta: float) -> np.ndarray:
    """Parameterized Rx gate."""
    return np.array(
        [
            [np.cos(theta / 2), -1j * np.sin(theta / 2)],
            [-1j * np.sin(theta / 2), np.cos(theta / 2)],
        ],
        dtype=complex,
    )


def crz(theta):
    return np.array(
        [
            [1, 0, 0, 0],
            [0, 1, 0, 0],
            [0, 0, np.exp(-1j * theta / 2), 0],
            [0, 0, 0, np.exp(1j * theta / 2)],
        ],
        dtype=complex,
    )


def u(theta: float, phi: float, lam: float) -> np.ndarray:
    """Parameterized U gate (generic single-qubit rotation)."""
    return np.array(
        [
            [np.cos(theta / 2), -np.exp(1j * lam) * np.sin(theta / 2)],
            [np.exp(1j * phi) * np.sin(theta / 2), np.exp(1j * (phi + lam)) * np.cos(theta / 2)],
        ],
        dtype=complex,
    )


PARAMETERIZED_GATES = {
    "rz": rz,
    "ry": ry,
    "rx": rx,
    "crz": crz,
    "u": u,
    "u3": u,
}

NON_PARAMETERIZED_GATES: dict[str, np.ndarray] = {
    "x": np.array([[0, 1], [1, 0]], dtype=complex),
    "y": np.array([[0, -1j], [1j, 0]], dtype=complex),
    "z": np.array([[1, 0], [0, -1]], dtype=complex),
    "h": np.array([[1, 1], [1, -1]], dtype=complex) / np.sqrt(2),
    "id": np.array([[1, 0], [0, 1]], dtype=complex),
    "cx": np.array([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1], [0, 0, 1, 0]], dtype=complex),
    "cy": np.array([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, -1j], [0, 0, 1j, 0]], dtype=complex),
    "cz": np.array([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, -1]], dtype=complex),
    "swap": np.array([[1, 0, 0, 0], [0, 0, 1, 0], [0, 1, 0, 0], [0, 0, 0, 1]], dtype=complex),
    "s": np.array([[1, 0], [0, 1j]], dtype=complex),
    "t": np.array([[1, 0], [0, np.exp(1j * np.pi / 4)]], dtype=complex),
    "sdg": np.array([[1, 0], [0, -1j]], dtype=complex),
    "tdg": np.array([[1, 0], [0, np.exp(-1j * np.pi / 4)]], dtype=complex),
}


class Result:

    def __init__(self, probabilities: np.ndarray, counts: Counter[str, int] | None = None):
        self._probabilities = probabilities
        self._counts = counts or Counter()

    @property
    def probabilities(self) -> np.ndarray:
        return self._probabilities

    @property
    def measurement_counts(self) -> Counter:
        return self._counts


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
        params: list[float | int] | None,
        statevector: sparse.csr_matrix,
    ) -> sparse.csr_matrix:
        if gate_name in PARAMETERIZED_GATES:
            required_params = PARAMETERIZED_GATES[gate_name].__code__.co_argcount
            if not params or len(params) != required_params:
                raise ValueError(f"Gate {gate_name} requires {required_params} parameter(s).")
            gate = PARAMETERIZED_GATES[gate_name](*params)
        elif gate_name in NON_PARAMETERIZED_GATES:
            gate = NON_PARAMETERIZED_GATES[gate_name]
        else:
            raise ValueError(f"Gate {gate_name} not supported")

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

    def run(self, program: QasmModule | str, shots: int = 1) -> Result:
        if isinstance(program, str):
            program = loads(program)

        program.unroll()
        program.remove_idle_qubits()

        num_qubits = program.num_qubits
        statevector = self._create_statevector(num_qubits)

        for statement in program._unrolled_ast.statements:
            if isinstance(statement, QuantumGate):
                params = [arg.value for arg in statement.arguments if hasattr(arg, "value")]
                if len(statement.qubits) == 1:
                    statevector = self._apply_gate(
                        statement.name.name,
                        statement.qubits[0].indices[0][0].value,
                        None,
                        num_qubits,
                        params,
                        statevector,
                    )
                elif len(statement.qubits) == 2:
                    statevector = self._apply_gate(
                        statement.name.name,
                        statement.qubits[1].indices[0][0].value,
                        statement.qubits[0].indices[0][0].value,
                        num_qubits,
                        params,
                        statevector,
                    )

        sv = statevector.toarray()[0]

        if shots < 0:
            raise ValueError("Shots must be greater than or equal to 0.")

        probabilities = np.abs(sv) ** 2
        samples = self._rng.choice(len(probabilities), size=shots, p=probabilities)
        counts = Counter(format(s, f"0{num_qubits}b") for s in samples)

        return Result(probabilities, counts)


from pyqasm import loads

qasm = """
OPENQASM 3;
include "stdgates.inc";
qubit[2] q;
h q[0];
cx q[0], q[1];
"""

simulator = Simulator()

result = simulator.run(qasm, shots=1000)

print(result.measurement_counts)


print(result.probabilities)
