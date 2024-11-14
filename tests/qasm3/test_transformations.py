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

from pyqasm.entrypoint import dumps, loads
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
    module = loads(qasm3_str)
    assert module.num_qubits == 4
    module.remove_idle_qubits()
    assert module.num_qubits == 2
    check_unrolled_qasm(dumps(module), expected_qasm3_str)


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

    module = loads(qasm3_str)
    assert module.num_qubits == 19
    module.remove_idle_qubits()
    assert module.num_qubits == 7

    check_unrolled_qasm(dumps(module), expected_qasm3_str)


def test_reverse_qubit_order_qasm3():
    """Test the reverse qubit ordering function for qasm3 string"""
    qasm3_str = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[2] q;
    qubit[4] q2;
    qubit q3;
    bit[1] c; 

    cnot q[0], q[1];
    cnot q2[0], q2[1];
    x q2[3];
    cnot q2[0], q2[2];
    x q3;
    c[0] = measure q2[0];
    """

    expected_qasm3_str = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[2] q;
    qubit[4] q2;
    qubit[1] q3;
    bit[1] c;

    cx q[1], q[0];
    cx q2[3], q2[2];
    x q2[0];
    cx q2[3], q2[1];
    x q3[0];

    c[0] = measure q2[3];
    """

    module = loads(qasm3_str)
    module.reverse_qubit_order()
    check_unrolled_qasm(dumps(module), expected_qasm3_str)


def test_populate_idle_qubits_qasm3():
    """Test the populate idle qubits function for qasm3 string"""

    qasm3_str = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[2] q;
    qubit[4] q2;
    qubit q3;
    bit[1] c;

    cnot q;
    """

    expected_qasm3_str = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[2] q;
    qubit[4] q2;
    qubit[1] q3;
    bit[1] c;

    cnot q;
    id q2[0];
    id q2[1];
    id q2[2];
    id q2[3];
    id q3[0];
    """

    module = loads(qasm3_str)
    module.populate_idle_qubits()
    check_unrolled_qasm(dumps(module), expected_qasm3_str)


def test_populate_idle_qubits_for_no_idle_qubits():
    """Test the populate idle qubits function for qasm3 string"""

    qasm3_str = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[2] q;
    qubit[4] q2;
    qubit q3;
    bit[1] c;

    h q;
    h q2;
    h q3;
    """
    # no change in the qasm
    expected_qasm3_str = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[2] q;
    qubit[4] q2;
    qubit[1] q3;
    bit[1] c;
    
    h q;
    h q2;
    h q3;
    """

    module = loads(qasm3_str)
    module.populate_idle_qubits()
    check_unrolled_qasm(dumps(module), expected_qasm3_str)


def test_populate_idle_qubits_increases_depth_by_one():
    """Test that the depth of the program increases by one when populating idle qubits"""
    qasm3_str = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[2] q;
    qubit[4] q2;
    qubit q3;
    
    """
    module = loads(qasm3_str)
    original_depth = module.depth()
    module.populate_idle_qubits()
    assert module.depth() == original_depth + 1
