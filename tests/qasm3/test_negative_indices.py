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

"""Tests for OpenQASM 3 negative-index normalization (issue #391).

Negative indices count from the end (``-1`` is the last element). These tests
cover arrays (single- and multi-dimensional, read and write), ``bit[n]``,
``qubit[n]``, ``let`` aliases, and ranges — including the stepped form — plus
the post-unroll transformation passes that must never see negative indices.
"""

import pytest

from pyqasm.entrypoint import dumps, loads
from pyqasm.exceptions import ValidationError


def test_negative_index_read_from_array():
    """``array[..., 5] a; ... a[-1]`` reads the last element."""
    module = loads("""
        OPENQASM 3.0;
        array[int[32], 5] myArray = {0, 1, 2, 3, 4};
        int[32] x = myArray[-1];
        int[32] y = myArray[-5];
        """)
    module.validate()


def test_negative_index_multi_dim_read():
    """Negative indices normalize per-dimension in a multi-dim array."""
    module = loads("""
        OPENQASM 3.0;
        array[int[32], 2, 3] multiDim = {{0, 1, 2}, {10, 11, 12}};
        int[32] x = multiDim[-1, -1];
        """)
    module.validate()


def test_negative_index_array_write():
    """``a[-1] = ...`` writes to the last element."""
    module = loads("""
        OPENQASM 3.0;
        array[int[32], 5] a = {0, 1, 2, 3, 4};
        a[-1] = 10;
        """)
    module.validate()


def test_negative_index_qubit_read():
    """``h q[-1];`` targets the last qubit; unrolled AST shows the concrete index."""
    module = loads("""
        OPENQASM 3.0;
        include "stdgates.inc";
        qubit[4] q;
        h q[-1];
        """)
    module.unroll()
    text = dumps(module)
    assert "h q[3];" in text


def test_negative_bit_register_index_read():
    """``bit c = b[-1]`` reads the last bit of the register."""
    module = loads("""
        OPENQASM 3.0;
        bit[4] b = "1010";
        bit c = b[-1];
        """)
    module.validate()


def test_negative_bit_register_index_write():
    """``b[-1] = 1`` writes the last bit; the emitted statement preserves the source."""
    module = loads("""
        OPENQASM 3.0;
        bit[4] b = "0000";
        b[-1] = 1;
        """)
    module.validate()
    assert "b[-1] = 1" in dumps(module)


def test_negative_range_qubit_gate_expands_to_concrete_indices():
    """``h q[-3:-1];`` unrolls to concrete non-negative indices; the end is
    exclusive (Python-slice convention on qubit ranges), so ``[-3:-1]`` on a
    5-qubit register selects positions 2 and 3."""
    module = loads("""
        OPENQASM 3.0;
        include "stdgates.inc";
        qubit[5] q;
        h q[-3:-1];
        """)
    module.unroll()
    text = dumps(module)
    assert "h q[2];" in text
    assert "h q[3];" in text
    # end-exclusive: q[4] is NOT touched.
    assert "h q[4];" not in text


def test_negative_range_alias_indexable():
    """A ``let`` alias built from a negative range resolves to the intended qubits.

    On an 8-qubit register, ``two[-4:-1]`` = ``two[4:7]`` (end-exclusive) covers
    three qubits, so ``last_three[0]`` maps to ``two[4]``.
    """
    module = loads("""
        OPENQASM 3.0;
        include "stdgates.inc";
        qubit[8] two;
        let last_three = two[-4:-1];
        h last_three[0];
        """)
    module.unroll()
    assert "h two[4];" in dumps(module)


def test_negative_index_out_of_bounds_reports_source_index(caplog):
    """A qubit index still out of range after normalization reports the source index."""
    with pytest.raises(ValidationError, match=r"Index -5"):
        with caplog.at_level("ERROR"):
            loads("""
                OPENQASM 3.0;
                include "stdgates.inc";
                qubit[4] q;
                h q[-5];
                """).validate()
    assert "-5" in caplog.text


def test_negative_index_out_of_bounds_for_array_reports_source_index(caplog):
    """For arrays, the message names the negative index as written in the source."""
    with pytest.raises(ValidationError):
        with caplog.at_level("ERROR"):
            loads("""
                OPENQASM 3.0;
                array[int[32], 5] a = {0, 1, 2, 3, 4};
                int[32] x = a[-6];
                """).validate()
    # The chained cause carries "Index -6 out of bounds ..."; the log captures it
    # before it is re-raised as "Invalid initialization value for variable 'x'".
    assert "-6" in caplog.text


def test_remove_idle_qubits_after_negative_source_index():
    """``remove_idle_qubits`` sees only non-negative indices after unroll."""
    module = loads("""
        OPENQASM 3.0;
        include "stdgates.inc";
        qubit[5] q;
        h q[-1];
        x q[-2];
        """)
    module.remove_idle_qubits()
    text = dumps(module)
    # Only 2 qubits remain — the ones actually operated on.
    assert "qubit[2] q;" in text
    assert "h q[1];" in text
    assert "x q[0];" in text


def test_reverse_qubit_order_after_negative_source_index():
    """``reverse_qubit_order`` correctly handles negative source indices."""
    module = loads("""
        OPENQASM 3.0;
        include "stdgates.inc";
        qubit[5] q;
        h q[-1];
        x q[-2];
        """)
    module.reverse_qubit_order()
    text = dumps(module)
    # After reversal, q[4] -> q[0] and q[3] -> q[1].
    assert "h q[0];" in text
    assert "x q[1];" in text


def test_descending_negative_range_positive_step_raises():
    """``a[-1:-5]`` with the implicit step of ``+1`` normalizes to a descending
    range on a positive step — pyqasm rejects that as a step-direction mismatch,
    which is the pre-existing behavior for any descending unstepped range. The
    caller sees ``ValidationError`` with the step-direction cause chained."""
    with pytest.raises(ValidationError) as excinfo:
        loads("""
            OPENQASM 3.0;
            array[int[32], 5] a = {0, 1, 2, 3, 4};
            array[int[32], 5] sub = a[-1:-5];
            """).validate()
    cause = excinfo.value.__cause__ or excinfo.value.__context__
    assert cause is not None
    assert "step" in str(cause)


def test_negative_index_in_branch_condition_normalizes():
    """``if (c[-1])`` normalizes the negative index against the classical register size."""
    module = loads("""
        OPENQASM 3.0;
        include "stdgates.inc";
        qubit[4] q;
        bit[4] c;
        c = measure q;
        if (c[-1]) {
            h q[0];
        }
        """)
    module.unroll()
    # After normalization the condition targets c[3] (last classical bit).
    assert "c[3]" in dumps(module)


def test_negative_qubit_range_end_only():
    """A range with just a negative end (``[0:-1]``) is exclusive, matching the
    end-exclusive convention of qubit ranges in pyqasm."""
    module = loads("""
        OPENQASM 3.0;
        include "stdgates.inc";
        qubit[5] q;
        h q[0:-1];
        """)
    module.unroll()
    text = dumps(module)
    # ``end = -1`` normalizes to 4 with end-exclusive iteration:
    # positions 0, 1, 2, 3 are hit (not 4).
    for i in range(4):
        assert f"h q[{i}];" in text
    assert "h q[4];" not in text
