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

from pyqasm.entrypoint import load


def test_gate_depth():
    qasm3_string = """
    OPENQASM 3;
    include "stdgates.inc";

    gate my_gate_2(p) q {
        ry(p * 2) q;
    }

    gate my_gate(a, b, c) q {
        rx(5 * a) q;
        rz(2 * b / a) q;
        my_gate_2(a) q;
        rx(!a) q; // not a = False
        rx(c) q;
    }

    qubit q;
    int[32] m = 3;
    float[32] n = 6.0;
    bool o = true;
    my_gate(m, n, o) q;
    """
    result = load(qasm3_string)
    result.unroll()
    assert result.num_qubits == 1
    assert result.num_clbits == 0
    assert result.depth() == 5


def test_pow_gate_depth():
    qasm3_string = """
    OPENQASM 3;
    include "stdgates.inc";
    qubit q;
    inv @ pow(2) @ pow(4) @ h q;
    pow(-2) @ h q;
    """
    result = load(qasm3_string)
    result.unroll()
    assert result.num_qubits == 1
    assert result.num_clbits == 0
    assert result.depth() == 10


def test_inv_gate_depth():
    qasm3_string = """
    OPENQASM 3;
    include "stdgates.inc";
    qubit q;
    inv @ h q;
    inv @ y q;
    inv @ rx(0.5) q;
    inv @ s q;

    qubit[2] q2;
    inv @ cx q2;
    inv @ ccx q[0], q2;
    """
    result = load(qasm3_string)
    result.unroll()
    assert result.num_qubits == 3
    assert result.num_clbits == 0

    # Q(0) ->  H  -> Y -> Rx(-0.5) -> Sdg -> CCX
    # Q2(0)-> CX  -> .....................-> CCX
    # Q2(1)-> CX  -> .....................-> CCX

    assert result.depth() == 5


def test_qubit_depth_with_unrelated_measure_op():
    qasm3_string = """
    OPENQASM 3;
    include "stdgates.inc";
    qubit q1;
    qubit[3] q2;
    h q2;
    bit c; 
    c[0] = measure q2[0];
    c[0] = measure q2[1];
    c[0] = measure q2[2];
    // This should affect the depth as measurement will have to wait 
    c[0] = measure q1; 
    """
    result = load(qasm3_string)
    result.unroll()
    assert result.num_qubits == 4
    assert result.num_clbits == 1
    assert result.depth() == 5


def test_subroutine_depth():
    """Test that multiple function calls are correctly parsed."""
    qasm_str = """OPENQASM 3.0;
    include "stdgates.inc";

    def my_function(int[32] a, qubit q_arg) {
        h q_arg;
        rx (a) q_arg;
        return;
    }
    qubit[3] q;
    my_function(2, q[2]);
    my_function(1, q[1]);
    my_function(0, q[0]);
    """

    result = load(qasm_str)
    result.unroll()
    assert result.num_clbits == 0
    assert result.num_qubits == 3
    assert result.depth() == 2


def test_depth_with_multi_control():
    qasm3_string = """
    OPENQASM 3;
    include "stdgates.inc";
    qubit[2] q;
    cx q[0], q[1];

    qubit[4] q2;
    ccx q2[0], q2[1], q2[2];

    h q2[0];
    h q2[3];

    cx q2[0], q[0];
    
    """
    result = load(qasm3_string)
    result.unroll()
    assert result.num_qubits == 6
    assert result.num_clbits == 0
    assert result.depth() == 3


def test_depth_with_no_ops():
    qasm3_string = """
    OPENQASM 3;
    include "stdgates.inc";
    qubit q;
    """
    result = load(qasm3_string)
    result.unroll()
    assert result.num_qubits == 1
    assert result.num_clbits == 0
    assert result.depth() == 0


def test_after_removing_measurement():
    qasm3_string = """
    OPENQASM 3;
    include "stdgates.inc";
    qubit[3] q;
    h q;
    cx q[0], q[1];
    bit[3] c;
    c = measure q;
    cx q[1], q[2];

    """
    result = load(qasm3_string)
    result.unroll()
    assert result.num_qubits == 3
    assert result.num_clbits == 3
    assert result.depth() == 4

    result.remove_measurements()

    assert result.depth() == 3


def test_after_removing_barriers():
    qasm3_string = """
    OPENQASM 3;
    include "stdgates.inc";
    qubit[3] q;
    h q;
    barrier q;
    cx q[0], q[1];
    barrier q;
    cx q[1], q[2];

    """
    result = load(qasm3_string)
    result.unroll()
    assert result.num_qubits == 3
    assert result.num_clbits == 0
    assert result.depth() == 5

    result_copy = result.copy()  # save a copy for in_place=False test

    result.remove_barriers()
    assert result.depth() == 3

    result_copy_2 = result_copy.remove_barriers(in_place=False)
    assert result_copy_2.depth() == 3
