import numpy as np

from pyqasm.algorithms.solovay_kitaev.utils import TU2Matrix, get_TU2Matrix_for_basic_approximation
from pyqasm.elements import BasisSet

# Constants
best_gate = None
closest_gate = None
closest_diff = float("inf")


def rescursive_traversal(
    U, A, target_gate_set_list, current_depth, accuracy=0.001, max_tree_depth=3
):
    if current_depth >= max_tree_depth:
        return

    global closest_diff, closest_gate, best_gate

    if best_gate:
        return

    for gate in target_gate_set_list:
        if not A.can_multiple(gate):
            continue
        A_copy = A.copy()
        A = A * gate

        diff = A.get_diff(U)
        if diff < accuracy:
            best_gate = A.copy()
            return best_gate

        # Update the closest gate if the current one is closer
        if diff < closest_diff:
            closest_diff = diff
            closest_gate = A.copy()

        # print(A.name)
        # if A.name == ['s', 'h', 's']:
        #     print(A)
        #     print(diff)
        rescursive_traversal(
            U, A.copy(), target_gate_set_list, current_depth + 1, accuracy, max_tree_depth
        )
        A = A_copy.copy()

    pass


def basic_approximation(U, target_gate_set, accuracy=0.001, max_tree_depth=3):
    global closest_diff, closest_gate, best_gate

    A = TU2Matrix(np.identity(2), [], None, None)
    target_gate_set_list = get_TU2Matrix_for_basic_approximation(target_gate_set)
    current_depth = 0
    rescursive_traversal(U, A.copy(), target_gate_set_list, current_depth, accuracy, max_tree_depth)

    result = None

    if best_gate:
        result = best_gate.copy()
    else:
        result = closest_gate.copy()

    # Reset global variables
    best_gate = None
    closest_gate = None
    closest_diff = float("inf")

    return result


if __name__ == "__main__":
    U = np.array([[0.70711, 0.70711j], [0.70711j, 0.70711]])

    print(basic_approximation(U, BasisSet.CLIFFORD_T, 0.0001, 3))
