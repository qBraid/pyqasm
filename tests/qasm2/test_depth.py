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
Module containing unit tests for calculating program depth.

"""

from pyqasm.entrypoint import loads


def test_gate_depth():
    qasm3_string = """
    OPENQASM 2.0;
    include "stdgates.inc";

    gate my_gate_2(p) q {
        ry(p * 2) q;
    }

    gate my_gate(a, b, c) q {
        rx(5 * a) q;
        rz(2 * b / a) q;
        my_gate_2(a) q;
        rx(a) q; 
        rx(c) q;
    }

    qreg q[1];
    my_gate(1, 2, 3) q;
    """
    result = loads(qasm3_string)
    result.unroll()
    assert result.num_qubits == 1
    assert result.num_clbits == 0
    assert result.depth() == 5


def test_qubit_depth_with_unrelated_measure_op():
    qasm3_string = """
    OPENQASM 2.0;
    include "stdgates.inc";
    qreg q1;
    qreg q2[3];
    h q2;
    creg c; 
    measure q2[0] -> c;
    measure q2[1] -> c;
    measure q2[2] -> c;
    // This should affect the depth as measurement will have to wait 
    measure q1 -> c; 
    """
    result = loads(qasm3_string)
    result.unroll()
    assert result.num_qubits == 4
    assert result.num_clbits == 1
    assert result.depth() == 5


def test_depth_with_no_ops():
    qasm3_string = """
    OPENQASM 2.0;
    include "stdgates.inc";
    qreg q;
    """
    result = loads(qasm3_string)
    result.unroll()
    assert result.num_qubits == 1
    assert result.num_clbits == 0
    assert result.depth() == 0
