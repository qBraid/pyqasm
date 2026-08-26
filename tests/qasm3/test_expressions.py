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
Module containing unit tests for expressions.

"""

import pytest
from openqasm3.ast import QuantumGate

from pyqasm.analyzer import bits_to_int, int_to_bits
from pyqasm.elements import BitValue
from pyqasm.entrypoint import dumps, loads
from pyqasm.exceptions import ValidationError
from pyqasm.maps.expressions import qasm3_expression_op_map
from tests.utils import check_measure_op, check_single_qubit_gate_op, check_single_qubit_rotation_op


def test_correct_expressions():
    qasm_str = """OPENQASM 3;
    qubit q;

    // supported
    rx(1.57) q;
    rz(3-2*3) q;
    rz(3-2*3*(8/2)) q;
    rx(-1.57) q;
    rx(4%2) q;

    int a = 5;
    float b = 10*a*pi;
    array[int[32], 2] c;
    c[0] = 1;
    c[1] = c[0] + 2;
    """

    result = loads(qasm_str)
    result.unroll()
    assert result.num_qubits == 1
    assert result.num_clbits == 0
    rx_expression_values = [1.57, -1.57, 0]
    rz_expression_values = [-3, -21.0]
    check_single_qubit_rotation_op(result.unrolled_ast, 3, [0] * 3, rx_expression_values, "rx")
    check_single_qubit_rotation_op(result.unrolled_ast, 2, [0] * 2, rz_expression_values, "rz")


def test_bit_in_expression():
    qasm_str = """
    OPENQASM 3.0;
    include "stdgates.inc";

    bit[1] c3;
    qubit[1] q3;
    int dummy_int;
    h q3[0];
    c3[0] = measure q3[0];
    dummy_int = c3[0];
    """

    result = loads(qasm_str)
    result.unroll()

    assert result.num_qubits == 1
    assert result.num_clbits == 1
    check_single_qubit_gate_op(result.unrolled_ast, 1, [0], "h")
    meas_pairs = [(("q3", 0), ("c3", 0))]
    check_measure_op(result.unrolled_ast, 1, meas_pairs)


def test_incorrect_expressions(caplog):
    with pytest.raises(ValidationError, match=r"Invalid parameter .*"):
        with caplog.at_level("ERROR"):
            loads("OPENQASM 3; qubit q; rx(~1.3) q;").validate()
    assert "Error at line 1" in caplog.text
    assert "~1.3" in caplog.text

    caplog.clear()

    with pytest.raises(ValidationError, match=r"Invalid parameter .*"):
        with caplog.at_level("ERROR"):
            loads("OPENQASM 3; qubit q; rx(~1.3+5im) q;").validate()
    assert "Error at line 1" in caplog.text
    assert "~1.3" in caplog.text

    caplog.clear()

    with pytest.raises(ValidationError, match="Invalid parameter 'x' .*"):
        with caplog.at_level("ERROR"):
            loads("OPENQASM 3; qubit q; rx(x) q;").validate()
    assert "Error at line 1" in caplog.text
    assert "x" in caplog.text

    caplog.clear()

    with pytest.raises(ValidationError, match="Invalid parameter 'x' .*"):
        with caplog.at_level("ERROR"):
            loads("OPENQASM 3; qubit q; int x; rx(x) q;").validate()
    assert "Error at line 1" in caplog.text
    assert "x" in caplog.text


# ---------------------------------------------------------------------------
# Issue #385 — bitwise, shift, and index operations on ``bit[n]``
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "op,expected_bits",
    [
        ("|", "1111"),  # 1010 | 0101
        ("&", "0000"),  # 1010 & 0101
        ("^", "1111"),  # 1010 ^ 0101
    ],
)
def test_bit_register_binary_bitwise_ops(op, expected_bits):
    """Binary bitwise operators on two ``bit[n]`` operands produce a masked result."""
    qasm = f"""
    OPENQASM 3.0;
    bit[4] a = "1010";
    bit[4] b = "0101";
    bit[4] c = a {op} b;
    """
    loads(qasm).validate()

    # The declaration above only proves the operator no longer raises. Drive the
    # same dispatch directly to pin the value it produces, and its width.
    lhs = BitValue(bits_to_int("1010", 4), 4)
    rhs = BitValue(bits_to_int("0101", 4), 4)
    result = qasm3_expression_op_map(op, lhs, rhs)
    assert int_to_bits(int(result), result.width) == expected_bits
    assert result.width == 4


def test_bit_register_unary_not_masks_to_width():
    """``~a`` on a ``bit[n]`` value re-masks so the result stays within ``n`` bits."""
    qasm = """
    OPENQASM 3.0;
    bit[4] a = "1010";
    bit[4] c = ~a;
    """
    module = loads(qasm)
    module.validate()
    assert "c = ~a" in dumps(module)


@pytest.mark.parametrize("shift_op", ["<<", ">>"])
def test_bit_register_shift_ops(shift_op):
    """``<<`` and ``>>`` on a ``bit[n]`` register with an integer shift-count work."""
    qasm = f"""
    OPENQASM 3.0;
    bit[4] a = "1010";
    bit[4] c = a {shift_op} 1;
    """
    module = loads(qasm)
    module.validate()
    assert f"c = a {shift_op} 1" in dumps(module)


def test_bit_register_binary_width_mismatch_raises(caplog):
    """Two ``bit[n]`` operands of different widths in a bitwise op raise ValidationError
    with the source span attached (an unspanned error would ship without a line number)."""
    qasm = """
    OPENQASM 3.0;
    bit[4] a = "1010";
    bit[3] b = "010";
    bit[4] c;
    c = a | b;
    """
    with pytest.raises(ValidationError, match="Width mismatch for bitwise"):
        with caplog.at_level("ERROR"):
            loads(qasm).validate()
    # The re-raise attaches the span; the logged message names the source line.
    assert "Error at line" in caplog.text


def test_bit_register_single_element_index():
    """``b[i]`` returns a single-bit value that can initialize a ``bit`` variable."""
    qasm = """
    OPENQASM 3.0;
    bit[4] b = "1010";
    bit c = b[0];
    """
    module = loads(qasm)
    module.validate()
    text = dumps(module)
    assert "bit[1] c = b[0]" in text


def test_bit_register_range_and_stepped_index():
    """``b[a:c]`` and ``b[a:step:c]`` both yield a bit register of the sliced width."""
    module = loads("""
        OPENQASM 3.0;
        bit[4] b = "1010";
        bit[3] c = b[0:2];
        bit[2] d = b[0:2:3];
        """)
    module.validate()
    text = dumps(module)
    assert "bit[3] c = b[0:2]" in text
    assert "bit[2] d = b[0:2:3]" in text


def test_bit_register_descending_slice_read():
    """A negative step reverses the slice and still keeps its final position.

    The stop bound has to move one past ``end`` in the direction of travel; a fixed
    ``end + 1`` drops every position below ``start`` and yields ``0``.
    """
    module = loads("""
        OPENQASM 3.0;
        qubit q;
        bit[4] b = "1100";
        bit[4] r = b[3:-1:0];
        int[8] v = r;
        rx(v) q;
        """)
    module.unroll()
    # Bit 0 is the most-significant bit, so "1100" read back-to-front is "0011" == 3.
    check_single_qubit_rotation_op(module.unrolled_ast, 1, [0], [3], "rx")


def test_bit_register_descending_slice_write():
    """A descending target range writes every selected position, not just the first."""
    module = loads("""
        OPENQASM 3.0;
        qubit q;
        bit[4] b = "0000";
        bit[2] t = "11";
        b[3:-1:2] = t;
        int[8] v = b;
        rx(v) q;
        """)
    module.unroll()
    # Positions 3 and 2 both become 1, giving "0011" == 3.
    check_single_qubit_rotation_op(module.unrolled_ast, 1, [0], [3], "rx")


def test_bit_register_bitstring_literal_roundtrips():
    """A ``bit[n] = \"1010\"`` declaration serializes back to the same literal form."""
    src = 'OPENQASM 3.0;\nbit[4] a = "1010";\n'
    out = dumps(loads(src))
    assert 'bit[4] a = "1010";' in out


