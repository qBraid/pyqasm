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
Module containing unit tests for expressions.

"""
# import pytest
# from qbraid_qir.qasm3 import Qasm3ConversionError, qasm3_to_qir

# from tests.qir_utils import check_attributes, check_expressions


# def test_correct_expressions():
#     qasm_str = """OPENQASM 3;
#     qubit q;

#     // supported
#     rx(1.57) q;
#     rz(3-2*3) q;
#     rz(3-2*3*(8/2)) q;
#     rx(-1.57) q;
#     rx(4%2) q;
#     rx(true) q;
#     rx(!0) q;
#     rx(~3) q;

#     int a = 5;
#     float b = 10*a*pi;
#     array[int[32], 2] c;
#     c[0] = 1;
#     c[1] = c[0] + 2;


#     """

#     result = qasm3_to_qir(qasm_str)
#     generated_qir = str(result).splitlines()

#     check_attributes(generated_qir, 1, 0)
#     gates = ["rx", "rz", "rz", "rx", "rx"]
#     expression_values = [1.57, 3 - 2 * 3, 3 - 2 * 3 * (8 / 2), -1.57, 4 % 2]
#     qubits = [0, 0, 0, 0, 0]
#     check_expressions(generated_qir, 5, gates, expression_values, qubits)


# def test_incorrect_expressions():
#     with pytest.raises(Qasm3ConversionError, match=r"Unsupported expression type .*"):
#         qasm3_to_qir("OPENQASM 3; qubit q; rz(1 - 2 + 32im) q;")
#     with pytest.raises(
#         Qasm3ConversionError, match=r"Unsupported expression type .* in ~ operation"
#     ):
#         qasm3_to_qir("OPENQASM 3; qubit q; rx(~1.3) q;")
#     with pytest.raises(
#         Qasm3ConversionError, match=r"Unsupported expression type .* in ~ operation"
#     ):
#         qasm3_to_qir("OPENQASM 3; qubit q; rx(~1.3+5im) q;")

#     with pytest.raises(Qasm3ConversionError, match="Undefined identifier x in expression"):
#         qasm3_to_qir("OPENQASM 3; qubit q; rx(x) q;")

#     with pytest.raises(Qasm3ConversionError, match="Uninitialized variable x in expression"):
#         qasm3_to_qir("OPENQASM 3; qubit q; int x; rx(x) q;")
