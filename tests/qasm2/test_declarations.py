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
Module containing unit tests for parsing and unrolling programs that contain quantum
declarations.

"""
from pyqasm.unroller import unroll
from tests.utils import check_unrolled_qasm


# 1. Test qubit declarations in different ways
def test_qubit_declarations():
    """Test qubit declarations in different ways"""
    qasm2_string = """
    OPENQASM 2;
    qreg q3[3];
    qreg q;
    
    """

    expected_qasm = """OPENQASM 2;
    include "stdgates.inc";
    qreg q3[3];
    qreg q[1];
    """

    unrolled_qasm = unroll(qasm2_string)
    check_unrolled_qasm(unrolled_qasm, expected_qasm)


# 2. Test clbit declarations in different ways
def test_clbit_declarations():
    """Test clbit declarations in different ways"""
    qasm2_string = """
    OPENQASM 2;
    include "stdgates.inc";
    
    creg c3[3];
    creg c;
    """

    expected_qasm = """OPENQASM 2;
    include "stdgates.inc";
    creg c3[3];
    creg c[1];
    """

    unrolled_qasm = unroll(qasm2_string)
    check_unrolled_qasm(unrolled_qasm, expected_qasm)


# 3. Test qubit and clbit declarations in different ways
def test_qubit_clbit_declarations():
    """Test qubit and clbit declarations in different ways"""
    qasm2_string = """
    OPENQASM 2;
    include "stdgates.inc";

    // qubit declarations
    qreg q1[1];
    qreg q2[2];

    // clbit declarations
    creg c1[1];
    creg c2[2];
    """

    expected_qasm = """OPENQASM 2;
    include "stdgates.inc";
    qreg q1[1];
    qreg q2[2];
    creg c1[1];
    creg c2[2];
    """

    unrolled_qasm = unroll(qasm2_string)
    check_unrolled_qasm(unrolled_qasm, expected_qasm)
