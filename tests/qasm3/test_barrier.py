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
Module containing unit tests for the barrier operation.

"""

import pytest

from pyqasm.entrypoint import dumps, loads
from pyqasm.exceptions import ValidationError
from tests.utils import check_unrolled_qasm


# 1. Test barrier operations in different ways
def test_barrier():
    qasm_str = """
    OPENQASM 3.0;
    include "stdgates.inc";

    qubit[2] q1;
    qubit[3] q2;
    qubit q3;
    
    // full qubits
    barrier q1, q2, q3; 
    barrier q1[0], q1[1], q2[:], q3[0];

    // subset of qubits
    barrier q1, q2[0:2], q3[:];
    """

    expected_qasm = """OPENQASM 3.0;
    include "stdgates.inc";
    qubit[2] q1;
    qubit[3] q2;
    qubit[1] q3;
    barrier q1[0], q1[1], q2[0], q2[1], q2[2], q3[0];
    barrier q1[0], q1[1], q2[0], q2[1], q2[2], q3[0];
    barrier q1[0], q1[1], q2[0], q2[1], q3[0];
    """
    module = loads(qasm_str)
    module.unroll()
    assert module.has_barriers() is True
    check_unrolled_qasm(dumps(module), expected_qasm)


def test_barrier_in_function():
    """Test that a barrier in a function is correctly parsed."""
    qasm_str = """OPENQASM 3.0;
    include "stdgates.inc";

    def my_function(qubit[4] a) {
        barrier a;
        return;
    }
    qubit[4] q;
    my_function(q);
    """

    expected_qasm = """OPENQASM 3.0;
    include "stdgates.inc";
    qubit[4] q;
    barrier q[0], q[1], q[2], q[3];
    """
    module = loads(qasm_str)
    module.unroll()
    check_unrolled_qasm(dumps(module), expected_qasm)


def test_remove_barriers():
    qasm_str = """OPENQASM 3.0;
    include "stdgates.inc";

    qubit[2] q1;
    qubit[3] q2;
    qubit[1] q3;
    
    // full qubits
    barrier q1, q2, q3; 
    barrier q1[0], q1[1], q2[:], q3[0];

    // subset of qubits
    barrier q1, q2[0:2], q3[:];
    """

    expected_qasm = """OPENQASM 3.0;
    include "stdgates.inc";
    qubit[2] q1;
    qubit[3] q2;
    qubit[1] q3;
    """
    module = loads(qasm_str)
    assert module.has_barriers() is True
    module.remove_barriers()
    assert module.has_barriers() is False
    check_unrolled_qasm(dumps(module), expected_qasm)


def test_remove_barriers_inside_box_and_branch():
    """Barriers nested in a box or an if block must be found and removed too (see #342)."""
    qasm_str = """OPENQASM 3.0;
    include "stdgates.inc";
    qubit[2] q;
    bit c;
    h q[0];
    box {
        barrier q;
        x q[1];
    }
    if (c == 1) {
        barrier q;
    }
    """
    expected_qasm = """OPENQASM 3.0;
    include "stdgates.inc";
    qubit[2] q;
    bit[1] c;
    h q[0];
    box {
        x q[1];
    }
    if (c[0] == true) {
    }
    """
    module = loads(qasm_str)
    module.unroll()
    assert module.has_barriers() is True
    module.remove_barriers()
    assert module.has_barriers() is False
    check_unrolled_qasm(dumps(module), expected_qasm)


def test_has_and_remove_barriers_inside_loop_before_unroll():
    """Barriers inside a loop or switch must be visible before unroll() (issue #354)."""
    qasm_str = """OPENQASM 3.0;
    include "stdgates.inc";
    qubit[2] q;
    for int i in [0:1] { h q[i]; barrier q; }
    """
    module = loads(qasm_str)
    assert module.has_barriers() is True

    module = loads(qasm_str)
    module.remove_barriers()
    assert module.has_barriers() is False
    module.unroll()
    unrolled_qasm = dumps(module)
    assert "barrier" not in unrolled_qasm
    # the loop's gates must survive the removal pass
    assert unrolled_qasm.count("h q[") == 2


def test_remove_barriers_not_in_place_leaves_the_original_alone():
    """Filtering rewrites nested bodies in place, so it must run on the returned copy."""
    qasm_str = """OPENQASM 3.0;
    include "stdgates.inc";
    qubit[2] q;
    h q[0];
    box {
        barrier q;
        x q[1];
    }
    """
    module = loads(qasm_str)
    module.unroll()
    new_module = module.remove_barriers(in_place=False)

    assert "barrier" not in dumps(new_module)
    assert "barrier" in dumps(module)


def test_unroll_barrier():
    qasm_str = """
    OPENQASM 3.0;
    include "stdgates.inc";

    qubit[2] q1;
    qubit[3] q2;
    qubit q3;

    // barriers
    barrier q1, q2, q3;
    barrier q2[:3];
    barrier q3[0];
    """
    expected_qasm = """OPENQASM 3.0;
    include "stdgates.inc";
    qubit[2] q1;
    qubit[3] q2;
    qubit[1] q3;
    barrier q1, q2, q3;
    barrier q2[:3];
    barrier q3[0];
    """
    module = loads(qasm_str)
    assert module.has_barriers() is True
    module.unroll(unroll_barriers=False)
    assert module.has_barriers() is True
    check_unrolled_qasm(dumps(module), expected_qasm)


def test_incorrect_barrier(caplog):

    undeclared = """
    OPENQASM 3.0;

    qubit[3] q1;

    barrier q2;
    """

    with pytest.raises(
        ValidationError, match="Missing qubit register declaration for 'q2' in QuantumBarrier"
    ):
        with caplog.at_level("ERROR"):
            loads(undeclared).validate()

    assert "Error at line 6, column 4" in caplog.text
    assert "barrier q2;" in caplog.text

    caplog.clear()

    out_of_bounds = """
    OPENQASM 3.0;

    qubit[2] q1;

    barrier q1[:4];
    """

    with pytest.raises(
        ValidationError, match="Index 3 out of range for register of size 2 in qubit"
    ):
        with caplog.at_level("ERROR"):
            loads(out_of_bounds).validate()

    assert "Error at line 6, column 4" in caplog.text
    assert "barrier q1[:4];" in caplog.text
