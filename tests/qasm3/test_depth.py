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
import pytest

from pyqasm.entrypoint import loads


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
    result = loads(qasm3_string)
    result.unroll()
    assert result.num_qubits == 1
    assert result.num_clbits == 0
    assert result.depth() == 5


@pytest.mark.skip(reason="Not implemented computing depth of external gates")
def test_gate_depth_external_function():
    qasm3_string = """
    OPENQASM 3;
    include "stdgates.inc";

    gate my_gate() q {
        h q;
        x q;
    }

    qubit q;
    my_gate() q;
    """
    result = loads(qasm3_string)
    result.unroll(external_gates=["my_gate"])
    assert result.num_qubits == 1
    assert result.num_clbits == 0
    assert result.depth() == 1


def test_pow_gate_depth():
    qasm3_string = """
    OPENQASM 3;
    include "stdgates.inc";
    qubit q;
    inv @ pow(2) @ pow(4) @ h q;
    pow(-2) @ h q;
    """
    result = loads(qasm3_string)
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
    result = loads(qasm3_string)
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
    result = loads(qasm3_string)
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

    result = loads(qasm_str)
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
    result = loads(qasm3_string)
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
    result = loads(qasm3_string)
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
    result = loads(qasm3_string)
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
    result = loads(qasm3_string)
    result.unroll()
    assert result.num_qubits == 3
    assert result.num_clbits == 0
    assert result.depth() == 5

    result_copy = result.copy()  # save a copy for in_place=False test

    result.remove_barriers()
    assert result.depth() == 3

    result_copy_2 = result_copy.remove_barriers(in_place=False)
    assert result_copy_2.depth() == 3


def test_qasm3_depth_sparse_operations():
    """Test calculating depth of qasm3 circuit with sparse operations"""
    qasm_string = """
    OPENQASM 3.0;
    gate iswap q0,q1 { s q0; s q1; h q0; cx q0,q1; cx q1,q0; h q1; }
    bit[2] b;
    qubit[2] q;
    s q[0];
    iswap q[0], q[1];
    barrier q;
    z q[1];
    """
    result = loads(qasm_string)
    result.unroll()

    assert result.depth() == 8


def test_qasm3_depth_measurement_direct():
    """Test calculating depth of qasm3 circuit with direct measurements"""
    qasm_string = """
OPENQASM 3.0;
gate iswap q0,q1 { s q0; s q1; h q0; cx q0,q1; cx q1,q0; h q1; }
bit[2] b;
qubit[2] q;
s q[0];
iswap q[0], q[1];
z q[1];
b[0] = measure q[0];
b[1] = measure q[1];
    """
    result = loads(qasm_string)
    result.unroll()

    assert result.depth() == 8


def test_qasm3_depth_measurement_indirect():
    """Test calculating depth of qasm3 circuit with indirect measurements"""
    qasm_string = """
OPENQASM 3.0;
include "stdgates.inc";
bit[3] c;
qubit[3] q;
cx q[1], q[2];
x q[0];
cx q[1], q[2];
h q[0];
rx(5.917500589065494) q[1];
c[0] = measure q[0];
c[1] = measure q[1];
c[2] = measure q[2];
    """
    result = loads(qasm_string)
    result.unroll()

    assert result.depth() == 4


@pytest.mark.parametrize(
    "program, expected_depth",
    [
        (
            """
OPENQASM 3.0;
include "stdgates.inc";
         
qubit[2] q;
qubit[2] r;
qubit[2] s;
         
h q[0];
h q[1];
h r[0];
""",
            1,
        ),
        (
            """
OPENQASM 3.0;
include "stdgates.inc";

qreg q[2];
creg c[2];

h q[0];
cx q[0], q[1];
h q;

measure q -> c;
     """,
            4,
        ),
        (
            """
OPENQASM 3.0;
include "stdgates.inc";

qreg q[2];

reset q;
reset q[0];
""",
            2,
        ),
        (
            """
OPENQASM 3.0;
include "stdgates.inc";

qreg q[2];

h q[0];
h q[0];
h q[0];
h q[0];

barrier q;

h q[1];
""",
            6,
        ),
    ],
)
def test_qasm3_depth_no_branching(program, expected_depth):
    """Test calculating depth of qasm3 circuit"""
    result = loads(program)
    result.unroll()
    assert result.depth() == expected_depth


@pytest.mark.skip(reason="Not implemented branching conditions depth")
@pytest.mark.parametrize(
    "program, expected_depth",
    [
        (
            """
OPENQASM 3.0;
include "stdgates.inc";

qreg q[2];
creg c[2];

h q[0];
cx q[0], q[1];
measure q[0] -> c[0];
measure q[1] -> c[1];

if (c==1) x q[0];
""",
            4,
        ),
        (
            """
OPENQASM 3.0;
include "stdgates.inc";

qreg q[2];
creg c[2];

h q[0];
cx q[0], q[1];
measure q[0] -> c[0];

if (c==1) measure q[1] -> c[1];
""",
            4,
        ),
        (
            """
OPENQASM 3.0;
include "stdgates.inc";
qreg q1[3];
qreg q2[3];
creg c1[3];
creg c2[3];

gate big_gate a1, a2, a3, b1, b2, b3
{
    h a1;
}
x q1[0];
barrier q1;
big_gate q1[0],q1[1],q1[2],q2[0],q2[1],q2[2];
x q1[0];
measure q1 -> c1;
if(c1==1) x q2[0];
if(c1==2) x q2[2];
if(c1==3) x q2[1];
measure q2 -> c2;
""",
            8,
        ),
    ],
)
def test_qasm3_depth_branching(program, expected_depth):
    """Test calculating depth of qasm3 circuit with branching conditions"""
    result = loads(program)
    result.unroll()
    assert result.depth() == expected_depth