def test_bit_register_op_result_stays_bit_type():
    """The result of ``a | b`` retains bit type and can seed a further ``bit[n]``."""
    module = loads("""
        OPENQASM 3.0;
        bit[4] a = "1010";
        bit[4] b = "0101";
        bit[4] c = a | b;
        bit[4] d = c & a;
        """)
    module.validate()
    text = dumps(module)
    assert "c = a | b" in text
    assert "d = c & a" in text


def test_bit_register_descending_slice():
    """``b[3:-1:0]`` selects every position down to 0, not just down to 1.

    Regression guard: an inclusive range must extend its stop bound in the
    direction of travel, so a negative step keeps the final position.
    """
    module = loads("""
        OPENQASM 3.0;
        qubit q;
        bit[4] b = "1100";
        bit[4] r = b[3:-1:0];
        int[8] v = r;
        rx(v) q;
        """)
    module.unroll()
    # "1100" read back-to-front is "0011" == 3.
    assert _rotation_args(module) == [3]


# ---------------------------------------------------------------------------
# Issue #395 — classical value bit slicing on ``int`` / ``uint``
# ---------------------------------------------------------------------------


def _rotation_args(module):
    """Return the evaluated ``rx`` arguments of an unrolled module, in order.

    Bit-slice results are not otherwise observable from the public API, so the
    tests below funnel each value into an ``rx`` angle and read it back.
    """
    return [
        stmt.arguments[0].value
        for stmt in module.unrolled_ast.statements
        if isinstance(stmt, QuantumGate) and stmt.name.name == "rx"
    ]


