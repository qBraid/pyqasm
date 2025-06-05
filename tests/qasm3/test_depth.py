# Copyright 2025 qBraid
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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


QASM3_STRING_1 = """
OPENQASM 3;
include "stdgates.inc";

gate my_gate() q {
    h q;
    x q;
}

qubit q;
my_gate() q;
"""

QASM3_STRING_2 = """
OPENQASM 3.0;
include "stdgates.inc";
gate my_gate q1, q2 {
  h q1;
  cx q1, q2;
  h q2;
}
qubit[2] q;
my_gate q[0], q[1];
"""

QASM3_STRING_3 = """
OPENQASM 3.0;
include "stdgates.inc";
gate my_gate q1, q2 { }
qubit[2] q;
my_gate q[0], q[1];
"""


@pytest.mark.parametrize(
    ["input_qasm_str", "first_depth", "second_depth", "num_qubits"],
    [
        (QASM3_STRING_1, 1, 2, 1),
        (QASM3_STRING_2, 1, 3, 2),
        (QASM3_STRING_3, 1, 0, 2),
    ],
)
def test_gate_depth_external_function(input_qasm_str, first_depth, second_depth, num_qubits):
    result = loads(input_qasm_str)
    result.unroll(external_gates=["my_gate"])
    assert result.num_qubits == num_qubits

    for i in range(num_qubits):
        assert result._qubit_depths[("q", i)].num_gates == 1

    assert result.num_clbits == 0
    assert result.depth() == first_depth

    # Check that unrolling with no external_gates flushes the internally stored
    # external gates and influences the depth calculation
    result.unroll()
    assert result.depth() == second_depth


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


def test_ctrl_depth():
    qasm3_string = """
    OPENQASM 3;
    include "stdgates.inc";
    qubit[3] q;
    ctrl @ x q[0], q[1]; 
    ctrl @ x q[0], q[2];
    """
    result = loads(qasm3_string)
    result.unroll()
    assert result.depth() == 2


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
if (c==3) measure q[1] -> c[1];
""",
            5,
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
        (
            """
OPENQASM 3.0;
include "stdgates.inc";
gate custom a, b{
    cx a, b;
    h a;
}
qubit[4] q;
bit[4] c;
bit[4] c0;
h q;
measure q -> c0;
if(c0[0]){
    x q[0];
    cx q[0], q[1];
    if (c0[1]){
        cx q[1], q[2];
    }
}
if (c[0]){
    custom q[2], q[3];
}
array[int[32], 8] arr;
arr[0] = 1;
if(arr[0] >= 1){
    h q[0];
    h q[1];
}
""",
            4,
        ),
        (
            """
OPENQASM 3.0;
include "stdgates.inc";
qubit[1] q;
bit[4] c;
if(c == 3){
    h q[0];
}
if(c >= 3){
    h q[0];
} else {
    x q[0];
}
if(c <= 3){
    h q[0];
} else {
    x q[0];
}
if(c[0] < 4){
    h q[0];
} else {
    x q[0];
}
""",
            4,
        ),
        (
            """
OPENQASM 3.0;
include "stdgates.inc";
qubit[2] q;
bit[2] c;
h q[0];
cx q[0], q[1];
c[0] = measure q[0];
c[1] = measure q[1];
if (c[0] == false) {
  if (c[1] == true) {
    x q[0];
  }
  else {
    if (c[1] == false){
      x q[1];
    }
    else {
      z q[0];
    }
  }
}

if (c == 0) {
    x q[0];
}
else {
    y q[1];
}
x q[0];
""",
            6,
        ),
    ],
)
def test_qasm3_depth_branching(program, expected_depth):
    """Test calculating depth of qasm3 circuit with branching conditions"""
    result = loads(program)
    result.unroll()
    result.remove_barriers()
    assert result.depth() == expected_depth
