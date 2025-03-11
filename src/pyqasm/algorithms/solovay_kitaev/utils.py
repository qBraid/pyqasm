"""
Definition of common utility functions for the Solovay-Kitaev algorithm.
"""

from typing import List

import numpy as np

from pyqasm.elements import BasisSet
from pyqasm.maps.gates import GATE_OPT_DATA, SELF_INVERTING_ONE_QUBIT_OP_SET, ST_GATE_INV_MAP


class SU2Matrix:
    """Class representing a 2x2 Special Unitary matrix.

    Used for the Solovay-Kitaev algorithm.
    """

    def __init__(self, matrix: np.ndarray, name: List[str]):
        self.matrix = matrix
        self.name = name

    def __mul__(self, other: "SU2Matrix") -> "SU2Matrix":
        """Calculates the dot product of two matrices, and stores them with the combined name.

        Args:
            other (SU2Matrix): The other matrix.

        Returns:
            SU2Matrix: The product of the two matrices.
        """
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
        return np.linalg.norm(self.matrix - other.matrix, 2)

    def _get_dagger_gate_name(self, name: str):
        """Returns the name of the dagger gate."""
        if name in SELF_INVERTING_ONE_QUBIT_OP_SET:
            return name

        return ST_GATE_INV_MAP[name]

    def __str__(self):
        return f"name: {self.name}, matrix: {self.matrix}"


class TU2Matrix:
    """Class representing a 2x2 Traversal Unitary matrix.

    Used for basic approximation in the Solovay-Kitaev algorithm.
    """

    def __init__(
        self, matrix: np.ndarray, name: List[str], identity_group: str, identity_weight: float
    ):
        self.matrix = matrix
        self.name = name
        self.identity_group = identity_group
        self.identity_weight = identity_weight

    def __mul__(self, other: "TU2Matrix") -> "TU2Matrix":
        """Calculates the dot product of two matrices, and stores them with the combined name.
        Adds the identity weight if the identity group is the same.
        Updates the identity group and weight if the identity group is different.
        Args:
            other (TU2Matrix): The other matrix.

        Returns:
            TU2Matrix: The product of the two matrices.
        """
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
        """Checks if the two matrices can be multiplied.
        If the identity group is the same, the identity weight should be less than 1.
        """
        if self.identity_group != other.identity_group:
            return True

        return self.identity_weight + other.identity_weight < 1

    def distance(self, other):
        """Calculates the operator norm distance between two matrices."""
        return np.linalg.norm(self.matrix - other, 2)

    def __str__(self):
        return f"""name: {self.name},
            matrix: {self.matrix},
            group: {self.identity_group},
            weight: {self.identity_weight}"""

    def copy(self) -> "TU2Matrix":
        """Returns a copy of the current matrix."""
        return TU2Matrix(
            self.matrix.copy(), self.name.copy(), self.identity_group, self.identity_weight
        )


def get_su2matrix_for_solovay_kitaev_algorithm(target_basis_set) -> List[SU2Matrix]:
    """Returns a list of SU2Matrix objects for the given basis set.
    This list is used for the Solovay-Kitaev algorithm.
    """
    gate_list = GATE_OPT_DATA[target_basis_set]
    return [SU2Matrix(gate["matrix"], [gate["name"]]) for gate in gate_list]


def get_tu2matrix_for_basic_approximation(target_basis_set) -> List[TU2Matrix]:
    """Returns a list of TU2Matrix objects for the given basis set.
    This list is used for the basic approximation algorithm.
    """
    whole_gate_list = GATE_OPT_DATA[target_basis_set]
    required_gate_list = [gate for gate in whole_gate_list if gate["used_for_basic_approximation"]]

    return [
        TU2Matrix(
            gate["matrix"], [gate["name"]], gate["identity"]["group"], gate["identity"]["weight"]
        )
        for gate in required_gate_list
    ]


def get_identity_weight_group_for_optimizer(target_basis_set):
    """Returns the identity weight group for the given basis set.
    This is used for the optimization of the gate sequence.
    """
    gate_list = GATE_OPT_DATA[target_basis_set]
    identity_weight_group = {}

    for gate in gate_list:
        identity_weight_group[gate["name"]] = {
            "group": gate["identity"]["group"],
            "weight": gate["identity"]["weight"],
        }

    return identity_weight_group


if __name__ == "__main__":
    result = get_identity_weight_group_for_optimizer(BasisSet.CLIFFORD_T)
    print(result)
