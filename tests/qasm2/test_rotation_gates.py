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
Module containing unit tests for parsing and unrolling programs that contain quantum
rotations in qasm2 format.

"""
from pyqasm.entrypoint import dumps, loads
from tests.utils import check_unrolled_qasm


def test_convert_qasm_one_param():
    """Test converting qasm string from one-parameter gate"""

    qasm_in = """
OPENQASM 2.0;
include 'qelib1.inc';
gate ryy(param0) q0,q1 { rx(pi/2) q0; rx(pi/2) q1; cx q0,q1; rz(param0) q1; cx q0,q1; rx(-pi/2) q0; rx(-pi/2) q1; }
qreg q[2];
ryy(2.0425171585294746) q[1],q[0];
"""
    expected_out = """
OPENQASM 2.0;
include 'qelib1.inc';
qreg q[2];
rx(1.5707963267948966) q[1];
rx(1.5707963267948966) q[0];
cx q[1], q[0];
rz(2.0425171585294746) q[0];
cx q[1], q[0];
rx(-1.5707963267948966) q[1];
rx(-1.5707963267948966) q[0];
"""
    result = loads(qasm_in)
    result.unroll()
    unrolled_qasm = dumps(result)
    check_unrolled_qasm(unrolled_qasm, expected_out)


def test_convert_qasm_two_param():
    """Test converting qasm string from two-parameter gate"""

    qasm_in = """
OPENQASM 2.0;
include 'qelib1.inc';
gate xx_minus_yy(param0,param1) q0,q1 { rz(-1.0*param1) q1; ry(param0/2) q0; }
qreg q[2];
xx_minus_yy(2.00367210595874,5.07865952845335) q[0],q[1];
"""
    expected_out = """
OPENQASM 2.0;
include 'qelib1.inc';
qreg q[2];
rz(-5.07865952845335) q[1];
ry(1.00183605297937) q[0];
"""
    result = loads(qasm_in)
    result.unroll()
    unrolled_qasm = dumps(result)
    check_unrolled_qasm(unrolled_qasm, expected_out)


def test_convert_qasm_three_qubit_gate():
    """Test converting qasm string that uses three qubit gate"""

    qasm_in = """
OPENQASM 2.0;
include 'qelib1.inc';
gate ryy(param0) q0,q1,q2 { rx(pi/2) q0; rx(pi/2) q1; cx q0,q2; rz(param0) q1; cx q0,q1; rx(-pi/2) q2; rx(-pi/2) q1; }
qreg q[3];
ryy(2.0425171585294746) q[1],q[0],q[2];
"""
    expected_out = """
OPENQASM 2.0;
include 'qelib1.inc';
qreg q[3];
rx(1.5707963267948966) q[1];
rx(1.5707963267948966) q[0];
cx q[1], q[2];
rz(2.0425171585294746) q[0];
cx q[1], q[0];
rx(-1.5707963267948966) q[2];
rx(-1.5707963267948966) q[0];
"""
    result = loads(qasm_in)
    result.unroll()
    unrolled_qasm = dumps(result)
    check_unrolled_qasm(unrolled_qasm, expected_out)


def test_convert_qasm_non_param_gate_def():
    """Test converting qasm string from non-parameterized gate def"""

    qasm_in = """
OPENQASM 2.0;
include 'qelib1.inc';
qreg q[2];
ecr q[0],q[1];
"""
    expected_out = """
OPENQASM 2.0;
include 'qelib1.inc';
qreg q[2];
s q[0];
rx(1.5707963267948966) q[1];
cx q[0], q[1];
x q[0];
"""
    result = loads(qasm_in)
    result.unroll()
    unrolled_qasm = dumps(result)
    check_unrolled_qasm(unrolled_qasm, expected_out)


def test_convert_qasm_recursive_gate_def():
    """Test converting qasm string from gate defined in terms of another gate"""

    qasm_in = """
OPENQASM 2.0;
include 'qelib1.inc';
gate rzx(param0) q0,q1 { h q1; cx q0,q1; rz(param0) q1; cx q0,q1; h q1; }
gate ecr q0,q1 { rzx(pi/4) q0,q1; x q0; rzx(-pi/4) q0,q1; }
qreg q[2];
ecr q[0], q[1];
"""
    expected_out = """
OPENQASM 2.0;
include 'qelib1.inc';
qreg q[2];
h q[1];
cx q[0], q[1];
rz(0.7853981633974483) q[1];
cx q[0], q[1];
h q[1];
x q[0];
h q[1];
cx q[0], q[1];
rz(-0.7853981633974483) q[1];
cx q[0], q[1];
h q[1];
"""
    result = loads(qasm_in)
    result.unroll()
    unrolled_qasm = dumps(result)
    check_unrolled_qasm(unrolled_qasm, expected_out)
