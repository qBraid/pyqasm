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
Module containing unit tests for reset operation.

"""
import pytest

from pyqasm.entrypoint import dumps, loads
from pyqasm.exceptions import ValidationError
from tests.utils import check_unrolled_qasm


# Test reset operations in different ways
def test_reset_operations():
    """Test reset operations in different ways"""
    qasm3_string = """
    OPENQASM 3.0;
    include "stdgates.inc";

    // qubit declarations
    qubit q1;
    qubit[2] q2;
    qreg q3[3];

    // reset operations
    reset q1;
    reset q2[1];
    reset q3[2];
    reset q3[:2];
    """

    expected_qasm = """OPENQASM 3.0;
    include "stdgates.inc";
    qubit[1] q1;
    qubit[2] q2;
    qubit[3] q3;
    reset q1[0];
    reset q2[1];
    reset q3[2];
    reset q3[0];
    reset q3[1];
    """

    result = loads(qasm3_string)
    result.unroll()
    check_unrolled_qasm(dumps(result), expected_qasm)


def test_reset_inside_function():
    """Test that a qubit reset inside a function is correctly parsed."""
    qasm3_string = """OPENQASM 3.0;
    include "stdgates.inc";

    def my_function(qubit a) {
        reset a;
        return;
    }
    qubit[3] q;
    my_function(q[1]);
    """

    expected_qasm = """OPENQASM 3.0;
    include "stdgates.inc";
    qubit[3] q;
    reset q[1];
    """

    result = loads(qasm3_string)
    result.unroll()
    check_unrolled_qasm(dumps(result), expected_qasm)


def test_incorrect_resets():
    undeclared = """
    OPENQASM 3.0;
    include "stdgates.inc";

    qubit[3] q1;

    // undeclared register 
    reset q2[0];
    """
    with pytest.raises(ValidationError):
        loads(undeclared).validate()

    index_error = """
    OPENQASM 3.0;
    include "stdgates.inc";

    qubit[2] q1;

    // out of bounds 
    reset q1[4];
    """
    with pytest.raises(ValidationError):
        loads(index_error).validate()
