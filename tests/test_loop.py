# Copyright (C) 2024 qBraid
#
# This file is part of the pyqasm
#
# The pyqasm is free software released under the GNU General Public License v3
# or later. You can redistribute and/or modify it under the terms of the GPL v3.
# See the LICENSE file in the project root or <https://www.gnu.org/licenses/gpl-3.0.html>.
#
# THERE IS NO WARRANTY for the pyqasm, as per Section 15 of the GPL v3.
"""
Module containing unit tests for parsing and unrolling programs that contain loops.

"""

# import pytest
# from qbraid_qir.qasm3 import qasm3_to_qir
# from qbraid_qir.qasm3.visitor import Qasm3ConversionError

# from tests.qir_utils import (
#     check_attributes,
#     check_single_qubit_gate_op,
#     check_single_qubit_rotation_op,
# )

# EXAMPLE_WITHOUT_LOOP = """
# OPENQASM 3.0;
# include "stdgates.inc";

# qubit[4] q;
# bit[4] c;

# h q;

# cx q[0], q[1];
# cx q[1], q[2];
# cx q[2], q[3];

# measure q->c;
# """


# def test_convert_qasm3_for_loop():
#     """Test converting a QASM3 program that contains a for loop."""
#     qir_expected = qasm3_to_qir(EXAMPLE_WITHOUT_LOOP, name="test")
#     qir_from_loop = qasm3_to_qir(
#         """
#         OPENQASM 3.0;
#         include "stdgates.inc";

#         qubit[4] q;
#         bit[4] c;

#         h q;
#         for int i in [0:2]{
#             cx q[i], q[i+1];
#         }
#         measure q->c;
#         """,
#         name="test",
#     )
#     assert str(qir_expected) == str(qir_from_loop)
#     assert str(qir_from_loop) == EXAMPLE_QIR_OUTPUT


# def test_convert_qasm3_for_loop_shadow():
#     """Test for loop where loop variable shadows variable from global scope."""
#     qir_expected = qasm3_to_qir(
#         """
#         OPENQASM 3.0;
#         include "stdgates.inc";

#         qubit[4] q;
#         bit[4] c;

#         int i = 3;

#         h q;
#         cx q[0], q[1];
#         cx q[1], q[2];
#         cx q[2], q[3];
#         h q[i];
#         measure q->c;
#         """,
#         name="test",
#     )
#     qir_from_loop = qasm3_to_qir(
#         """
#         OPENQASM 3.0;
#         include "stdgates.inc";

#         qubit[4] q;
#         bit[4] c;

#         int i = 3;

#         h q;
#         for int i in [0:2]{
#             cx q[i], q[i+1];
#         }
#         h q[i];
#         measure q->c;
#         """,
#         name="test",
#     )
#     assert str(qir_expected) == str(qir_from_loop)


# def test_convert_qasm3_for_loop_enclosing():
#     """Test for loop where variable from outer loop is accessed from inside the loop."""
#     qir_expected = qasm3_to_qir(
#         """
#         OPENQASM 3.0;
#         include "stdgates.inc";

#         qubit[4] q;
#         bit[4] c;

#         int j = 3;

#         h q;
#         cx q[0], q[1];
#         h q[j];
#         cx q[1], q[2];
#         h q[j];
#         cx q[2], q[3];
#         h q[j];
#         measure q->c;
#         """,
#         name="test",
#     )
#     qir_from_loop = qasm3_to_qir(
#         """
#         OPENQASM 3.0;
#         include "stdgates.inc";

#         qubit[4] q;
#         bit[4] c;

#         int j = 3;

#         h q;
#         for int i in [0:2]{
#             cx q[i], q[i+1];
#             h q[j];
#         }
#         measure q->c;
#         """,
#         name="test",
#     )
#     assert str(qir_expected) == str(qir_from_loop)


# def test_convert_qasm3_for_loop_enclosing_modifying():
#     """Test for loop where variable from outer loop is modified from inside the loop."""
#     qir_expected = qasm3_to_qir(
#         """
#         OPENQASM 3.0;
#         include "stdgates.inc";

#         qubit[4] q;
#         bit[4] c;

#         int j = 0;

#         h q;
#         cx q[0], q[1];
#         h q[j];
#         j += 1;
#         cx q[1], q[2];
#         h q[j];
#         j += 1;
#         cx q[2], q[3];
#         h q[j];
#         j += 1;

#         h q[j];
#         measure q->c;
#         """,
#         name="test",
#     )
#     qir_from_loop = qasm3_to_qir(
#         """
#         OPENQASM 3.0;
#         include "stdgates.inc";

#         qubit[4] q;
#         bit[4] c;

#         int j = 0;

#         h q;
#         for int i in [0:2]{
#             cx q[i], q[i+1];
#             h q[j];
#             j += 1;
#         }
#         h q[j];
#         measure q->c;
#         """,
#         name="test",
#     )
#     assert str(qir_expected) == str(qir_from_loop)


