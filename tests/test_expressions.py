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
Module containing unit tests for expressions.

"""
import pytest

from pyqasm.exceptions import ValidationError
from pyqasm.unroller import unroll
from pyqasm.validate import validate
from tests.utils import check_single_qubit_rotation_op


def test_correct_expressions():
    qasm_str = """OPENQASM 3;
    qubit q;

    // supported
    rx(1.57) q;
    rz(3-2*3) q;
    rz(3-2*3*(8/2)) q;
    rx(-1.57) q;
    rx(4%2) q;

    int a = 5;
    float b = 10*a*pi;
    array[int[32], 2] c;
    c[0] = 1;
    c[1] = c[0] + 2;
    """

    result = unroll(qasm_str, as_module=True)
    assert result.num_qubits == 1
    assert result.num_clbits == 0
    rx_expression_values = [1.57, -1.57, 0]
    rz_expression_values = [-3, -21.0]
    check_single_qubit_rotation_op(result.unrolled_ast, 3, [0] * 3, rx_expression_values, "rx")
    check_single_qubit_rotation_op(result.unrolled_ast, 2, [0] * 2, rz_expression_values, "rz")


def test_incorrect_expressions():
    with pytest.raises(ValidationError, match=r"Unsupported expression type .*"):
        validate("OPENQASM 3; qubit q; rz(1 - 2 + 32im) q;")

    with pytest.raises(ValidationError, match=r"Unsupported expression type .* in ~ operation"):
        validate("OPENQASM 3; qubit q; rx(~1.3) q;")

    with pytest.raises(ValidationError, match=r"Unsupported expression type .* in ~ operation"):
        validate("OPENQASM 3; qubit q; rx(~1.3+5im) q;")

    with pytest.raises(ValidationError, match="Undefined identifier x in expression"):
        validate("OPENQASM 3; qubit q; rx(x) q;")

    with pytest.raises(ValidationError, match="Uninitialized variable x in expression"):
        validate("OPENQASM 3; qubit q; int x; rx(x) q;")
