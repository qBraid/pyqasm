from math import pi
import pickle
import numpy as np

from pyqasm.elements import BasisSet
import os


def basic_approximation(U, target_gate_set, accuracy=0.001, max_tree_depth=10):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    gate_set_files = {
        BasisSet.CLIFFORD_T: os.path.join(current_dir, "cache", "clifford-t_depth-5.pkl"),
    }

    if target_gate_set not in gate_set_files:
        raise ValueError(f"Unknown target gate set: {target_gate_set}")

    pkl_file_name = gate_set_files[target_gate_set]
    try:
        with open(pkl_file_name, "rb") as file:
            gate_list = pickle.load(file)
    except FileNotFoundError:
        raise FileNotFoundError(f"Pickle file not found: {pkl_file_name}")

    closest_gate = None
    closest_trace_diff = float("inf")

    for gate in gate_list:
        gate_matrix = gate["matrix"]
        tree_depth = gate["depth"]

        # Stop if the maximum depth is exceeded
        if tree_depth > max_tree_depth:
            break

        trace_diff = np.abs(np.trace(np.dot(gate_matrix.conj().T, U) - np.identity(2)))

        if trace_diff < accuracy:
            return gate

        # Update the closest gate if the current one is closer
        if trace_diff < closest_trace_diff:
            closest_trace_diff = trace_diff
            closest_gate = gate

    return closest_gate


if __name__ == "__main__":
    U = np.array([[0.70711,  0.70711j],
                  [0.70711j, 0.70711]])
    print(basic_approximation(U, BasisSet.CLIFFORD_T, 0.001, 10))
