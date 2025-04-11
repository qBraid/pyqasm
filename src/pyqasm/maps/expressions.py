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
from openqasm3.ast import AngleType, BitType, BoolType, ComplexType, FloatType, IntType, UintType

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
    """
    try:
        operator = OPERATOR_MAP[op_name]
        return operator(*args)
    except KeyError as exc:
        raise ValidationError(f"Unsupported / undeclared QASM operator: {op_name}") from exc


# pylint: disable=inconsistent-return-statements
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
    type_of_rhs = type(rhs_value)

    if type_of_rhs not in VARIABLE_TYPE_CAST_MAP[openqasm_type]:
        raise ValidationError(
            f"Cannot cast {type_of_rhs} to {openqasm_type}. "
            f"Invalid assignment of type {type_of_rhs} to variable {var_name} "
            f"of type {openqasm_type}"
        )

    if openqasm_type == BoolType:
        return bool(rhs_value)
    if openqasm_type == IntType:
        return int(rhs_value)
    if openqasm_type == UintType:
        return int(rhs_value) % (2**base_size)
    if openqasm_type == FloatType:
        return float(rhs_value)
    # not sure if we wanna hande array bit assignments too.
    # For now, we only cater to single bit assignment.
    if openqasm_type == BitType:
        return rhs_value != 0
    if openqasm_type == AngleType:
        return rhs_value  # not sure


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
    # AngleType: None,  # not sure
}

# Reference: https://openqasm.com/language/types.html#allowed-casts
VARIABLE_TYPE_CAST_MAP = {
    BoolType: (int, float, bool, np.int64, np.float64, np.bool_),
    IntType: (bool, int, float, np.int64, np.float64, np.bool_),
    BitType: (bool, int, np.int64, np.bool_),
    UintType: (bool, int, float, np.int64, np.uint64, np.float64, np.bool_),
    FloatType: (bool, int, float, np.int64, np.float64, np.bool_),
    AngleType: (float, np.float64),
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
