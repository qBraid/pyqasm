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
Module containing unit tests for unrolling measurement operations.

"""
import pytest

from pyqasm.exceptions import ValidationError
from pyqasm.unroller import unroll
from pyqasm.validate import validate
from tests.utils import check_unrolled_qasm


# 6. Test measurement operations in different ways
def test_measure():
    qasm3_string = """
    OPENQASM 3;

    qubit[2] q1;
    qubit[5] q2;
    qubit q3;

    bit[2] c1;
    bit c2;

    // supported
    c1 = measure q1;
    measure q1 -> c1;
    c2[0] = measure q3[0];
    measure q1[:1] -> c1[1];
    measure q2[{0, 1}] -> c1[{1, 0}];

    """

    expected_qasm = """OPENQASM 3;
    include "stdgates.inc";
    qubit[2] q1;
    qubit[5] q2;
    qubit[1] q3;
    bit[2] c1;
    bit[1] c2;
    c1[0] = measure q1[0]; 
    c1[1] = measure q1[1]; 
    c1[0] = measure q1[0]; 
    c1[1] = measure q1[1]; 
    c2[0] = measure q3[0]; 
    c1[1] = measure q1[0]; 
    c1[1] = measure q2[0]; 
    c1[0] = measure q2[1]; 
    """

    unrolled_qasm = unroll(qasm3_string).unrolled_qasm
    check_unrolled_qasm(unrolled_qasm, expected_qasm)


def test_incorrect_measure():
    def run_test(qasm3_code, error_message):
        with pytest.raises(ValidationError, match=error_message):
            validate(qasm3_code)

    # Test for undeclared register q2
    run_test(
        """
        OPENQASM 3;
        qubit[2] q1;
        bit[2] c1;
        c1[0] = measure q2[0];  // undeclared register
    """,
        r"Missing register declaration for q2 .*",
    )

    # Test for undeclared register c2
    run_test(
        """
        OPENQASM 3;
        qubit[2] q1;
        bit[2] c1;
        measure q1 -> c2;  // undeclared register
    """,
        r"Missing register declaration for c2 .*",
    )

    # Test for size mismatch between q1 and c2
    run_test(
        """
        OPENQASM 3;
        qubit[2] q1;
        bit[2] c1;
        bit[1] c2;
        c2 = measure q1;  // size mismatch
    """,
        r"Register sizes of q1 and c2 do not match .*",
    )

    # Test for size mismatch between q1 and c2 in ranges
    run_test(
        """
        OPENQASM 3;
        qubit[5] q1;
        bit[4] c1;
        bit[1] c2;
        c1[:3] = measure q1;  // size mismatch
    """,
        r"Register sizes of q1 and c1 do not match .*",
    )

    # Test for out of bounds index for q1
    run_test(
        """
        OPENQASM 3;
        qubit[2] q1;
        bit[2] c1;
        measure q1[3] -> c1[0];  // out of bounds
    """,
        r"Index 3 out of range for register of size 2 in qubit",
    )

    # Test for out of bounds index for c1
    run_test(
        """
        OPENQASM 3;
        qubit[2] q1;
        bit[2] c1;
        measure q1 -> c1[3];  // out of bounds
    """,
        r"Index 3 out of range for register of size 2 in clbit",
    )
