from typing import List

import numpy as np

from pyqasm.elements import BasisSet
from pyqasm.maps.gates import GATE_ENTITY_DATA, SELF_INVERTING_ONE_QUBIT_OP_SET, ST_GATE_INV_MAP


class SU2Matrix:
    """Class representing a 2x2 Special Unitary matrix."""

    def __init__(self, matrix: np.ndarray, name: List[str]):
        self.matrix = matrix
        self.name = name

    def __mul__(self, other: "SU2Matrix") -> "SU2Matrix":
        matrix = np.dot(self.matrix, other.matrix)
        name = self.name.copy()
        name.extend(other.name)
        return SU2Matrix(matrix, name)

    def dagger(self) -> "SU2Matrix":
        """Returns the conjugate transpose."""
        matrix = self.matrix.conj().T
        name = []
        for n in self.name[::-1]:
            name.append(self._get_dagger_gate_name(n))

        return SU2Matrix(matrix, name)

    def distance(self, other: "SU2Matrix") -> float:
        """Calculates the operator norm distance between two matrices."""
        diff = self.matrix - other.matrix
        return np.linalg.norm(diff)

    def _get_dagger_gate_name(self, name: str):
        if name in SELF_INVERTING_ONE_QUBIT_OP_SET:
            return name
        else:
            return ST_GATE_INV_MAP[name]

    def __str__(self):
        return f"name: {self.name}, matrix: {self.matrix}"


class TU2Matrix:
    def __init__(
        self, matrix: np.ndarray, name: List[str], identity_group: str, identity_weight: float
    ):
        self.matrix = matrix
        self.name = name
        self.identity_group = identity_group
        self.identity_weight = identity_weight

    def __mul__(self, other: "TU2Matrix") -> "TU2Matrix":
        matrix = np.dot(self.matrix, other.matrix)
        name = self.name.copy()
        name.extend(other.name)
        identity_weight = 0
        identity_group = ""
        if self.identity_group == other.identity_group:
            identity_weight = self.identity_weight + other.identity_weight
        else:
            identity_group = other.identity_group
            identity_weight = other.identity_weight

        return TU2Matrix(matrix, name, identity_group, identity_weight)

    def can_multiple(self, other: "TU2Matrix"):
        if self.identity_group != other.identity_group:
            return True

        if self.identity_weight + other.identity_weight < 1:
            return True

        return False

    def get_diff(self, U):
        # trace_diff = np.abs(np.trace(np.dot(self.matrix.conj().T, U) - np.identity(2)))
        diff = np.linalg.norm(self.matrix - U, 2)
        return diff

    def __str__(self):
        # return f"name: {self.name}"
        return f"name: {self.name}, matrix: {self.matrix}"

    def copy(self) -> "TU2Matrix":
        return TU2Matrix(
            self.matrix.copy(), self.name.copy(), self.identity_group, self.identity_weight
        )


def get_SU2Matrix_for_solovay_kitaev_algorithm(target_basis_set) -> List[SU2Matrix]:
    gate_list = GATE_ENTITY_DATA[target_basis_set]
    return [SU2Matrix(gate["matrix"], [gate["name"]]) for gate in gate_list]


def get_TU2Matrix_for_basic_approximation(target_basis_set) -> List[TU2Matrix]:
    whole_gate_list = GATE_ENTITY_DATA[target_basis_set]
    required_gate_list = [gate for gate in whole_gate_list if gate["used_for_basic_approximation"]]

    return [
        TU2Matrix(
            gate["matrix"], [gate["name"]], gate["identity"]["group"], gate["identity"]["weight"]
        )
        for gate in required_gate_list
    ]


if __name__ == "__main__":
    result = get_SU2Matrix_for_solovay_kitaev_algorithm(BasisSet.CLIFFORD_T)
    for i in result:
        print(i)
