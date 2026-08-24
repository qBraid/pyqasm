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

import math
import re

import pytest

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


# ---------------------------------------------------------------------------
# Issue #390 — built-in constant expression functions
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "call,expected",
    [
        ("exp(1.0)", math.e),
        ("log(2.0)", math.log(2.0)),
        ("ceiling(1.2)", 2.0),
        ("floor(1.8)", 1.0),
        ("mod(7, 2)", 1),
        ("popcount(37)", 3),
        ("sqrt(4.0)", 2.0),
    ],
)
def test_builtin_function_in_const_and_gate_argument(call, expected):
    """Each built-in evaluates identically in a ``const`` initializer and inline
    as a gate argument."""
    module = loads(f"""
        OPENQASM 3.0;
        include "stdgates.inc";
        qubit[1] q;
        const float[64] c = {call};
        rx(c) q[0];
        rx({call}) q[0];
        """)
    module.unroll()
    check_single_qubit_rotation_op(module.unrolled_ast, 2, [0, 0], [expected, expected], "rx")


@pytest.mark.parametrize("amount", [0, 1, 3, 8, 11, -3])
def test_bit_rotation_preserves_width_and_direction(amount):
    """``rotl(a, n) == rotr(a, -n)``, both in and out of a ``const`` initializer, and
    both keep the operand's declared width."""
    module = loads(f"""
        OPENQASM 3.0;
        include "stdgates.inc";
        qubit[1] q;
        bit[8] left = rotl("00101010", {amount});
        bit[8] right = rotr("00101010", {-amount});
        const bit[8] const_left = rotl("00101010", {amount});
        const bit[8] const_right = rotr("00101010", {-amount});
        rx(const_left) q[0];
        rx(const_right) q[0];
        """)
    module.unroll()
    source, shift = "00101010", amount % 8
    expected = source[shift:] + source[:shift]
    left, right = re.findall(r'= "(\d+)";', dumps(module))
    assert left == right == expected
    assert len(left) == 8
    rotated = int(expected, 2)
    check_single_qubit_rotation_op(module.unrolled_ast, 2, [0, 0], [rotated, rotated], "rx")


def test_rotation_on_uint_uses_declared_width():
    """A ``uint[n]`` operand carries no width at evaluation time, so the width is
    recovered from its declaration."""
    module = loads("""
        OPENQASM 3.0;
        include "stdgates.inc";
        qubit[1] q;
        const uint[8] u = 37;
        rx(rotl(u, 3)) q[0];
        rx(rotr(u, -3)) q[0];
        """)
    module.unroll()
    check_single_qubit_rotation_op(module.unrolled_ast, 2, [0, 0], [41, 41], "rx")


@pytest.mark.parametrize(
    "call,message",
    [
        ("sqrt(2.0, 3.0)", r"Function 'sqrt' expects 1 argument\(s\), but 2 were given"),
        ("mod(7)", r"Function 'mod' expects 2 argument\(s\), but 1 were given"),
        ('rotl("1010")', r"Function 'rotl' expects 2 argument\(s\), but 1 were given"),
        ('ceiling("01")', r"Invalid argument for function 'ceiling'"),
        ('rotl("1010", 1.5)', r"Invalid argument for function 'rotl'"),
        ("popcount(1.5)", r"Invalid argument for function 'popcount'"),
        ("rotl(37, 3)", r"Function 'rotl' expects a 'bit\[n\]' or 'uint\[n\]' operand"),
        ("nosuchfn(2.0)", r"Undefined subroutine 'nosuchfn' was called"),
    ],
)
def test_builtin_function_errors_name_the_function(call, message):
    """An unknown name, a wrong arity, or a wrong argument type names the offending
    function instead of only reporting a generic initialization failure."""
    with pytest.raises(ValidationError, match=message):
        loads(f"OPENQASM 3.0;\nconst float[64] c = {call};").validate()


def test_pow_function_is_parse_blocked_and_power_operator_works():
    """``pow`` is ambiguous with the gate modifier of the same name, so ``openqasm3``
    rejects the call before pyqasm sees it. Upstream removed ``pow`` from the spec
    (openqasm/openqasm#635); ``**`` is the supported spelling."""
    with pytest.raises(ValidationError, match="Failed to parse OpenQASM string"):
        loads("OPENQASM 3.0;\nconst int c = pow(2, 3);")
    loads("OPENQASM 3.0;\nconst int c = 2 ** 3;").validate()
