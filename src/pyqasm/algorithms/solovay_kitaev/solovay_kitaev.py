"""
Definition of the Solovay-Kitaev algorithm.
"""

from typing import List, Tuple

import numpy as np

from pyqasm.algorithms.solovay_kitaev.basic_approximation import basic_approximation
from pyqasm.algorithms.solovay_kitaev.optimizer import optimize_gate_sequence
from pyqasm.algorithms.solovay_kitaev.utils import (
    SU2Matrix,
    get_su2matrix_for_solovay_kitaev_algorithm,
)
from pyqasm.elements import BasisSet


def group_commutator(a: SU2Matrix, b: SU2Matrix) -> SU2Matrix:
    """Compute the group commutator [a,b] = aba^{-1}b^{-1}."""
    return a * b * a.dagger() * b.dagger()


def find_basic_approximation(
    target_matrix: SU2Matrix, target_basis_set, use_optimization, accuracy=1e-6, max_tree_depth=10
) -> SU2Matrix:
    """Find the basic approximation of a target matrix.

    Args:
        target_matrix (SU2Matrix): The target matrix to approximate.
        target_basis_set (BasisSet): The basis set to use for the approximation.
        use_optimization (bool): Whether to use optimization to reduce the number of gates.
        accuracy (float): The accuracy of the approximation.
        max_tree_depth (int): The maximum depth of the tree.

    Returns:
        SU2Matrix: The basic approximation of the target matrix.
    """
    gates = basic_approximation(target_matrix, target_basis_set, accuracy, max_tree_depth)
    if use_optimization:
        gates.name = optimize_gate_sequence(gates.name, target_basis_set)
    return SU2Matrix(gates.matrix, gates.name)


def decompose_group_element(
    target: SU2Matrix,
    target_gate_set,
    basic_gates: List[SU2Matrix],
    depth,
    accuracy,
    use_optimization,
) -> Tuple[List[SU2Matrix], float]:
    """Decompose a group element into a sequence of basic gates.

    Args:
        target (SU2Matrix): The target group element.
        target_gate_set (BasisSet): The target gate set.
        basic_gates (List[SU2Matrix]): The basic gates to use for the approximation.
        depth (int): The depth of the approximation.
        accuracy (float): The accuracy of the approximation.
        use_optimization (bool): Whether to use optimization to reduce the number of gates.

    Returns:
        Tuple[List[SU2Matrix], float]: The sequence of basic gates and the error.
    """

    if depth == 0:
        best_approx = find_basic_approximation(
            target.matrix, target_gate_set, use_optimization=use_optimization
        )
        return best_approx, target.distance(best_approx)

    # Recursive approximation
    prev_sequence, prev_error = decompose_group_element(
        target, target_gate_set, basic_gates, depth - 1, accuracy, use_optimization
    )

    # If previous approximation is good enough, return it
    # ERROR IS HARD CODED RIGHT NOW -> CHANGE THIS TO FIT USER-INPUT
    if prev_error < accuracy:
        return prev_sequence, prev_error

    error = target * prev_sequence.dagger()

    # Find Va and Vb such that their group commutator approximates the error
    best_v = None
    best_w = None
    best_error = float("inf")

    for v in basic_gates:
        for w in basic_gates:
            comm = group_commutator(v, w)
            curr_error = error.distance(comm)
            if curr_error < best_error:
                best_error = curr_error
                best_v = v
                best_w = w

    result = prev_sequence

    # Add correction terms
    if best_v is not None and best_w is not None:
        v_sequence, error = decompose_group_element(
            best_v, target_gate_set, basic_gates, depth - 1, accuracy, use_optimization
        )
        w_sequence, error = decompose_group_element(
            best_w, target_gate_set, basic_gates, depth - 1, accuracy, use_optimization
        )

        result = group_commutator(v_sequence, w_sequence) * prev_sequence

    final_error = target.distance(result)

    return result, final_error


def solovay_kitaev(
    target: np.ndarray, target_basis_set, depth: int = 3, accuracy=1e-6, use_optimization=True
) -> List[np.ndarray]:
    """
    Main function to run the Solovay-Kitaev algorithm.

    Args:
        target: The target unitary matrix to approximate
        target_basis_set: The basis set to use for the approximation
        depth: The depth of the approximation
        accuracy: The accuracy of the approximation
        use_optimization: Whether to use optimization to reduce the number

    Returns:
        A list of gates that approximate the target unitary matrix
    """
    # Convert inputs to SU2Matrix objects
    target_su2 = SU2Matrix(target, [])

    basic_gates_su2 = get_su2matrix_for_solovay_kitaev_algorithm(target_basis_set)

    # Run the decomposition
    sequence, _ = decompose_group_element(
        target_su2, target_basis_set, basic_gates_su2, depth, accuracy, use_optimization
    )

    if use_optimization:
        sequence.name = optimize_gate_sequence(sequence.name, target_basis_set)
        return sequence

    return sequence


if __name__ == "__main__":
    target_matrix_U = np.array([[0.70711, 0.70711j], [0.70711j, 0.70711]])

    r0 = solovay_kitaev(target_matrix_U, BasisSet.CLIFFORD_T, depth=0)
    print(r0.name)  # Output: ['s', 'h', 's']

    r1 = solovay_kitaev(target_matrix_U, BasisSet.CLIFFORD_T, depth=1)
    print(
        r1.name
    )  # Output: ['s', 's', 's', 't', 't', 'tdg', 'sdg', 'sdg', 'sdg', 'tdg', 's', 'h', 's']

    r2 = solovay_kitaev(target_matrix_U, BasisSet.CLIFFORD_T, depth=2)
    print(r2.name)  # Output: ['t', 's', 's', 's', 't',
    #             'tdg', 'tdg', 'sdg', 'sdg', 'sdg',
    #             't', 's', 's', 's', 't',
    #             'tdg', 'tdg', 'sdg', 'sdg', 'sdg',
    #             's', 'h', 's']

    print(np.allclose(r0.matrix, r1.matrix))  # Output: True
    print(np.allclose(r1.matrix, r2.matrix))  # Output: True
    print(np.allclose(r2.matrix, r0.matrix))  # Output: True
