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
from pyqasm.exceptions import LoopControlSignal, LoopLimitExceededError, ValidationError
from tests.utils import check_single_qubit_gate_op, check_two_qubit_gate_op


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
    qubit[4] q;
    int i = 0;
    while (i < 3) {
        h q[i];
        cx q[i], q[i+1];
        i += 1;
    }

    """
    result = loads(qasm_str)
    result.unroll()
    check_single_qubit_gate_op(result.unrolled_ast, 3, [0, 1, 2], "h")
    check_two_qubit_gate_op(result.unrolled_ast, 3, [(0, 1), (1, 2), (2, 3)], "cx")


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
    while (i < 1e5) {
        i += 1;
    }
    """
    result = loads(qasm_str)
    with pytest.raises(LoopLimitExceededError):
        result.unroll(max_loop_iters=1e3)


def test_while_loop_allows_exactly_max_iterations():
    """A loop finishing on its last permitted iteration must not raise.

    The limit is checked once the condition is known true, so `max_loop_iters`
    iterations may complete. Checking after the counter bumped instead allowed
    only `max_loop_iters - 1`.
    """
    qasm_str = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[1] q;
    int[8] i = 0;
    while (i < 3) {
        h q[0];
        i += 1;
    }
    """
    result = loads(qasm_str)
    result.unroll(max_loop_iters=3)
    check_single_qubit_gate_op(result.unrolled_ast, 3, [0, 0, 0], "h")

    result = loads(qasm_str)
    with pytest.raises(LoopLimitExceededError):
        result.unroll(max_loop_iters=2)


def test_while_loop_limit_counts_continue_iterations():
    """A body that always hits `continue` must still trip the loop limit.

    The counter used to be incremented only on the path that ran the body to
    completion, so `while (cond) { continue; }` never reached the limit and
    unrolled forever.
    """
    qasm_str = """
    OPENQASM 3.0;
    qubit q;
    int i = 0;
    while (i < 3) {
        continue;
    }
    """
    result = loads(qasm_str)
    with pytest.raises(LoopLimitExceededError):
        result.unroll(max_loop_iters=1e2)


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


# ---------------------------------------------------------------------------
# Regression tests for GitHub issue #386 - while-loop break dropping the
# interrupted iteration's already-emitted statements.
# ---------------------------------------------------------------------------


def test_while_loop_break_preserves_prior_iteration_body():
    """`break` in a while iter must keep gates emitted before the break."""
    qasm_str = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[1] q;
    int[8] i = 0;
    while (i < 3) {
        h q[0];
        i += 1;
        break;
    }
    """
    result = loads(qasm_str)
    result.unroll()
    # Exactly one h q[0] survives - depth reflects it.
    assert result.depth() == 1
    check_single_qubit_gate_op(result.unrolled_ast, 1, [0], "h")


def test_while_loop_continue_preserves_prior_iteration_body():
    """`continue` mid-iteration must keep gates emitted before the continue."""
    qasm_str = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[1] q;
    int[8] i = 0;
    while (i < 3) {
        h q[0];
        i += 1;
        if (i == 2) {
            continue;
        }
        x q[0];
    }
    """
    result = loads(qasm_str)
    result.unroll()
    # h emitted every iter (i=0,1,2) -> 3; x emitted on iters where i!=2 after
    # increment (i=1 and i=3) -> 2.
    check_single_qubit_gate_op(result.unrolled_ast, 3, [0, 0, 0], "h")
    check_single_qubit_gate_op(result.unrolled_ast, 2, [0, 0], "x")


def test_while_loop_break_does_not_leak_internal_signal():
    """`break` in a `while` must not leak internal control-flow exceptions."""
    qasm_str = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[1] q;
    int[8] i = 0;
    while (i < 3) {
        h q[0];
        i += 1;
        break;
    }
    """
    result = loads(qasm_str)
    for op in (result.validate, result.unroll):
        try:
            op()
        except LoopControlSignal:
            pytest.fail(f"{op.__name__}() leaked a LoopControlSignal")
