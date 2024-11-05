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
Module containing unit tests for transformations on qasm3 programs 

"""

from pyqasm.entrypoint import load
from tests.utils import check_unrolled_qasm


def test_remove_idle_qubits_qasm3_small():
    """Test that remove_idle_qubits for qasm3 string"""
    qasm3_str = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[4] q;
    h q[1];
    cx q[1], q[3];
    """

    expected_qasm3_str = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[2] q;
    h q[0];
    cx q[0], q[1];
    """
    module = load(qasm3_str)
    assert module.num_qubits == 4
    module.remove_idle_qubits()
    assert module.num_qubits == 2
    check_unrolled_qasm(module.unrolled_qasm, expected_qasm3_str)


def test_remove_idle_qubits_qasm3():
    """Test conversion of qasm3 to compressed contiguous qasm3"""
    qasm3_str = """
    OPENQASM 3.0;
    include "stdgates.inc";
    gate custom q1, q2, q3{
        x q1;
        y q2;
        z q3;
    }
    qreg q1[2];
    qubit[2] q2;
    qubit[3] q3;
    qubit q4;
    qubit[5]   q5;
    qreg qr[3];
    
    x q1[0];
    y q2[1];
    z q3;
    
    
    qubit[3] q6;
    
    cx q6[1], q6[2];
    """

    expected_qasm3_str = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[1] q1;
    qubit[1] q2;
    qubit[3] q3;
    x q1[0];
    y q2[0];
    z q3[0];
    z q3[1];
    z q3[2];
    qubit[2] q6;
    cx q6[0], q6[1];
    """

    module = load(qasm3_str)
    assert module.num_qubits == 19
    module.remove_idle_qubits()
    assert module.num_qubits == 7

    check_unrolled_qasm(module.unrolled_qasm, expected_qasm3_str)
