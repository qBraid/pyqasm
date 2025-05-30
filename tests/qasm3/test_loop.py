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
Module containing unit tests for parsing and unrolling programs that contain loops.

"""

import pytest

from pyqasm.entrypoint import loads
from pyqasm.exceptions import ValidationError, LoopLimitExceeded
from tests.utils import (
    check_single_qubit_gate_op,
    check_single_qubit_rotation_op,
    check_two_qubit_gate_op,
)

EXAMPLE_WITHOUT_LOOP = """
OPENQASM 3.0;
include "stdgates.inc";

qubit[4] q;
bit[4] c;

h q;

cx q[0], q[1];
cx q[1], q[2];
cx q[2], q[3];

measure q->c;
"""


def test_convert_qasm3_for_loop():
    """Test converting a QASM3 program that contains a for loop."""
    result = loads(
        """
        OPENQASM 3.0;
        include "stdgates.inc";

        qubit[4] q;
        bit[4] c;

        h q;
        for int i in [0:2]{
            cx q[i], q[i+1];
        }
        measure q->c;
        """
    )
    result.unroll()
    assert result.num_qubits == 4
    assert result.num_clbits == 4

    check_single_qubit_gate_op(result.unrolled_ast, 4, [0, 1, 2, 3], "h")
    check_two_qubit_gate_op(result.unrolled_ast, 3, [(0, 1), (1, 2), (2, 3)], "cx")


def test_convert_qasm3_for_loop_shadow():
    """Test for loop where loop variable shadows variable from global scope."""
    result = loads(
        """
        OPENQASM 3.0;
        include "stdgates.inc";

        qubit[4] q;
        bit[4] c;

        int i = 3;

        h q;
        for int i in [0:2]{
            cx q[i], q[i+1];
        }
        h q[i];
        measure q->c;
        """
    )
    result.unroll()

    assert result.num_clbits == 4
    assert result.num_qubits == 4

    check_single_qubit_gate_op(result.unrolled_ast, 5, [0, 1, 2, 3, 3], "h")
    check_two_qubit_gate_op(result.unrolled_ast, 3, [(0, 1), (1, 2), (2, 3)], "cx")


def test_convert_qasm3_for_loop_enclosing():
    """Test for loop where variable from outer loop is accessed from inside the loop."""
    result = loads(
        """
        OPENQASM 3.0;
        include "stdgates.inc";

        qubit[4] q;
        bit[4] c;

        int j = 3;

        h q;
        for int i in [0:2]{
            cx q[i], q[i+1];
            h q[j];
        }
        measure q->c;
        """
    )
    result.unroll()

    assert result.num_clbits == 4
    assert result.num_qubits == 4

    check_single_qubit_gate_op(result.unrolled_ast, 7, [0, 1, 2, 3, 3, 3, 3], "h")
    check_two_qubit_gate_op(result.unrolled_ast, 3, [(0, 1), (1, 2), (2, 3)], "cx")


def test_convert_qasm3_for_loop_enclosing_modifying():
    """Test for loop where variable from outer loop is modified from inside the loop."""
    result = loads(
        """
        OPENQASM 3.0;
        include "stdgates.inc";

        qubit[4] q;
        bit[4] c;

        int j = 0;

        h q;
        for int i in [0:2]{
            cx q[i], q[i+1];
            h q[j];
            j += i;
        }
        h q[j];
        measure q->c;
        """
    )
    result.unroll()

    assert result.num_clbits == 4
    assert result.num_qubits == 4

    check_single_qubit_gate_op(result.unrolled_ast, 8, [0, 1, 2, 3, 0, 0, 1, 3], "h")
    check_two_qubit_gate_op(result.unrolled_ast, 3, [(0, 1), (1, 2), (2, 3)], "cx")


def test_convert_qasm3_for_loop_discrete_set():
    """Test converting a QASM3 program that contains a for loop initialized from a DiscreteSet."""
    result = loads(
        """
        OPENQASM 3.0;
        include "stdgates.inc";

        qubit[4] q;
        bit[4] c;

        h q;
        for int i in {0, 1, 2} {
            cx q[i], q[i+1];
        }
        measure q->c;
        """
    )
    result.unroll()

    assert result.num_clbits == 4
    assert result.num_qubits == 4

    check_single_qubit_gate_op(result.unrolled_ast, 4, [0, 1, 2, 3], "h")
    check_two_qubit_gate_op(result.unrolled_ast, 3, [(0, 1), (1, 2), (2, 3)], "cx")


def test_function_executed_in_loop():
    """Test that a function executed in a loop is correctly parsed."""
    qasm_str = """OPENQASM 3;
    include "stdgates.inc";

    def my_function(qubit q_arg, float[32] b) {
        rx(b) q_arg;
        return;
    }
    qubit[5] q;

    int[32] n = 2;
    float[32] b = 3.14;

    for int i in [0:n] {
        my_function(q[i], i*b);
    }
    """

    result = loads(qasm_str)
    result.unroll()

    assert result.num_qubits == 5
    assert result.num_clbits == 0

    check_single_qubit_rotation_op(
        result.unrolled_ast, 3, list(range(3)), [0, 3.14, 2 * 3.14], "rx"
    )


def test_loop_inside_function():
    """Test that a function with a loop is correctly parsed."""
    qasm_str = """OPENQASM 3;
    include "stdgates.inc";

    def my_function(qubit[3] q2) {
        for int[32] i in [0:2] {
            h q2[i];
        }
        return;
    }
    qubit[3] q1;
    my_function(q1);
    """

    result = loads(qasm_str)
    result.unroll()

    assert result.num_qubits == 3
    assert result.num_clbits == 0

    check_single_qubit_gate_op(result.unrolled_ast, 3, [0, 1, 2], "h")


def test_function_in_nested_loop():
    """Test that a function executed in a nested loop is correctly parsed."""
    qasm_str = """OPENQASM 3;
    include "stdgates.inc";

    def my_function(qubit q_arg, float[32] b) {
        rx(b) q_arg;
        return;
    }
    qubit[5] q;

    int[32] n = 2;
    float[32] b = 3.14;

    for int i in [0:n] {
        for int j in [0:n] {
            my_function(q[i], j*b);
        }
    }

    my_function(q[0], 2*b);
    """

    result = loads(qasm_str)
    result.unroll()

    assert result.num_qubits == 5
    assert result.num_clbits == 0

    check_single_qubit_rotation_op(
        result.unrolled_ast,
        10,
        [0, 0, 0, 1, 1, 1, 2, 2, 2, 0],
        [0, 3.14, 2 * 3.14, 0, 3.14, 2 * 3.14, 0, 3.14, 2 * 3.14, 2 * 3.14],
        "rx",
    )


@pytest.mark.skip(reason="Not implemented nested functions yet")
def test_loop_in_nested_function_call():
    qasm3_string = """
    OPENQASM 3;
    include "stdgates.inc";
    def my_function_1(qubit q1, int[32] a){
        for int[32] i in [0:2]{
            rx(a*i) q1;
        }
    }

    def my_function_2(qubit q2, int[32] b){
        my_function_1(q2, b);
    }

    qubit q;
    my_function_2(q, 3);
    """
    result = loads(qasm3_string)
    result.unroll()

    assert result.num_clbits == 0
    assert result.num_qubits == 1

    check_single_qubit_rotation_op(result.unrolled_ast, 3, [0, 0, 0], [0, 3, 6], "rx")


def test_convert_qasm3_for_loop_unsupported_type(caplog):
    """Test correct error when converting a QASM3 program that contains a for loop initialized from
    an unsupported type."""
    with pytest.raises(
        ValidationError,
        match=(
            "Unexpected type <class 'openqasm3.ast.BitstringLiteral'>"
            " of set_declaration in loop."
        ),
    ):
        with caplog.at_level("ERROR"):
            loads(
                """
                OPENQASM 3.0;
                include "stdgates.inc";

                qubit[4] q;
                bit[4] c;

                h q;
                for bit b in "001" {
                    x q[b];
                }
                measure q->c;
                """,
            ).validate()

    assert "Error at line 9, column 16" in caplog.text
    assert 'for bit b in "001"' in caplog.text


def test_while_loop_with_break_and_continue():
    """Test a while loop with break and continue statements."""
    qasm_str = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[2] q;
    bit[2] c;
    int i = 0;
    while (i < 2) {
        h q[i];
        if (i == 0) {
            i += 1;
            continue;
        }
        if (i == 1) {
            break;
        }
        i += 1;
    }
    measure q -> c;
    """
    result = loads(qasm_str)
    result.unroll()
    assert result.num_qubits == 2
    assert result.num_clbits == 2
    check_single_qubit_gate_op(result.unrolled_ast, 2, [0, 1], "h")


