# Copyright (C) 2024 qBraid
#
# This file is part of pyqasm
#
# Pyqasm is free software released under the GNU General Public License v3
# or later. You can redistribute and/or modify it under the terms of the GPL v3.
# See the LICENSE file in the project root or <https://www.gnu.org/licenses/gpl-3.0.html>.
#
# THERE IS NO WARRANTY for pyqasm, as per Section 15 of the GPL v3.

"""
Module containing unit tests for parsing, unrolling, and
converting OpenQASM3 programs that contain arrays in subroutines.

"""

import pytest

from pyqasm.entrypoint import loads
from pyqasm.exceptions import ValidationError
from tests.qasm3.resources.subroutines import SUBROUTINE_INCORRECT_TESTS_WITH_ARRAYS
from tests.utils import check_single_qubit_rotation_op


def test_simple_function_call():
    """Test that a simple function call is correctly parsed."""
    qasm_str = """OPENQASM 3.0;
    include "stdgates.inc";

    def my_function(qubit a, readonly array[int[8], 2, 2] my_arr) {
        return;
    }
    qubit q;
    array[int[8], 2, 2] arr;
    my_function(q, arr);

    """

    result = loads(qasm_str)
    result.unroll()
    assert result.num_clbits == 0
    assert result.num_qubits == 1


def test_passing_array_to_function():
    """Test that passing an array to a function is correctly parsed."""
    qasm_str = """OPENQASM 3.0;
    include "stdgates.inc";

    def my_function(readonly array[int[8], 2, 2] my_arr, qubit q) {
        rx(my_arr[0][0]) q;
        rx(my_arr[0][1]) q;
        rx(my_arr[1][0]) q;
        rx(my_arr[1][1]) q;

        return;
    }
    qubit my_q;
    array[int[8], 2, 2] arr = { {1, 2}, {3, 4} };
    my_function(arr, my_q);
    """

    result = loads(qasm_str)
    result.unroll()
    assert result.num_clbits == 0
    assert result.num_qubits == 1

    check_single_qubit_rotation_op(
        result.unrolled_ast, 4, qubit_list=[0, 0, 0, 0], param_list=[1, 2, 3, 4], gate_name="rx"
    )


def test_passing_subarray_to_function():
    """Test that passing a smaller subarray to a function is correctly parsed."""
    qasm_str = """OPENQASM 3.0;
    include "stdgates.inc";

    def my_function(readonly array[int[8], 2, 2] my_arr, qubit q) {
        rx(my_arr[0][0]) q;
        rx(my_arr[0][1]) q;
        return;
    }
    qubit my_q;
    array[int[8], 4, 3] arr_1 = { {1, 2, 3}, {4, 5, 6}, {7, 8, 9}, {10, 11, 12} };
    array[int[8], 2, 2] arr_2 = { {1, 2}, {3, 4} };
    my_function(arr_1[1:2][1:2], my_q);
    my_function(arr_2[0:1, :], my_q);

    """

    result = loads(qasm_str)
    result.unroll()
    assert result.num_clbits == 0
    assert result.num_qubits == 1

    check_single_qubit_rotation_op(
        result.unrolled_ast, 4, qubit_list=[0] * 4, param_list=[5, 6, 1, 2], gate_name="rx"
    )


def test_passing_array_with_dim_identifier():
    """Test that passing an array with a dimension identifier is correctly parsed."""
    qasm_str = """OPENQASM 3.0;
    include "stdgates.inc";

    def my_function(readonly array[int[8], #dim = 2] my_arr, qubit q) {
        rx(my_arr[0][0]) q;
        rx(my_arr[0][1]) q;
        return;
    }
    qubit my_q;
    array[int[8], 2, 2, 2] arr = { { {1, 2}, {3, 4} }, { {5, 6}, {7, 8} } };
    my_function(arr[0, :, :], my_q);
    """

    result = loads(qasm_str)
    result.unroll()
    assert result.num_clbits == 0
    assert result.num_qubits == 1

    check_single_qubit_rotation_op(
        result.unrolled_ast, 2, qubit_list=[0] * 2, param_list=[1, 2], gate_name="rx"
    )


def test_pass_multiple_arrays_to_function():
    """Test that passing multiple arrays to a function is correctly parsed."""
    qasm_str = """OPENQASM 3.0;
    include "stdgates.inc";

    def my_function(readonly array[int[8], 2, 2] my_arr1, 
                    readonly array[int[8], 2, 2] my_arr2, 
                    qubit q) {
        for int[8] i in [0:1] {
            rx(my_arr1[i][0]) q;
            rx(my_arr2[i][1]) q;
        }

        return;
    }
    qubit my_q;
    array[int[8], 2, 2] arr_1 = { {1, 2}, {3, 4} };
    array[int[8], 2, 2] arr_2 = { {5, 6}, {7, 8} };
    my_function(arr_1, arr_2, my_q);
    """

    result = loads(qasm_str)
    result.unroll()
    assert result.num_clbits == 0
    assert result.num_qubits == 1

    check_single_qubit_rotation_op(
        result.unrolled_ast, 4, qubit_list=[0] * 4, param_list=[1, 6, 3, 8], gate_name="rx"
    )


@pytest.mark.parametrize("test_name", SUBROUTINE_INCORRECT_TESTS_WITH_ARRAYS.keys())
def test_incorrect_custom_ops_with_arrays(test_name):
    qasm_input, error_message = SUBROUTINE_INCORRECT_TESTS_WITH_ARRAYS[test_name]
    with pytest.raises(ValidationError, match=error_message):
        loads(qasm_input).validate()
