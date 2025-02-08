# Copyright (C) 2025 qBraid
#
# This file is part of PyQASM
#
# PyQASM is free software released under the GNU General Public License v3
# or later. You can redistribute and/or modify it under the terms of the GPL v3.
# See the LICENSE file in the project root or <https://www.gnu.org/licenses/gpl-3.0.html>.
#
# THERE IS NO WARRANTY for PyQASM, as per Section 15 of the GPL v3.

"""
Statevector simulator for PyQASM.

"""

from collections import Counter
from dataclasses import dataclass, field

import numpy as np
from openqasm3.ast import QuantumGate
from scipy import sparse

from pyqasm import loads
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


def crz(theta: float) -> np.ndarray:
    """Parameterized Controlled-Rz gate."""
    return np.array(
        [
            [1, 0, 0, 0],
            [0, 1, 0, 0],
            [0, 0, np.exp(-1j * theta / 2), 0],
            [0, 0, 0, np.exp(1j * theta / 2)],
        ],
        dtype=complex,
    )


def u3(theta: float, phi: float, lam: float) -> np.ndarray:
    """Parameterized U3 gate (generic single-qubit rotation)."""
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
    "u3": u3,
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


@dataclass(frozen=True)
class SimulatorResult:
    """Class to store the result of a statevector simulation."""

    probabilities: np.ndarray
    measurement_counts: Counter[str, int]
    final_statevector: np.ndarray


class Simulator:
    """
    Statevector simulator

    """

    def __init__(self, seed: None | int = None):
        """
        Initialize the statevector simulator.

        Parameters:
            seed (None | int): A seed to initialize the `np.random.BitGenerator`.
                If None, then fresh, unpredictable entropy will be pulled from
                the OS using `np.random.SeedSequence`.
        """
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
            # Two-qubit gate
            if control_qubit < 0 or control_qubit >= num_qubits:
                raise ValueError(f"Invalid control qubit: {control_qubit}")

            for i in range(2**num_qubits):
                if gate_name == "swap":
                    control, target = sorted((control_qubit, target_qubit))
                    bit_c = (i >> control) & 1
                    bit_t = (i >> target) & 1
                    if bit_c != bit_t:  # If control and target don't match
                        j = i ^ (1 << target)
                        # j = i ^ ((1 << control) | (1 << target)) # Flip both bits to swap states
                        full_operator[i, j] = 1.0  # Set off-diagonal element
                    else:
                        full_operator[i, i] = 1.0  # Set diagonal element
                else:
                    if (i >> control_qubit) & 1:
                        # If the control qubit is |1>, flip the target qubit
                        j = i ^ (1 << target_qubit)  # XOR to flip the target qubit
                        full_operator[i, j] = 1.0  # Apply CX gate
                    else:
                        full_operator[i, i] = 1.0  # Apply Identity
        else:
            # Single-qubit gate
            for i in range(2**num_qubits):
                if gate_name == "ry":
                    if (i & (1 << target_qubit)) == 0:
                        i1 = i
                        i0 = i1 ^ (1 << target_qubit)
                        full_operator[i0, i0] = gate[0, 0]
                        full_operator[i0, i1] = gate[0, 1]
                        full_operator[i1, i0] = gate[1, 0]
                        full_operator[i1, i1] = gate[1, 1]
                elif (i & (1 << target_qubit)) != 0:
                    i1 = i
                    i0 = i1 ^ (1 << target_qubit)
                    full_operator[i0, i0] = gate[0, 0]
                    full_operator[i0, i1] = gate[0, 1]
                    full_operator[i1, i0] = gate[1, 0]
                    full_operator[i1, i1] = gate[1, 1]

        # Convert to CSR format for efficient multiplication
        full_operator = full_operator.tocsr()
        return statevector.dot(full_operator)

    def run(self, program: QasmModule | str, shots: int = 1) -> SimulatorResult:
        """Run the statevector simulator.

        Args:
            program (QasmModule | str): The program to simulate.
            shots (int): The number of shots to simulate. Defaults to 1.

        Returns:
            SimulatorResult: The result of the simulation.

        Raises:
            ValueError: If shots is less than 0, or if the program contains
                an unsupported gate or invalid syntax.
        """
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
        counts = Counter(format(s, f"0{num_qubits}b")[::-1] for s in samples)

        return SimulatorResult(probabilities, counts, sv)
