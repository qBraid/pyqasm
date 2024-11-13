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
Module containing unit tests for parsing and unrolling programs that contain subroutines.

"""

import pytest

from pyqasm.entrypoint import loads
from pyqasm.exceptions import ValidationError
from tests.qasm3.resources.subroutines import SUBROUTINE_INCORRECT_TESTS
from tests.utils import check_single_qubit_gate_op, check_single_qubit_rotation_op


def test_function_declaration():
    """Test that a function declaration is correctly parsed."""
    qasm_str = """OPENQASM 3.0;
    include "stdgates.inc";
    def my_function(qubit q) {
        h q;
        return;
    }
    qubit q;
    my_function(q);
    """

    result = loads(qasm_str)
    result.unroll()
    assert result.num_clbits == 0
    assert result.num_qubits == 1

    check_single_qubit_gate_op(result.unrolled_ast, 1, [0], "h")


def test_simple_function_call():
    """Test that a simple function call is correctly parsed."""
    qasm_str = """OPENQASM 3.0;
    include "stdgates.inc";

    def my_function(qubit a, float[32] b) {
        rx(b) a;
        float[64] c = 2*b;
        rx(c) a;
        return;
    }
    qubit q;
    float[32] r = 3.14;
    my_function(q, r);
    """

    result = loads(qasm_str)
    result.unroll()
    assert result.num_clbits == 0
    assert result.num_qubits == 1

    check_single_qubit_rotation_op(result.unrolled_ast, 2, [0, 0], [3.14, 6.28], "rx")


def test_const_visible_in_function_call():
    """Test that a constant is visible in a function call."""
    qasm_str = """OPENQASM 3.0;
    include "stdgates.inc";
    const float[32] pi2 = 3.14;

    def my_function(qubit q) {
        rx(pi2) q;
        return;
    }
    qubit q;
    my_function(q);
    """

    result = loads(qasm_str)
    result.unroll()
    assert result.num_clbits == 0
    assert result.num_qubits == 1

    check_single_qubit_rotation_op(result.unrolled_ast, 1, [0], [3.14], "rx")


def test_update_variable_in_function():
    """Test that variable update works correctly in a function."""
    qasm_str = """OPENQASM 3.0;
    include "stdgates.inc";

    def my_function(qubit q) {
        float[32] a = 3.14;
        a = 2*a;
        rx(a) q;
        return;
    }
    qubit q;
    my_function(q);
    """

    result = loads(qasm_str)
    result.unroll()
    assert result.num_clbits == 0
    assert result.num_qubits == 1

    check_single_qubit_rotation_op(result.unrolled_ast, 1, [0], [6.28], "rx")


def test_function_call_in_expression():
    """Test that a function call in an expression is correctly parsed."""
    qasm_str = """OPENQASM 3.0;
    include "stdgates.inc";

    def my_function(qubit[4] q) -> bool{
        h q;
        return true;
    }
    qubit[4] q;
    
    // this is to be explained
    bool b = my_function(q);
    """

    result = loads(qasm_str)
    result.unroll()
    assert result.num_clbits == 0
    assert result.num_qubits == 4

    check_single_qubit_gate_op(result.unrolled_ast, 4, list(range(4)), "h")


def test_classical_quantum_function():
    """Test that a function with classical and quantum instructions is correctly unrolled"""
    qasm_str = """
    OPENQASM 3.0;
    include "stdgates.inc";
    def my_function(qubit q, int[32] iter) -> int[32]{
        h q;
        if(iter>2)
            x q;
        if (iter>3)
            y q;
        return iter + 1;
    }
    qubit[4] q;
    int[32] new_var ;
    for int i in [0:3]
    { 
        new_var = my_function(q[i] , i);
    }

    if(new_var>2)
        h q[0];
    """
    result = loads(qasm_str)
    result.unroll()
    assert result.num_clbits == 0
    assert result.num_qubits == 4

    check_single_qubit_gate_op(result.unrolled_ast, 5, list(range(4)) + [0], "h")
    check_single_qubit_gate_op(result.unrolled_ast, 1, [3], "x")


def test_multiple_function_calls():
    """Test that multiple function calls are correctly parsed."""
    qasm_str = """OPENQASM 3.0;
    include "stdgates.inc";

    def my_function(int[32] a, qubit q_arg) {
        h q_arg;
        rx (a) q_arg;
        return;
    }
    qubit[3] q;
    my_function(2, q[2]);
    my_function(1, q[1]);
    my_function(0, q[0]);
    """

    result = loads(qasm_str)
    result.unroll()
    assert result.num_clbits == 0
    assert result.num_qubits == 3

    check_single_qubit_gate_op(result.unrolled_ast, 3, [2, 1, 0], "h")
    check_single_qubit_rotation_op(result.unrolled_ast, 3, [2, 1, 0], [2, 1, 0], "rx")


def test_function_call_with_return():
    """Test that a function call with a return value is correctly parsed."""
    qasm_str = """OPENQASM 3.0;
    include "stdgates.inc";

    def my_function(qubit q) -> float[32] {
        h q;
        return 3.14;
    }
    qubit q;
    float[32] r = my_function(q);
    """

    result = loads(qasm_str)
    result.unroll()
    assert result.num_clbits == 0
    assert result.num_qubits == 1

    check_single_qubit_gate_op(result.unrolled_ast, 1, [0], "h")


def test_return_values_from_function():
    """Test that the values returned from a function are used correctly in other function."""
    qasm_str = """OPENQASM 3.0;
    include "stdgates.inc";

    def my_function(qubit q) -> float[32] {
        h q;
        return 3.14;
    }
    def my_function_2(qubit q, float[32] r) {
        rx(r) q;
        return;
    }
    qubit[2] q;
    float[32] r1 = my_function(q[0]);
    my_function_2(q[0], r1);

    array[float[32], 1, 1] r2 = {{3.14}};
    my_function_2(q[1], r2[0,0]);

    """

    result = loads(qasm_str)
    result.unroll()
    assert result.num_clbits == 0
    assert result.num_qubits == 2

    check_single_qubit_gate_op(result.unrolled_ast, 1, [0], "h")
    check_single_qubit_rotation_op(result.unrolled_ast, 2, [0, 1], [3.14, 3.14], "rx")


def test_function_call_with_custom_gate():
    """Test that a function call with a custom gate is correctly parsed."""
    qasm_str = """OPENQASM 3.0;
    include "stdgates.inc";

    gate my_gate(a) q2 { 
        rx(a) q2; 
    }

    def my_function(qubit a, float[32] b) {
        float[64] c = 2*b;
        my_gate(b) a;
        my_gate(c) a;
        return;
    }
    qubit q;
    float[32] r = 3.14;
    my_function(q, r);
    """

    result = loads(qasm_str)
    result.unroll()
    assert result.num_clbits == 0
    assert result.num_qubits == 1

    check_single_qubit_rotation_op(result.unrolled_ast, 2, [0, 0], [3.14, 6.28], "rx")


@pytest.mark.skip(reason="Not implemented nested functions yet")
def test_function_call_from_within_fn():
    """Test that a function call from within another function is correctly converted."""
    qasm_str = """OPENQASM 3.0;
    include "stdgates.inc";

    def my_function(qubit q1) {
        h q1;
        return;
    }

    def my_function_2(qubit[2] q2) {
        my_function(q2[1]);
        return;
    }
    qubit[2] q;
    my_function_2(q);
    """

    result = loads(qasm_str)
    result.unroll()
    assert result.num_clbits == 0
    assert result.num_qubits == 2

    check_single_qubit_gate_op(result.unrolled_ast, 1, [1], "h")


@pytest.mark.parametrize("data_type", ["int[32] a = 1;", "float[32] a = 1.0;", "bit a = 0;"])
def test_return_value_mismatch(data_type):
    """Test that returning a value of incorrect type raises error."""
    qasm_str = (
        """OPENQASM 3.0;
    include "stdgates.inc";

    def my_function(qubit q) {
        h q;
    """
        + data_type
        + """
        return a;
    }
    qubit q;
    my_function(q);
    """
    )

    with pytest.raises(
        ValidationError, match=r"Return type mismatch for subroutine 'my_function'.*"
    ):
        loads(qasm_str).validate()


@pytest.mark.parametrize("keyword", ["pi", "euler", "tau"])
def test_subroutine_keyword_naming(keyword):
    """Test that using a keyword as a subroutine name raises error."""
    qasm_str = f"""OPENQASM 3.0;
    include "stdgates.inc";

    def {keyword}(qubit q) {{
        h q;
        return;
    }}
    qubit q;
    {keyword}(q);
    """

    with pytest.raises(ValidationError, match=f"Subroutine name '{keyword}' is a reserved keyword"):
        loads(qasm_str).validate()


@pytest.mark.parametrize("qubit_params", ["q", "q[:2]", "q[{0,1}]"])
def test_qubit_size_arg_mismatch(qubit_params):
    """Test that passing a qubit of different size raises error."""
    qasm_str = (
        """OPENQASM 3.0;
    include "stdgates.inc";

    def my_function(qubit[3] q) {
        h q;
        return;
    }
    qubit[2] q;
    my_function("""
        + qubit_params
        + """);
    """
    )

    with pytest.raises(
        ValidationError,
        match="Qubit register size mismatch for function 'my_function'. "
        "Expected 3 in variable 'q' but got 2",
    ):
        loads(qasm_str).validate()


@pytest.mark.parametrize("test_name", SUBROUTINE_INCORRECT_TESTS.keys())
def test_incorrect_custom_ops(test_name):
    qasm_str, error_message = SUBROUTINE_INCORRECT_TESTS[test_name]
    with pytest.raises(ValidationError, match=error_message):
        loads(qasm_str).validate()
