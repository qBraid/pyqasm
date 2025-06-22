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
    assert result.depth(decompose_gates=False) == 5


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
