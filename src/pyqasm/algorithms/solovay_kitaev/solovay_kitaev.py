import numpy as np
from typing import List, Tuple

from pyqasm.algorithms.solovay_kitaev.generator import gate_sets
from pyqasm.algorithms.solovay_kitaev.optimizer import optimize_gate_sequnce
from pyqasm.maps.gates import BASIS_GATE_MAP, SELF_INVERTING_ONE_QUBIT_OP_SET, ST_GATE_INV_MAP
from pyqasm.algorithms.solovay_kitaev.basic_approximation import basic_approximation
from pyqasm.elements import BasisSet

gate_matrix = {
    "h": (1 / np.sqrt(2)) * np.array([[1, 1], [1, -1]]),
    "s": np.array([[1, 0], [0, 1j]]),
    "t": np.array([[1, 0], [0, np.exp(1j * np.pi / 4)]]),
    "sdg": np.array([[1, 0], [0, 1j]]).conj().T,
    "tdg": np.array([[1, 0], [0, np.exp(1j * np.pi / 4)]]).conj().T,
}

class SU2Matrix:
    """Class representing a 2x2 Special Unitary matrix."""
    def __init__(self, matrix: np.ndarray, name: List[str]):
        self.matrix = matrix
        self.name = name

    def __mul__(self, other: 'SU2Matrix') -> 'SU2Matrix':
        matrix = np.dot(self.matrix, other.matrix)
        name = self.name.copy()
        name.extend(other.name)
        return SU2Matrix(matrix, name)

    def dagger(self) -> 'SU2Matrix':
        """Returns the conjugate transpose."""
        matrix = self.matrix.conj().T
        name = []
        for n in self.name[::-1]:
            name.append(self._get_dagger_gate_name(n))
        
        return SU2Matrix(matrix, name)

    def distance(self, other: 'SU2Matrix') -> float:
        """Calculates the operator norm distance between two matrices."""
        diff = self.matrix - other.matrix
        return np.linalg.norm(diff)
    
    def _get_dagger_gate_name(self,name: str):
        if name in SELF_INVERTING_ONE_QUBIT_OP_SET:
            return name
        else:
            return ST_GATE_INV_MAP[name]
        
    def __str__(self):
        return f"name: {self.name}, matrix: {self.matrix}"

def group_commutator(a: SU2Matrix, b: SU2Matrix) -> SU2Matrix:
    """Compute the group commutator [a,b] = aba^{-1}b^{-1}."""
    return a * b * a.dagger() * b.dagger()        

def find_basic_approximation(U: SU2Matrix, target_basis_set, accuracy=0.001, max_tree_depth=10) -> SU2Matrix:
    gates = basic_approximation(U, target_basis_set, accuracy, max_tree_depth)
    return SU2Matrix(gates["matrix"], gates["name"])

def decompose_group_element(target: SU2Matrix, target_gate_set, basic_gates: List[SU2Matrix], depth: int) -> Tuple[List[SU2Matrix], float]:
    
    if depth == 0:
        best_approx = find_basic_approximation(target.matrix, target_gate_set)
        return best_approx, target.distance(best_approx)
    
    # Recursive approximation
    prev_sequence, prev_error = decompose_group_element(target, target_gate_set, basic_gates, depth - 1)
    
    # If previous approximation is good enough, return it
    # ERROR IS HARD CODED RIGHT NOW -> CHANGE THIS TO FIT USER-INPUT
    if prev_error < 1e-6:
        return prev_sequence, prev_error
    
    error = target * prev_sequence.dagger()
    
    # Find Va and Vb such that their group commutator approximates the error
    best_v = None
    best_w = None
    best_error = float('inf')

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
        v_sequence, error  = decompose_group_element(best_v, target_gate_set, basic_gates, depth - 1)
        w_sequence, error = decompose_group_element(best_w, target_gate_set, basic_gates, depth - 1)

        result = group_commutator(v_sequence, w_sequence) * prev_sequence
        
    final_error = target.distance(result)
    
    return result, final_error

def solovay_kitaev(target: np.ndarray, target_basis_set, depth: int = 3) -> List[np.ndarray]:
    """
    Main function to run the Solovay-Kitaev algorithm.
    
    Args:
        target: Target unitary matrix as numpy array
        target_basis_set: The target basis set to rebase the module to.
        depth: Recursion depth
    
    Returns:
        List of gates that approximate the target unitary
    """
    # Convert inputs to SU2Matrix objects
    target_su2 = SU2Matrix(target, [])
    
    target_basis_gate_list = BASIS_GATE_MAP[target_basis_set]
    basic_gates_su2 = [SU2Matrix(gate_matrix[gate], [gate]) for gate in target_basis_gate_list if gate != "cx"]


    # Run the decomposition
    sequence, error = decompose_group_element(target_su2, target_basis_set, basic_gates_su2, depth)

    return sequence
    # return optimize_gate_sequnce(sequence, target_basis_set)
        
if __name__ == '__main__':  
    U = np.array([[0.70711,  0.70711j],
                  [0.70711j, 0.70711]])
    
    r0 = solovay_kitaev(U, BasisSet.CLIFFORD_T, depth=0)
    print(r0.name)  # Output: ['s', 'h', 's']
    
    r1 = solovay_kitaev(U, BasisSet.CLIFFORD_T, depth=1)
    print(r1.name)  # Output: ['s', 's', 's', 't', 't', 'tdg', 'sdg', 'sdg', 'sdg', 'tdg', 's', 'h', 's']
    
    r2 = solovay_kitaev(U, BasisSet.CLIFFORD_T, depth=2)
    print(r2.name)  # Output: ['t', 's', 's', 's', 't', 'tdg', 'tdg', 'sdg', 'sdg', 'sdg', 't', 's', 's', 's', 't', 'tdg', 'tdg', 'sdg', 'sdg', 'sdg', 's', 'h', 's']
    
    print(np.allclose(r0.matrix, r1.matrix))    # Output: True
    print(np.allclose(r1.matrix, r2.matrix))    # Output: True
    print(np.allclose(r2.matrix, r0.matrix))    # Output: True
    
    # Test optimizer
    print(optimize_gate_sequnce(r2.name, BasisSet.CLIFFORD_T))