# def test_convert_qasm3_for_loop_discrete_set():
#     """Test converting a QASM3 program that contains a for loop initialized from a DiscreteSet."""
#     qir_expected = qasm3_to_qir(EXAMPLE_WITHOUT_LOOP, name="test")
#     qir_from_loop = qasm3_to_qir(
#         """
#         OPENQASM 3.0;
#         include "stdgates.inc";

#         qubit[4] q;
#         bit[4] c;

#         h q;
#         for int i in {0, 1, 2} {
#             cx q[i], q[i+1];
#         }
#         measure q->c;
#         """,
#         name="test",
#     )
#     assert str(qir_expected) == str(qir_from_loop)
#     assert str(qir_from_loop) == EXAMPLE_QIR_OUTPUT


# def test_function_executed_in_loop():
#     """Test that a function executed in a loop is correctly parsed."""
#     qasm_str = """OPENQASM 3;
#     include "stdgates.inc";

#     def my_function(qubit q_arg, float[32] b) {
#         rx(b) q_arg;
#         return;
#     }
#     qubit[5] q;

#     int[32] n = 2;
#     float[32] b = 3.14;

#     for int i in [0:n] {
#         my_function(q[i], i*b);
#     }
#     """

#     result = qasm3_to_qir(qasm_str)
#     generated_qir = str(result).splitlines()

#     check_attributes(generated_qir, 5, 0)
#     check_single_qubit_rotation_op(generated_qir, 3, list(range(3)), [0, 3.14, 2 * 3.14], "rx")


# def test_loop_inside_function():
#     """Test that a function with a loop is correctly parsed."""
#     qasm_str = """OPENQASM 3;
#     include "stdgates.inc";

#     def my_function(qubit[3] q2) {
#         for int[32] i in [0:2] {
#             h q2[i];
#         }
#         return;
#     }
#     qubit[3] q1;
#     my_function(q1);
#     """

#     result = qasm3_to_qir(qasm_str)
#     generated_qir = str(result).splitlines()

#     check_attributes(generated_qir, 3, 0)
#     check_single_qubit_gate_op(generated_qir, 3, [0, 1, 2], "h")


# def test_function_in_nested_loop():
#     """Test that a function executed in a nested loop is correctly parsed."""
#     qasm_str = """OPENQASM 3;
#     include "stdgates.inc";

#     def my_function(qubit q_arg, float[32] b) {
#         rx(b) q_arg;
#         return;
#     }
#     qubit[5] q;

#     int[32] n = 2;
#     float[32] b = 3.14;

#     for int i in [0:n] {
#         for int j in [0:n] {
#             my_function(q[i], j*b);
#         }
#     }

#     my_function(q[0], 2*b);
#     """

#     result = qasm3_to_qir(qasm_str)
#     generated_qir = str(result).splitlines()

#     check_attributes(generated_qir, 5, 0)
#     check_single_qubit_rotation_op(
#         generated_qir,
#         9,
#         [0, 0, 0, 1, 1, 1, 2, 2, 2, 0],
#         [0, 3.14, 2 * 3.14, 0, 3.14, 2 * 3.14, 0, 3.14, 2 * 3.14, 2 * 3.14],
#         "rx",
#     )


# @pytest.mark.skip(reason="Not implemented nested functions yet")
# def test_loop_in_nested_function_call():
#     qasm3_string = """
#     OPENQASM 3;
#     include "stdgates.inc";
#     def my_function_1(qubit q1, int[32] a){
#         for int[32] i in [0:2]{
#             rx(a*i) q1;
#         }
#     }

#     def my_function_2(qubit q2, int[32] b){
#         my_function_1(q2, b);
#     }

#     qubit q;
#     my_function_2(q, 3);
#     """
#     result = qasm3_to_qir(qasm3_string)
#     generated_qir = str(result).splitlines()

#     check_attributes(generated_qir, 1, 0)
#     check_single_qubit_rotation_op(generated_qir, 3, [0, 0, 0], [0, 3, 6], "rx")


# def test_convert_qasm3_for_loop_unsupported_type():
#     """Test correct error when converting a QASM3 program that contains a for loop initialized from
#     an unsupported type."""
#     with pytest.raises(
#         Qasm3ConversionError,
#         match=(
#             "Unexpected type <class 'openqasm3.ast.BitstringLiteral'>"
#             " of set_declaration in loop."
#         ),
#     ):
#         _ = qasm3_to_qir(
#             """
#             OPENQASM 3.0;
#             include "stdgates.inc";

#             qubit[4] q;
#             bit[4] c;

#             h q;
#             for bit b in "001" {
#                 x q[b];
#             }
#             measure q->c;
#             """,
#             name="test",
#         )