def test_int_bit_slice_spec_example():
    """The spec's ``int[32] myInt = 15`` example evaluates to its documented values.

    Reference: https://openqasm.com/versions/3.1/language/types.html#classical-value-bit-slicing
    """
    module = loads("""
        OPENQASM 3.0;
        qubit q;
        int[32] myInt = 15;
        bit[1] lastBit = myInt[0];
        bit[1] signBit = myInt[31];
        bit[1] alsoSignBit = myInt[-1];
        bit[16] evenBits = myInt[0:2:31];
        bit[16] upperBits = myInt[-16:-1];
        int[8] a = lastBit;
        int[8] b = signBit;
        int[8] c = alsoSignBit;
        int[32] d = evenBits;
        int[32] e = upperBits;
        myInt[4:7] = "1010";
        rx(a) q;
        rx(b) q;
        rx(c) q;
        rx(d) q;
        rx(e) q;
        rx(myInt) q;
        """)
    module.unroll()
    assert _rotation_args(module) == [1, 0, 0, 3, 0, 0xAF]


@pytest.mark.parametrize("int_type", ["int", "uint"])
def test_int_bit_slice_single_bit_read(int_type):
    """``i[k]`` yields the bit at position ``k``, counted from the LSB."""
    module = loads(f"""
        OPENQASM 3.0;
        qubit q;
        {int_type}[8] i = 15;
        int[8] low = i[0];
        int[8] high = i[4];
        rx(low) q;
        rx(high) q;
        """)
    module.unroll()
    assert _rotation_args(module) == [1, 0]


@pytest.mark.parametrize("int_type", ["int", "uint"])
def test_int_bit_slice_assignment(int_type):
    """``i[a:b] = <bit[k]>`` writes the bit vector into the integer, LSB first."""
    module = loads(f"""
        OPENQASM 3.0;
        qubit q;
        {int_type}[32] i = 15;
        i[4:7] = "1010";
        rx(i) q;
        """)
    module.unroll()
    # 0b1010 written LSB-first into positions 4..7 sets bits 5 and 7: 15 + 32 + 128.
    assert _rotation_args(module) == [0xAF]


