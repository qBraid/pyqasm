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
Module containing unit tests for the barrier operation.

"""
import pytest

from pyqasm.entrypoint import dumps, loads
from pyqasm.exceptions import ValidationError
from tests.utils import check_unrolled_qasm


# 1. Test barrier operations in different ways
def test_barrier():
    qasm_str = """
    OPENQASM 3.0;
    include "stdgates.inc";

    qubit[2] q1;
    qubit[3] q2;
    qubit q3;
    
    // full qubits
    barrier q1, q2, q3; 
    barrier q1[0], q1[1], q2[:], q3[0];

    // subset of qubits
    barrier q1, q2[0:2], q3[:];
    """

    expected_qasm = """OPENQASM 3.0;
    include "stdgates.inc";
    qubit[2] q1;
    qubit[3] q2;
    qubit[1] q3;
    barrier q1[0];
    barrier q1[1];
    barrier q2[0];
    barrier q2[1];
    barrier q2[2];
    barrier q3[0];
    barrier q1[0];
    barrier q1[1];
    barrier q2[0];
    barrier q2[1];
    barrier q2[2];
    barrier q3[0];
    barrier q1[0];
    barrier q1[1];
    barrier q2[0];
    barrier q2[1];
    barrier q3[0];
    """
    module = loads(qasm_str)
    module.unroll()
    assert module.has_barriers() is True
    check_unrolled_qasm(dumps(module), expected_qasm)


def test_barrier_in_function():
    """Test that a barrier in a function is correctly parsed."""
    qasm_str = """OPENQASM 3.0;
    include "stdgates.inc";

    def my_function(qubit[4] a) {
        barrier a;
        return;
    }
    qubit[4] q;
    my_function(q);
    """

    expected_qasm = """OPENQASM 3.0;
    include "stdgates.inc";
    qubit[4] q;
    barrier q[0];
    barrier q[1];
    barrier q[2];
    barrier q[3];
    """
    module = loads(qasm_str)
    module.unroll()
    check_unrolled_qasm(dumps(module), expected_qasm)


def test_remove_barriers():
    qasm_str = """OPENQASM 3.0;
    include "stdgates.inc";

    qubit[2] q1;
    qubit[3] q2;
    qubit[1] q3;
    
    // full qubits
    barrier q1, q2, q3; 
    barrier q1[0], q1[1], q2[:], q3[0];

    // subset of qubits
    barrier q1, q2[0:2], q3[:];
    """

    expected_qasm = """OPENQASM 3.0;
    include "stdgates.inc";
    qubit[2] q1;
    qubit[3] q2;
    qubit[1] q3;
    """
    module = loads(qasm_str)
    assert module.has_barriers() is True
    module.remove_barriers()
    assert module.has_barriers() is False
    check_unrolled_qasm(dumps(module), expected_qasm)


def test_incorrect_barrier():

    undeclared = """
    OPENQASM 3.0;

    qubit[3] q1;

    barrier q2;
    """

    with pytest.raises(ValidationError, match=r"Missing register declaration for q2 .*"):
        loads(undeclared).validate()

    out_of_bounds = """
    OPENQASM 3.0;

    qubit[2] q1;

    barrier q1[:4];
    """

    with pytest.raises(
        ValidationError, match="Index 3 out of range for register of size 2 in qubit"
    ):
        loads(out_of_bounds).validate()

    duplicate = """
    OPENQASM 3.0;

    qubit[2] q1;

    barrier q1, q1;
    """

    with pytest.raises(ValidationError, match=r"Duplicate qubit .*argument"):
        loads(duplicate).validate()
