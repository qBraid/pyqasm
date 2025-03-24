import numpy as np
from typing import List, Tuple

class SU2Matrix:
    """Class representing a 2x2 Special Unitary matrix."""
    def __init__(self, matrix: np.ndarray):
        self.matrix = matrix
    
    def __mul__(self, other: 'SU2Matrix') -> 'SU2Matrix':
        return SU2Matrix(np.dot(self.matrix, other.matrix))
    
    def dagger(self) -> 'SU2Matrix':
        """Returns the conjugate transpose."""
        return SU2Matrix(self.matrix.conj().T)
    
    def distance(self, other: 'SU2Matrix') -> float:
        """Calculates the operator norm distance between two matrices."""
        diff = self.matrix - other.matrix
        return np.linalg.norm(diff)

def group_commutator(a: SU2Matrix, b: SU2Matrix) -> SU2Matrix:
    """Compute the group commutator [a,b] = aba^{-1}b^{-1}."""
    return a * b * a.dagger() * b.dagger()

def find_basic_approximation(target: SU2Matrix, basic_gates: List[SU2Matrix]) -> SU2Matrix:
    """
    Find the best approximation of the target unitary from the basic gate set.
    
    Args:
        target: Target unitary matrix to approximate
        basic_gates: List of available basic gates
    
    Returns:
        Best approximating unitary from the basic gate set
    """
    best_dist = float('inf')
    best_gate = None
    
    for gate in basic_gates:
        dist = target.distance(gate)
        if dist < best_dist:
            best_dist = dist
            best_gate = gate
    
    return best_gate

def decompose_group_element(target: SU2Matrix, basic_gates: List[SU2Matrix], depth: int) -> Tuple[List[SU2Matrix], float]:
    """
    Decompose a target unitary into a sequence of basic gates using Solovay-Kitaev.
    
    Args:
        target: Target unitary matrix to decompose
        basic_gates: List of available basic gates
        depth: Recursion depth for the algorithm
    
    Returns:
        Tuple of (sequence of gates, approximation error)
    """
    if depth == 0:
        best_approx = find_basic_approximation(target, basic_gates)
        return [best_approx], target.distance(best_approx)
    
    # Recursive approximation
    prev_sequence, prev_error = decompose_group_element(target, basic_gates, depth - 1)
    
    # If previous approximation is good enough, return it
    # ERROR IS HARD CODED RIGHT NOW -> CHANGE THIS TO FIT USER-INPUT
    if prev_error < 1e-6:
        return prev_sequence, prev_error
    
    # Compute the error unitary
    approx = prev_sequence[0]
    for gate in prev_sequence[1:]:
        approx = approx * gate
    
    error = target * approx.dagger()
    
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

    # Construct the final sequence
    result_sequence = []
    result_sequence.extend(prev_sequence)
    
    # Add correction terms
    if best_v is not None and best_w is not None:
        v_sequence, error  = decompose_group_element(best_v, basic_gates, depth - 1)
        w_sequence, error = decompose_group_element(best_w, basic_gates, depth - 1)

        v_approx = v_sequence[0]
        for gate in v_sequence[1:]:
            v_approx = v_approx * gate
        
        w_approx = w_sequence[0]
        for gate in w_sequence[1:]:
            w_approx = w_approx * gate

        result_sequence.extend([best_v, best_w, v_approx.dagger(), w_approx.dagger()])
    
    # Calculate final error
    final_approx = result_sequence[0]
    for gate in result_sequence[1:]:
        final_approx = final_approx * gate
    final_error = target.distance(final_approx)
    
    return result_sequence, final_error

def solovay_kitaev(target: np.ndarray, basic_gates: List[np.ndarray], depth: int = 3) -> List[np.ndarray]:
    """
    Main function to run the Solovay-Kitaev algorithm.
    
    Args:
        target: Target unitary matrix as numpy array
        basic_gates: List of basic gates as numpy arrays
        depth: Recursion depth
    
    Returns:
        List of gates that approximate the target unitary
    """
    # Convert inputs to SU2Matrix objects
    target_su2 = SU2Matrix(target)
    basic_gates_su2 = [SU2Matrix(gate) for gate in basic_gates]
    
    # Run the decomposition
    sequence, error = decompose_group_element(target_su2, basic_gates_su2, depth)
    
    # Convert back to numpy arrays
    return [gate.matrix for gate in sequence]

def gate_to_name(gate: np.ndarray) -> str:
        """Convert a gate (numpy array) to its standard name."""
        # Helper function to check if matrices are equal within numerical precision
        # I just made up a tolerance, does it matter too much? I thought this would make my life easier
        def is_equal(A, B, tol=1e-10):
            return np.allclose(A, B, rtol=tol, atol=tol)
        
        # Define gates and their names
        gate_map = {
            'X': X,
            'Y': Y,
            'Z': Z,
            'H': H,
            'S': S,
            'S_dagger': S.conj().T,
            'T': T,
            'T_dagger': T.conj().T,
        }
        
        # Check each known gate
        for name, reference_gate in gate_map.items():
            if is_equal(gate, reference_gate):
                return name
                
        # If no match found, return a generic descriptor
        return "U"  # Unknown gate

# FOR TESTING - DELETE BEFORE MERGING
if __name__ == "__main__":
    X = np.array([[0, 1], [1, 0]], dtype=complex)
    Y = np.array([[0, -1j], [1j, 0]], dtype=complex)
    Z = np.array([[1, 0], [0, -1]], dtype=complex)
    H = np.array([[1, 1], [1, -1]], dtype=complex) / np.sqrt(2)
    S = np.array([[1, 0], [0, 1j]], dtype=complex)
    T = np.array([[1, 0], [0, np.exp((1j*np.pi)/4)]], dtype=complex)
    
    basis_gates = [H, T, S, T.conj().T, S.conj().T]
    
    # Define a target unitary
    theta = np.pi / 4
    target = np.array([
        [np.cos(theta/2), -np.sin(theta/2)],
        [np.sin(theta/2), np.cos(theta/2)]
    ], dtype=complex)
    
    # Run the algorithm
    sequence = solovay_kitaev(target, basis_gates, depth=3)

    sequence_to_string = ""

    for matrix in sequence:
        sequence_to_string += gate_to_name(matrix) + " "

    # Compare target matrix and approx matrix
    print(target)

    approx = sequence[0]
    for gate in sequence[1:]:
        approx = approx * gate
    print(approx)

    print(sequence_to_string)
