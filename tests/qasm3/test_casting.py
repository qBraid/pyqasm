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
Module containing unit tests for explicit casts between OpenQASM 3 classical types.

"""

import math

import pytest

from pyqasm.entrypoint import loads
from pyqasm.exceptions import ValidationError
from pyqasm.visitor import QasmVisitor, ScopeManager


def global_scope(qasm3_string: str) -> dict:
    """Validate ``qasm3_string`` and return its global symbol table."""
    module = loads(qasm3_string)
    module.validate()
    scope_manager = ScopeManager()
    module.accept(QasmVisitor(module, scope_manager, check_only=True))
    return scope_manager.get_global_scope()


@pytest.mark.parametrize(
    "bits,expected_int,expected_uint",
    [("00000101", 5, 5), ("11111111", -1, 255), ("10000000", -128, 128)],
)
def test_bit_register_to_int(bits, expected_int, expected_uint):
    """A ``bit[n]`` casts to ``int[n]``/``uint[n]`` by reinterpreting its bit pattern.

    Bit 0 of the register is the most significant bit, so "00000101" is 5. ``int[n]``
    reads the pattern as two's complement, while ``uint[n]`` reads it as unsigned.
    """
    scope = global_scope(f"""
        OPENQASM 3.0;
        bit[8] b = "{bits}";
        int[8] i = int[8](b);
        uint[8] u = uint[8](b);
        """)
    assert scope["i"].value == expected_int
    assert scope["u"].value == expected_uint


def test_bit_register_to_int_wider_target_is_unsigned():
    """A ``bit[n]`` widened past its own width has no sign bit to reinterpret."""
    scope = global_scope("""
        OPENQASM 3.0;
        bit[4] b = "1111";
        int[32] i = int[32](b);
        """)
    assert scope["i"].value == 15


@pytest.mark.parametrize(
    "declaration,expression,expected_bits",
    [
        # Worked examples from https://openqasm.com/language/types.html#angles
        ("angle[4]", "pi", "1000"),
        ("angle[6]", "pi / 2", "010000"),
        ("angle[8]", "7 * (pi / 8)", "01110000"),
        ("angle[4]", "7 * (pi / 8)", "0111"),
    ],
)
def test_angle_fixed_point_bit_patterns(declaration, expression, expected_bits):
    """An ``angle[n]`` stores ``round(value / (2*pi) * 2**n)`` as its bit pattern."""
    scope = global_scope(f"OPENQASM 3.0;\n{declaration} a = {expression};\n")
    assert scope["a"].angle_bit_string == expected_bits


def test_float_to_angle_cast():
    """``angle[n](f)`` quantizes a float to the target width — issue #399 example."""
    scope = global_scope("""
        OPENQASM 3.0;
        float[64] f = 1.5;
        angle[8] a = angle[8](f);
        """)
    assert scope["a"].angle_bit_string == "00111101"  # round(256 * 1.5 / (2*pi)) == 61


def test_sizeless_angle_cast_takes_width_from_context():
    """``angle(f)`` with no designator quantizes at the declared width, not a default."""
    scope = global_scope("""
        OPENQASM 3.0;
        float[64] f = 1.0;
        angle[20] a = angle(f);
        """)
    assert scope["a"].angle_bit_string == format(round(2**20 / (2 * math.pi)), "020b")
    assert scope["a"].value == pytest.approx(1.0)


def test_angle_narrowing_truncates():
    """Narrowing an angle drops the low-order bits rather than rounding them.

    ``angle[4]`` holding "0111" narrows to ``angle[2]`` as "01". Rounding would give
    "10", so this pins the truncation behaviour the spec names as hardware-friendly.
    """
    scope = global_scope("""
        OPENQASM 3.0;
        angle[4] wide = 7 * (pi / 8);
        angle[2] narrow = angle[2](wide);
        """)
    assert scope["wide"].angle_bit_string == "0111"
    assert scope["narrow"].angle_bit_string == "01"
    assert scope["narrow"].value == pytest.approx(math.pi / 2)


def test_angle_widening_is_lossless():
    """Widening an angle left-shifts the fixed-point integer, adding zero bits."""
    scope = global_scope("""
        OPENQASM 3.0;
        angle[2] narrow = pi / 2;
        angle[4] wide = angle[4](narrow);
        """)
    assert scope["wide"].angle_bit_string == "0100"


def test_angle_narrowing_from_expression():
    """The spec's own narrowing example: ``angle[20]`` operands assigned to ``angle[10]``."""
    scope = global_scope("""
        OPENQASM 3.0;
        angle[20] a = pi / 2;
        angle[20] b = pi;
        angle[10] c;
        c = angle(a + b);
        """)
    assert scope["c"].angle_bit_string == "1100000000"  # 3/2 * pi


def test_angle_to_float_still_allowed():
    """``float(angle)`` is marked "No" by the cast table but used by the spec's own
    comparison example. pyqasm accepts it; issue #399 deliberately leaves it alone."""
    scope = global_scope("""
        OPENQASM 3.0;
        angle[8] a = pi;
        float[64] f = float[64](a);
        """)
    assert scope["f"].value == pytest.approx(math.pi)


@pytest.mark.parametrize(
    "qasm3_string,var_name,expected_value",
    [
        ("float[64] f = 2.5;\nint[8] i = int[8](f);", "i", 2),
        ("float[64] f = 2.5;\nuint u = uint(f);", "u", 2),
        ("int[8] i = 3;\nbool b = bool(i);", "b", True),
        ("int[8] i = 3;\nbit[8] b = bit[8](i);", "b", 3),
    ],
)
def test_previously_supported_casts_unchanged(qasm3_string, var_name, expected_value):
    """The casts that worked before issue #399 keep their values."""
    scope = global_scope(f"OPENQASM 3.0;\n{qasm3_string}\n")
    assert scope[var_name].value == expected_value


@pytest.mark.parametrize(
    "qasm3_string,expected_error",
    [
        (
            "int[8] i = 3;\nangle[8] a = angle[8](i);",
            "Cannot cast 'int' to 'angle'",
        ),
        (
            "angle[8] a = pi;\nbit[8] b = bit[8](a);",
            "Cannot cast 'angle' to 'bit'",
        ),
        (
            "float[64] f = 2.5;\nbit[2] b = bit[2](f);",
            "Cannot cast 'float' to 'bit'",
        ),
        (
            'bit[8] b = "00000101";\nangle[8] a = angle[8](b);',
            "Cannot cast 'bit' to 'angle'",
        ),
    ],
)
def test_unsupported_cast_names_both_types(qasm3_string, expected_error):
    """An unsupported cast reports the source and target type, not a generic message."""
    with pytest.raises(ValidationError) as excinfo:
        loads(f"OPENQASM 3.0;\n{qasm3_string}\n").validate()

    chained = excinfo.value.__cause__ or excinfo.value.__context__
    assert chained is not None, "Expected a chained ValidationError"
    assert expected_error in str(chained)
