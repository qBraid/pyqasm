"""
Definition of the basic approximation algorithm for the Solovay-Kitaev theorem.
"""

import numpy as np

from pyqasm.algorithms.solovay_kitaev.utils import TU2Matrix, get_tu2matrix_for_basic_approximation
from pyqasm.elements import BasisSet


def rescursive_traversal(
    target_matrix, approximated_matrix, target_gate_set_list, current_depth, params
):
    """Recursively traverse the tree to find the best approximation of the target matrix.
    Args:
        target_matrix (np.ndarray): The target matrix to approximate.
        approximated_matrix (TU2Matrix): The approximated matrix.
        target_gate_set_list (list): The list of target gates to approximate.
        current_depth (int): The current depth of the tree.
        params (tuple): The parameters for the approximation.

    Returns:
        float: The closest difference between the target and approximated matrix.
        TU2Matrix: The closest approximated matrix.
        TU2Matrix: The best approx

    """
    accuracy, max_tree_depth, best_gate = params

    if current_depth >= max_tree_depth :
        return best_gate

    for gate in target_gate_set_list:
        if not approximated_matrix.can_multiple(gate):
            continue
        approximated_matrix_copy = approximated_matrix.copy()
        approximated_matrix = approximated_matrix * gate

        diff = approximated_matrix.distance(target_matrix)
        if diff < accuracy:
            best_gate = approximated_matrix.copy()
            return  best_gate

        # Update the closest gate if the current one is closer
        if diff < best_gate.distance(target_matrix):
            best_gate = approximated_matrix.copy()

        best_gate = rescursive_traversal(
            target_matrix,
            approximated_matrix.copy(),
            target_gate_set_list,
            current_depth + 1,
            (accuracy, max_tree_depth, best_gate),
        )
        approximated_matrix = approximated_matrix_copy.copy()

    return best_gate


def basic_approximation(target_matrix, target_gate_set, accuracy=0.001, max_tree_depth=3):
    """Approximate the target matrix using the basic approximation algorithm.

    Args:
        target_matrix (np.ndarray): The target matrix to approximate.
        target_gate_set (BasisSet): The target gate set to approximate.
        accuracy (float): The accuracy of the approximation.
        max_tree_depth (int): The maximum depth of the tree.

    Returns:
        TU2Matrix: The approximated matrix.
    """
    approximated_matrix = TU2Matrix(np.identity(2), [], None, None)
    target_gate_set_list = get_tu2matrix_for_basic_approximation(target_gate_set)
    current_depth = 0
    best_gate = TU2Matrix(np.identity(2), [], None, None)

    params = (accuracy, max_tree_depth, best_gate)

    best_gate = rescursive_traversal(
        target_matrix, approximated_matrix.copy(), target_gate_set_list, current_depth, params
    )
    
    return best_gate

    # result = None

    # if best_gate:
    #     result = best_gate.copy()
    # else:
    #     result = closest_gate.copy()

    # return result


if __name__ == "__main__":
    target_matrix_U = np.array([[0.70711, 0.70711j], [0.70711j, 0.70711]])

    print(basic_approximation(target_matrix_U, BasisSet.CLIFFORD_T, 0.0001, 3))
