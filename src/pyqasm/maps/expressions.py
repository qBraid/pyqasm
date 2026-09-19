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
Module mapping supported QASM expressions to lower level gate operations.

"""

from typing import Callable

import numpy as np
from openqasm3.ast import (
    AngleType,
    BitType,
    BoolType,
    ComplexType,
    DurationType,
    FloatType,
    IntType,
    StretchType,
    UintType,
)

from pyqasm.elements import AngleValue, BitValue
from pyqasm.exceptions import ValidationError

# Define the type for the operator functions
OperatorFunction = (
    Callable[[int | float | bool], int | float | bool]
    | Callable[[int | float | bool, int | float | bool], int | float | bool]
)


OPERATOR_MAP: dict[str, OperatorFunction] = {
    "+": lambda x, y: x + y,
    "-": lambda x, y: x - y,
    "*": lambda x, y: x * y,
    "/": lambda x, y: x / y,
    "%": lambda x, y: x % y,
    "==": lambda x, y: x == y,
    "**": lambda x, y: x**y,
    "!=": lambda x, y: x != y,
    "<": lambda x, y: x < y,
    ">": lambda x, y: x > y,
    "<=": lambda x, y: x <= y,
    ">=": lambda x, y: x >= y,
    "&&": lambda x, y: x and y,
    "||": lambda x, y: x or y,
    "^": lambda x, y: x ^ y,
    "&": lambda x, y: x & y,
    "|": lambda x, y: x | y,
    "<<": lambda x, y: x << y,
    ">>": lambda x, y: x >> y,
    "~": lambda x: ~x,
    "!": lambda x: not x,
    "UMINUS": lambda x: -x,
}


# Binary bitwise operators for which both operands must be the same width when
# they are ``BitValue``s. Shifts (``<<``, ``>>``) take an int shift-count and are
# not width-checked against the right-hand side.
_BITWISE_EQUAL_WIDTH_OPS = frozenset({"|", "&", "^"})
_BITWISE_SHIFT_OPS = frozenset({"<<", ">>"})


def qasm3_expression_op_map(op_name: str, *args) -> float | int | bool:
    """
    Return the result of applying the given operator to the given operands.

    Args:
        op_name (str): The operator name.
        *args: The operands of type int | float | bool
                1. For unary operators, a single operand (e.g., ~3)
                2. For binary operators, two operands (e.g., 3 + 2)

    Returns:
        (float | int | bool): The result of applying the operator to the operands.

    Raises:
        ValidationError: For unknown operators, or when two ``BitValue`` operands of
            a width-sensitive bitwise op have different widths.
    """
    try:
        operator = OPERATOR_MAP[op_name]
    except KeyError as exc:
        raise ValidationError(f"Unsupported / undeclared QASM operator: {op_name}") from exc

    if len(args) == 2:
        lhs, rhs = args
        lhs_is_bit = isinstance(lhs, BitValue)
        rhs_is_bit = isinstance(rhs, BitValue)
        if lhs_is_bit or rhs_is_bit:
            width = lhs.width if lhs_is_bit else rhs.width  # type: ignore[union-attr]
            if op_name in _BITWISE_EQUAL_WIDTH_OPS:
                if lhs_is_bit and rhs_is_bit and lhs.width != rhs.width:  # type: ignore[union-attr]
                    raise ValidationError(
                        f"Width mismatch for bitwise '{op_name}': "
                        f"lhs has width {lhs.width} but rhs has width "  # type: ignore[union-attr]
                        f"{rhs.width}"  # type: ignore[union-attr]
                    )
                return BitValue(int(operator(int(lhs), int(rhs))), width)  # type: ignore[call-arg]
            if op_name in _BITWISE_SHIFT_OPS and lhs_is_bit:
                return BitValue(int(operator(int(lhs), int(rhs))), width)  # type: ignore[call-arg]
        return operator(*args)  # type: ignore[call-arg]

    if len(args) == 1:
        (operand,) = args
        if isinstance(operand, BitValue) and op_name == "~":
            # ``~`` on Python ints turns the operand negative; re-mask to width so
            # the result remains a valid ``bit[n]`` value.
            return BitValue(int(operator(int(operand))), operand.width)  # type: ignore[call-arg]
        return operator(*args)  # type: ignore[call-arg]

    return operator(*args)


def qasm_type_name(qasm_type: type) -> str:
    """Return the OpenQASM source spelling of an AST type class, e.g. ``uint``."""
    return qasm_type.__name__.removesuffix("Type").lower()


def cast_to_angle(value: float, width: int) -> AngleValue:
    """Cast ``value`` to an ``angle[width]``.

    An angle source is re-expressed at the new width — truncating when narrowing — so a
    cast between angle widths follows the fixed-point rules rather than re-rounding the
    real number.

    Args:
        value (float): The value to cast — a real number, a ``bool``, or an
            :class:`~pyqasm.elements.AngleValue`.
        width (int): Target precision, in bits.

    Returns:
        AngleValue: The angle, quantized to ``width`` bits.
    """
    if isinstance(value, bool):
        # OpenQASM has no bool -> angle cast, but pyqasm has long accepted one that
        # maps ``true`` to the half-turn; see ALLOWED_CASTS.
        value = CONSTANTS_MAP["pi"] if value else 0.0
    if isinstance(value, AngleValue):
        return value.resize(width)
    return AngleValue(float(value), width)


# pylint: disable=inconsistent-return-statements,too-many-return-statements,too-many-branches
def qasm_variable_type_cast(openqasm_type, var_name, base_size, rhs_value):
    """Cast the variable type to the type to match, if possible.

    Args:
        openqasm_type : The type of the variable.
        type_of_rhs (type): The type to match.

    Returns:
        The casted variable type.

    Raises:
        ValidationError: If the cast is not possible.
    """
    # ``BitValue`` and ``AngleValue`` are ``int`` / ``float`` subclasses; look them up
    # under their base type so a value read from a ``bit[n]`` or ``angle[n]`` register
    # flows into a cast without a bespoke tuple entry per site.
    type_of_rhs = type(rhs_value)
    if isinstance(rhs_value, (BitValue, AngleValue)):
        type_of_rhs = type_of_rhs.__base__

    if openqasm_type in (DurationType, StretchType):
        return rhs_value

    if type_of_rhs not in VARIABLE_TYPE_CAST_MAP[openqasm_type]:
        raise ValidationError(
            f"Cannot cast '{type_of_rhs.__name__}' to '{openqasm_type.__name__}'. "
            f"Invalid assignment of type '{type_of_rhs.__name__}' to variable '{var_name}' "
            f"of type '{openqasm_type.__name__}'"
        )

    if openqasm_type == BoolType:
        return bool(rhs_value)
    if openqasm_type == IntType:
        if isinstance(rhs_value, BitValue) and rhs_value.width == base_size:
            # ``int[n](b)`` reinterprets a ``bit[n]`` register as the integer's
            # two's-complement bit pattern, so a set sign bit reads as negative.
            sign_bit = int(rhs_value) >> (base_size - 1)
            return int(rhs_value) - (1 << base_size) if sign_bit else int(rhs_value)
        return int(rhs_value)
    if openqasm_type == UintType:
        return int(rhs_value) % (2**base_size)
    if openqasm_type == FloatType:
        return float(rhs_value)
    # ``bit`` / ``bit[n]`` values are normalized to a width-carrying ``BitValue``
    # so downstream bitwise operators can enforce the OpenQASM equal-width rule
    # and produce properly-masked results. A ``str`` bitstring ("1010") is parsed
    # into its integer form; the caller (``_visit_classical_declaration`` or
    # ``_visit_classical_assignment``) is responsible for validating the string
    # width against ``base_size`` before we get here.
    if openqasm_type == BitType:
        if isinstance(rhs_value, BitValue):
            return rhs_value
        if isinstance(rhs_value, str):
            return BitValue(int(rhs_value, 2) if rhs_value else 0, base_size)
        return BitValue(int(rhs_value), base_size)
    if openqasm_type == AngleType:
        return cast_to_angle(rhs_value, base_size)
    if openqasm_type == ComplexType:
        if isinstance(rhs_value, float):
            return complex(rhs_value)
        return rhs_value


# IEEE 754 Standard for floats
# https://openqasm.com/language/types.html#floating-point-numbers
LIMITS_MAP = {"float_32": 1.70141183 * (10**38), "float_64": 10**308}

CONSTANTS_MAP = {
    "π": 3.141592653589793,
    "pi": 3.141592653589793,
    "ℇ": 2.718281828459045,
    "euler": 2.718281828459045,
    "τ": 6.283185307179586,
    "tau": 6.283185307179586,
}

VARIABLE_TYPE_MAP = {
    BitType: bool,
    IntType: int,
    UintType: int,
    BoolType: bool,
    FloatType: float,
    ComplexType: complex,
    DurationType: float,
    StretchType: float,
    AngleType: float,
}

# Reference: https://openqasm.com/language/types.html#allowed-casts
VARIABLE_TYPE_CAST_MAP = {
    BoolType: (int, float, bool, np.int64, np.float64, np.bool_),
    IntType: (bool, int, float, np.int64, np.float64, np.bool_),
    BitType: (bool, int, np.int64, np.bool_, str, BitValue),
    UintType: (bool, int, float, np.int64, np.uint64, np.float64, np.bool_),
    FloatType: (bool, int, float, np.int64, np.float64, np.bool_),
    AngleType: (float, np.float64, bool, np.bool_),
    ComplexType: (complex, np.complex128, float, np.float64),
}

# The explicit-cast surface, as ``source type -> allowed target types``. Rows follow the
# spec's allowed-casts table (https://openqasm.com/language/types.html#allowed-casts),
# with these deliberate differences, each of which pyqasm has always had:
#   - bool -> angle, angle -> {int, uint, float} and bit -> float are marked "No" by the
#     spec but are accepted here. The spec is self-inconsistent on angle -> float: its
#     own angle comparison example uses it. Left alone pending an upstream ruling.
#   - duration -> * is marked "No" by the spec but is accepted here.
#   - bit -> angle and angle -> bit are marked "Yes" by the spec but are not implemented.
# A source type absent from this map (``stretch``, arrays) is not classified, so its
# casts fall through to the value-level check in ``qasm_variable_type_cast``.
ALLOWED_CASTS: dict[type, frozenset[type]] = {
    BoolType: frozenset({BoolType, IntType, UintType, FloatType, AngleType, BitType}),
    IntType: frozenset({BoolType, IntType, UintType, FloatType, BitType}),
    UintType: frozenset({BoolType, IntType, UintType, FloatType, BitType}),
    FloatType: frozenset({BoolType, IntType, UintType, FloatType, AngleType, ComplexType}),
    AngleType: frozenset({BoolType, IntType, UintType, FloatType, AngleType, ComplexType}),
    BitType: frozenset({BoolType, IntType, UintType, FloatType, BitType}),
    DurationType: frozenset({BoolType, IntType, UintType, FloatType, AngleType, ComplexType}),
    ComplexType: frozenset({ComplexType}),
}

ARRAY_TYPE_MAP = {
    BitType: np.bool_,
    IntType: np.int64,
    UintType: np.uint64,
    FloatType: np.float64,
    ComplexType: np.complex128,
    BoolType: np.bool_,
    AngleType: np.float64,
}

# Reference : https://openqasm.com/language/types.html#arrays
MAX_ARRAY_DIMENSIONS = 7

# Time units supported in OpenQASM3 (https://openqasm.com/language/delays.html#duration-and-stretch)
TIME_UNITS_MAP: dict[str, dict[str, float]] = {
    "ns": {"ns": 1, "s": 1e-9},
    "us": {"ns": 1000, "s": 1e-6},
    "µs": {"ns": 1000, "s": 1e-6},  # Unicode micro
    "ms": {"ns": 1_000_000, "s": 1e-3},
    "s": {"ns": 1_000_000_000, "s": 1},
}

# Function map for complex functions
FUNCTION_MAP = {
    "abs": np.abs,
    "real": lambda v: v.real if isinstance(v, complex) else v,
    "imag": lambda v: v.imag if isinstance(v, complex) else v,
    "sqrt": np.sqrt,
    "sin": np.sin,
    "cos": np.cos,
    "tan": np.tan,
    "arccos": np.arccos,
    "arcsin": np.arcsin,
    "arctan": np.arctan,
}
