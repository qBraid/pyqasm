from pyqasm.algorithms.solovay_kitaev.experimental import basic_approximation_traversal
from pyqasm.algorithms.solovay_kitaev import basic_approximation

from pyqasm.algorithms.solovay_kitaev.experimental.basic_approximation_traversal import H, S, T

import numpy as np
from pyqasm.elements import BasisSet

import timeit
from functools import partial


# ['t', 'h', 's', 'h', 't']
U1 = np.array([[0.5+5.00000000e-01j, 0.70710678-2.29934717e-17j], [0.70710678+0.00000000e+00j, -0.5 +5.00000000e-01j]]) # T*H*S*H*T

# ['s', 'h', 's']
U2 = np.array([[0.70711,  0.70711j],
                  [0.70711j, 0.70711]])

# ['h', 't', 'h', 's']
U3 = (H*T*H*S).matrix

# ['s', 's', 'h', 't']
U4 = (S*S*H*T).matrix

def test_time(U, U_name):

    cache_approach_func = partial(basic_approximation.basic_approximation, U, BasisSet.CLIFFORD_T, 0.001, 5)
    traversal_approach_func = partial(basic_approximation_traversal.basic_approximation, U, BasisSet.CLIFFORD_T, 0.001, 5)

    cache_approach_execution_time = timeit.timeit(cache_approach_func, number=1)
    traversal_approach_execution_time = timeit.timeit(traversal_approach_func, number=1)

    cache_approach_result = basic_approximation.basic_approximation(U, BasisSet.CLIFFORD_T, 0.001, 5)
    traversal_approach_result = basic_approximation_traversal.basic_approximation(U, BasisSet.CLIFFORD_T, 0.001, 5)

    print("-------------------------------------------")

    print(f"U: {U_name}")
    
    print("**************** Result ****************")

    print(f"Cache approach:     {cache_approach_result['name']}")
    print(f"Traversal approach: {traversal_approach_result.name}")

    print("**************** Time Taken **************** ")
    print(f"Cache approach:     {cache_approach_execution_time}")
    print(f"Traversal approach: {traversal_approach_execution_time}")
    
    print("-------------------------------------------")

if __name__ == '__main__':
    test_time(U1, ['t', 'h', 's', 'h', 't'])
    test_time(U2, ['s', 'h', 's'])
    test_time(U3, ['h', 't', 'h', 's'])
    test_time(U4, ['s', 's', 'h', 't'])