def test_int_bit_slice_assignment_wraps_to_signed():
    """Writing the top bit of a signed ``int[n]`` re-reads as a negative value."""
    module = loads("""
        OPENQASM 3.0;
        qubit q;
        int[4] x = 0;
        uint[4] y = 0;
        x[3] = 1;
        y[3] = 1;
        rx(x) q;
        rx(y) q;
        """)
    module.unroll()
    assert _rotation_args(module) == [-8, 8]


def test_int_bit_slice_array_element():
    """``arr[i][k]`` and ``arr[i][a:b]`` address the bits of one array element."""
    module = loads("""
        OPENQASM 3.0;
        qubit q;
        array[int[32], 5] intArr = {0, 1, 2, 3, 4};
        intArr[0][0] = 1;
        bit[5] b = intArr[4][0:4];
        int[8] v = b;
        int[8] w = intArr[0];
        rx(v) q;
        rx(w) q;
        """)
    module.unroll()
    assert _rotation_args(module) == [4, 1]


def test_int_bit_slice_multi_dimensional_array_element():
    """A trailing bit subscript is separated from the element subscripts, not flattened.

    Regression guard for ``Invalid index for variable``: ``a[0][0][3]`` carries one
    subscript more than the array has dimensions, and the extra one selects bits.
    """
    module = loads("""
        OPENQASM 3.0;
        qubit q;
        array[int[8], 2, 3] a = {{1, 2, 3}, {4, 5, 6}};
        a[0][0][3] = 1;
        bit[3] s = a[1][1][0:2];
        int[8] w = a[0][0];
        int[8] u = s;
        rx(w) q;
        rx(u) q;
        """)
    module.unroll()
    # a[0][0] == 1, setting bit 3 adds 8; a[1][1] == 5, whose low three bits are 0b101.
    assert _rotation_args(module) == [9, 5]


def test_int_bit_slice_reversed_range_requires_explicit_step(caplog):
    """A descending range needs an explicit negative step.

    The spec's ``myInt[-1:-16]`` is an empty index set under the normative range
    definition (``a:b`` implies step 1, and no ``a + m`` reaches a smaller ``b``),
    yet its example assigns it to a ``bit[16]``. pyqasm follows the normative rule
    and rejects the ambiguous form; ``myInt[-1:-1:-16]`` gives the reversed slice.
    """
    with pytest.raises(ValidationError, match="Invalid initialization value"):
        with caplog.at_level("ERROR"):
            loads("""
                OPENQASM 3.0;
                int[32] myInt = 15;
                bit[16] upperReversed = myInt[-1:-16];
                """).validate()
    assert "Error at line" in caplog.text

    module = loads("""
        OPENQASM 3.0;
        qubit q;
        int[8] myInt = 15;
        bit[8] reversed_bits = myInt[-1:-1:-8];
        int[16] v = reversed_bits;
        rx(v) q;
        """)
    module.unroll()
    # 0b00001111 read from bit 7 down to bit 0 is 0b11110000 == 240.
    assert _rotation_args(module) == [240]


def test_int_bit_slice_index_out_of_range_names_width(caplog):
    """An index outside ``[0, n)`` after normalisation reports the declared width."""
    with pytest.raises(ValidationError, match=r"Index 32 out of range for 'int\[32\]' variable"):
        with caplog.at_level("ERROR"):
            loads("OPENQASM 3.0; int[32] m = 15; m[32] = 1;").validate()
    assert "Error at line" in caplog.text

    with pytest.raises(ValidationError) as excinfo:
        loads("OPENQASM 3.0; uint[8] m = 15; bit b = m[-9];").validate()
    assert "Index -9 out of range for 'uint[8]' variable 'm'" in str(excinfo.value.__cause__)


def test_int_bit_slice_assignment_width_mismatch():
    """The right-hand side of a slice assignment must match the slice width."""
    with pytest.raises(ValidationError, match="Cannot assign a 2-bit value to a 4-bit slice"):
        loads('OPENQASM 3.0; int[32] m = 15; m[0:3] = "10";').validate()

    with pytest.raises(ValidationError, match="Value 4 out of range for a 1-bit slice"):
        loads("OPENQASM 3.0; int[32] m = 15; m[0] = 4;").validate()
