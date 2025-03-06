import pickle
import sys
from collections import deque
from typing import List
import numpy as np
from math import pi

from pyqasm.elements import BasisSet
from pyqasm.maps.gates import SELF_INVERTING_ONE_QUBIT_OP_SET, ST_GATE_INV_MAP

gate_sets_info = {
    BasisSet.CLIFFORD_T: [
        {
            "name": "h", 
            "identity": {
                "group": "h",
                "weight": 0.5
            },
            "matrix": (1 / np.sqrt(2)) * np.array([[1, 1], [1, -1]])
        },
        {
            "name": "s",
            "identity": {
                "group": "s-t",
                "weight": 0.25
            },
            "matrix": np.array([[1, 0], [0, 1j]])
        },
        {
            "name": "t",
            "identity": {
                "group": "s-t",
                "weight": 0.125
            },
            "matrix": np.array([[1, 0], [0, np.exp(1j * np.pi / 4)]]),
        },
    ]
}

class TU2Matrix:
    def __init__(self, matrix: np.ndarray, name: List[str], identity_group:str, identity_weight:float):
        self.matrix = matrix
        self.name = name
        self.identity_group = identity_group
        self.identity_weight = identity_weight

    def __mul__(self, other: 'TU2Matrix') -> 'TU2Matrix':
        matrix = np.dot(self.matrix, other.matrix)
        name = self.name.copy()
        name.extend(other.name)
        identity_weight = 0
        identity_group = ''
        if self.identity_group == other.identity_group:
            identity_weight = self.identity_weight + other.identity_weight
        else:
            identity_group = other.identity_group
            identity_weight = other.identity_weight
            
        return TU2Matrix(matrix, name, identity_group, identity_weight)
    
    def can_multiple(self, other: 'TU2Matrix'):
        if self.identity_group != other.identity_group:
            return True
        
        if self.identity_weight + other.identity_weight < 1:
            return True
        
        return False

    def get_trace_diff(self, U):
        # trace_diff = np.abs(np.trace(np.dot(self.matrix.conj().T, U) - np.identity(2)))
        trace_diff = np.linalg.norm(self.matrix - U, 2)
        return trace_diff
        
    def __str__(self):
        # return f"name: {self.name}"
        return f"name: {self.name}, matrix: {self.matrix}"
    
    def copy(self) -> 'TU2Matrix':
        return TU2Matrix(self.matrix.copy(), self.name.copy(), self.identity_group, self.identity_weight)

# Constants
best_gate = None
closest_gate = None
closest_trace_diff = float("inf")

H = TU2Matrix((1 / np.sqrt(2)) * np.array([[1, 1], [1, -1]]), ['h'], 'h', 0.5)
S = TU2Matrix(np.array([[1, 0], [0, 1j]]), ['s'], 's-t', 0.25)
T = TU2Matrix(np.array([[1, 0], [0, np.exp(1j * np.pi / 4)]]), ['t'], 's-t', 0.125)

gate_sets = {
    BasisSet.CLIFFORD_T: [H, S, T]
}

def rescursive_traversal(U, A,  target_gate_set_list, current_depth, accuracy=0.001, max_tree_depth=3):
    if current_depth >= max_tree_depth:
        return
    
    global closest_trace_diff, closest_gate, best_gate
    
    if best_gate:
        return
    
    for gate in target_gate_set_list:
        if not A.can_multiple(gate):
            continue
        A_copy = A.copy()
        A = A*gate
        
        trace_diff = A.get_trace_diff(U)
        if trace_diff < accuracy:
            best_gate = A.copy()
            return best_gate
        
        # Update the closest gate if the current one is closer
        if trace_diff < closest_trace_diff:
            closest_trace_diff = trace_diff
            closest_gate = A.copy()
            
        # print(A.name)
        # if A.name == ['s', 'h', 's']:
        #     print(A)
        #     print(trace_diff)
        rescursive_traversal(U, A.copy(), target_gate_set_list, current_depth+1, accuracy, max_tree_depth)
        A = A_copy.copy()
        
    pass

def basic_approximation(U, target_gate_set, accuracy=0.001, max_tree_depth=3):
    global closest_trace_diff, closest_gate, best_gate
    
    A = TU2Matrix(np.identity(2), [], None, None)
    target_gate_set_list = gate_sets[target_gate_set]
    current_depth = 0
    rescursive_traversal(U, A.copy(), target_gate_set_list,current_depth, accuracy, max_tree_depth)
    
    result = None
    
    if best_gate:
        result = best_gate.copy()
    else:
        result = closest_gate.copy()
        
    # Reset global variables
    best_gate = None
    closest_gate = None
    closest_trace_diff = float("inf")
    
    return result


if __name__ == "__main__":
    U = np.array([[0.70711,  0.70711j],
                  [0.70711j, 0.70711]])
    # basic_approximation(U, BasisSet.CLIFFORD_T, 0.00001, 3)
    print(basic_approximation(U, BasisSet.CLIFFORD_T, 0.0001, 3))