def test_while_loop_limit_exceeded():
    """Test that exceeding the loop limit raises LoopLimitExceeded."""
    qasm_str = """
    OPENQASM 3.0;
    qubit q;
    int i = 0;
    while (i < 10) {
        i += 1;
    }
    """
    result = loads(qasm_str)
    # Set loop_limit to 5 to force exception
    with pytest.raises(LoopLimitExceeded):
        result.unroll(loop_limit=5)


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
    expected = [
        'h q;',
        'i += 1;',
        'h q;',
        'i += 1;'
    ]
    result = loads(qasm_str)
    result.unroll()
    # Check that the unrolled AST contains the expected sequence
    stmts = [str(s) for s in result.unrolled_ast if hasattr(s, '__str__')]
    for e in expected:
        assert any(e in s for s in stmts)


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
    stmts = [str(s) for s in result.unrolled_ast if hasattr(s, '__str__')]
    assert any('h q' in s for s in stmts)
    # No extra statements from the while loop
    assert len(stmts) == 1


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
    stmts = [str(s) for s in result.unrolled_ast if hasattr(s, '__str__')]
    assert any('h q' in s for s in stmts)


def test_mixed_for_while_loops():
    """Test a for loop inside a while loop and vice versa."""
    qasm_str = """
    OPENQASM 3.0;
    qubit[2] q;
    int i = 0;
    while (i < 2) {
        for int j in [0, 1] {
            h q[j];
        }
        i += 1;
    }
    """
    result = loads(qasm_str)
    result.unroll()
    stmts = [str(s) for s in result.unrolled_ast if hasattr(s, '__str__')]
    assert sum('h q' in s for s in stmts) == 4
