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
Module containing unit tests for while loops in OpenQASM 3.0.

"""

import pytest

from pyqasm import loads
from pyqasm.exceptions import LoopLimitExceededError, ValidationError

from tests.utils import check_single_qubit_gate_op

def test_while_loop_with_continue():
    """Test a while loop with break and continue statements."""
    qasm_str = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[3] q;
    bit[3] c;
    int i = 0;
    while (i < 3) {
        if (i == 1) {
            i += 1;
            continue;
        }
        h q[i];
        i += 1;
    }
    measure q -> c;

    """

    result = loads(qasm_str)
    result.unroll()


    check_single_qubit_gate_op(result.unrolled_ast, 2, [0, 2], "h")

def test_while_loop_with_break():
    qasm_str = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[3] q;
    bit[3] c;
    int i = 0;
    while (i < 3) {
        if (i == 1) {
            break;
        }
        h q[i];
        i += 1;
    }
    measure q -> c;
    """

    result = loads(qasm_str)
    result.unroll()

    check_single_qubit_gate_op(result.unrolled_ast, 1, [0], "h")


def test_while_loop_unroll_qasm_output():
    """Test that unrolling a while loop produces the expected QASM string."""
    qasm_str = """
    OPENQASM 3.0;
    qubit q;
    int i = 0;
    while (i < 2) {
        h q;
        i += 1;
    }
    """
    result = loads(qasm_str)
    result.unroll()
    # Validate number of h q operations
    check_single_qubit_gate_op(result.unrolled_ast, 2, [0, 0], "h")


def test_empty_while_loop_ignored():
    """Test that an empty while loop is ignored (no effect)."""
    qasm_str = """
    OPENQASM 3.0;
    qubit q;
    int i = 0;
    while (i < 0) {
    }
    h q;
    """
    result = loads(qasm_str)
    result.unroll()
    # Only one h q operation should be present
    check_single_qubit_gate_op(result.unrolled_ast, 1, [0], "h")


def test_nested_while_loops_break_continue():
    """Test nested while loops: break/continue in inner loop does not affect outer loop."""
    qasm_str = """
    OPENQASM 3.0;
    qubit q;
    int i = 0;
    int j = 0;
    while (i < 2) {
        j = 0;
        while (j < 2) {
            if (j == 1) {
                break;
            }
            j += 1;
        }
        i += 1;
    }
    h q;
    """
    result = loads(qasm_str)
    result.unroll()
    check_single_qubit_gate_op(result.unrolled_ast, 1, [0], "h")


def test_mixed_for_while_loops():
    """Test a for loop inside a while loop and vice versa."""
    qasm_str = """
    OPENQASM 3.0;
    qubit[2] q;
    int i = 0;
    while (i < 2) {
        for int j in {0, 1} {
            h q[j];
        }
        i += 1;
    }
    """
    result = loads(qasm_str)
    result.unroll()
    # Validate number of h operations and indices
    check_single_qubit_gate_op(result.unrolled_ast, 4, [0, 1, 0, 1], "h")


def test_while_loop_scope():
    """Test that while loop properly handles variable scoping."""
    qasm_str = """
    OPENQASM 3.0;
    qubit q;
    int i = 0;
    int j = 0;
    while (i < 2) {
        int k = i;
        h q;
        j += k;
        i += 1;
    }
    """
    result = loads(qasm_str)
    result.unroll()
    check_single_qubit_gate_op(result.unrolled_ast, 2, [0, 0], "h")

def test_while_loop_limit_exceeded():
    """Test that exceeding the loop limit raises LoopLimitExceeded."""
    qasm_str = """
    OPENQASM 3.0;
    qubit q;
    int i = 0;
    while (i < 1e10) {
        i += 1;
    }
    """
    result = loads(qasm_str)
    with pytest.raises(LoopLimitExceededError):
        result.unroll()

def test_while_loop_quantum_measurement():
    """Test that while loop with quantum measurement in condition raises error."""
    qasm_str = """
    OPENQASM 3.0;
    qubit q;
    bit c;
    c = measure q;
    while (c) {
        h q;
        c = measure q;
    }
    """
    with pytest.raises(ValidationError, match="quantum measurement"):
        result = loads(qasm_str)
        result.unroll()

def test_while_loop_measurement_complex_condition():
    qasm_str = """
    OPENQASM 3.0;
    qubit q;
    bit c;
    c = measure q;
    while (!(!c)) {
        x q;
        c = measure q;
    }
    """
    with pytest.raises(ValidationError, match="quantum measurement"):
        result = loads(qasm_str)
        result.unroll()

def test_while_loop_measurement_binary_expr():
    qasm_str = """
    OPENQASM 3.0;
    qubit q;
    bit c;
    c = measure q;
    while (c == 1) {
        h q;
        c = measure q;
    }
    """
    with pytest.raises(ValidationError, match="quantum measurement"):
        result = loads(qasm_str)
        result.unroll()
