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
Module with utility functions for Pulse visitor

"""
from typing import Any, Optional

import numpy as np
from openqasm3.ast import (
    BinaryExpression,
    BinaryOperator,
    BitstringLiteral,
    Box,
    Cast,
    ConstantDeclaration,
    DelayInstruction,
    DurationLiteral,
    DurationType,
    FloatLiteral,
    Identifier,
    ImaginaryLiteral,
    IntegerLiteral,
    Statement,
    StretchType,
)

from pyqasm.exceptions import raise_qasm3_error
from pyqasm.maps.expressions import CONSTANTS_MAP


class PulseValidator:
    """Class with validation functions for Pulse visitor"""

    @staticmethod
    def validate_angle_type_value(
        statement: Any,
        init_value: int | float,
        base_size: int,
        compiler_angle_width: Optional[int] = None,
    ) -> tuple:
        """
        Validates and processes angle type value.

        Args:
            statement: The AST statement node
            init_value: The evaluated initialization value
            base_size: The base size of the angle type
            compiler_angle_width: Optional compiler angle width override

        Returns:
            tuple: The processed angle value and bit string representation

        Raises:
            ValidationError: If the angle initialization is invalid
        """
        # Optimize: check both possible fields for BitstringLiteral in one go
        init_exp = getattr(statement, "init_expression", None)
        rval = getattr(statement, "rvalue", None)
        is_bitstring = isinstance(init_exp, BitstringLiteral) or isinstance(rval, BitstringLiteral)
        expression = init_exp or rval
        if is_bitstring and expression is not None:
            angle_type_size = expression.width
            if compiler_angle_width:
                if angle_type_size != compiler_angle_width:
                    raise_qasm3_error(
                        f"BitString angle width '{angle_type_size}' does not match "
                        f"with compiler angle width '{compiler_angle_width}'",
                        error_node=statement,
                        span=statement.span,
                    )
                angle_type_size = compiler_angle_width
            angle_bit_string = format(expression.value, f"0{angle_type_size}b")
            # Reference: https://openqasm.com/language/types.html#angles
            angle_val = (2 * CONSTANTS_MAP["pi"]) * (expression.value / (2**angle_type_size))
        else:
            angle_val = init_value % (2 * CONSTANTS_MAP["pi"])
            angle_type_size = compiler_angle_width or base_size
            bit_string_value = round((2**angle_type_size) * (angle_val / (2 * CONSTANTS_MAP["pi"])))
            angle_bit_string = format(bit_string_value, f"0{angle_type_size}b")

        return angle_val, angle_bit_string

    @staticmethod
    def validate_duration_or_stretch_statements(
        statement: Statement,
        base_type: Any,
        rvalue: Any,
        global_scope: dict,
    ) -> None:
        """
        Generic validation function for DurationType and StretchType declarations or assignments.

        Args:
            statement: The AST statement node
            statement_type: The expected AST node type
            base_type: The declared type (DurationType or StretchType)
            rvalue: The initializer or assigned value
            global_scope: Global symbol table.

        Raises:
            ValidationError: If the assigned value is not a DurationLiteral,
            or if an Identifier is assigned that does not refer to a DurationType
            or StretchType, or if a Cast is used as the assigned value.
        """
        statement_type = type(statement)
        kind = "constant variable" if statement_type is ConstantDeclaration else "variable"

        if isinstance(base_type, (DurationType, StretchType)):
            if isinstance(rvalue, IntegerLiteral):
                raise_qasm3_error(
                    f"{kind} with '{type(base_type).__name__}' "
                    "expects a value of type "
                    f"'{DurationLiteral.__name__}'",
                    error_node=statement,
                    span=statement.span,
                )

            if isinstance(rvalue, Identifier):
                if rvalue.name in global_scope:
                    ref_var = global_scope[rvalue.name]
                    if not isinstance(ref_var.base_type, (DurationType, StretchType)):
                        raise_qasm3_error(
                            f"Assigned {kind} '{ref_var.name}' is not "
                            "in 'DurationType' or 'StretchType'",
                            error_node=statement,
                            span=statement.span,
                        )

            if isinstance(rvalue, Cast):
                raise_qasm3_error(
                    f"{kind} with '{type(base_type).__name__}' " "doesn't support 'Casting'",
                    error_node=statement,
                    span=statement.span,
                )

    @staticmethod
    def validate_duration_literal_value(
        duration_literal: Any,
        statement: Statement,
        base_type: Optional[Any] = None,
    ) -> None:
        """
        Validates the value of a duration literal value.

        Args:
            duration_literal: The value to validate (should be a number).
            statement: The AST statement node.
            base_type: The declared type (DurationType or StretchType), optional.

        Raises:
            ValidationError: If the duration value is invalid.
        """
        if base_type and duration_literal is not None:
            if isinstance(base_type, StretchType) and duration_literal <= 0:
                raise_qasm3_error(
                    f"'{StretchType.__name__}'[{duration_literal}] cannot have duration "
                    "value 'less than or equal to 0'",
                    error_node=statement,
                    span=statement.span,
                )
            if isinstance(base_type, DurationType) and duration_literal == 0:
                raise_qasm3_error(
                    f"'{DurationType.__name__}' cannot have duration value '0'",
                    error_node=statement,
                    span=statement.span,
                )
            return

        if isinstance(statement, (Box, DelayInstruction)):
            if duration_literal <= 0:
                raise_qasm3_error(
                    f"'{type(statement).__name__}' cannot have duration "
                    "value 'less than or equal to 0'",
                    error_node=statement,
                    span=statement.span,
                )

    @staticmethod
    def validate_duration_variable(  # pylint: disable=too-many-branches
        duration_var: Any, statement: Statement, global_scope: dict, curr_scope: dict
    ) -> None:
        """
        Validates that the duration variable.
        Args:
            duration_var: The duration variable/expression to validate.
            statement: Any Statement AST node with duration.
            global_scope: The global dict of variable names to Variable objects.
            curr_scope: current scope of variable names to Variable objects

        Raises:
            ValidationError: Raised if the duration variable is not defined in the current
            or global scope, or if the variable is not of type 'stretch' or 'duration',
            or if both sides of a binary duration expression are numeric literals.
        """
        if isinstance(duration_var, BinaryExpression):
            lhs_val = duration_var.lhs
            rhs_val = duration_var.rhs
            for val in (lhs_val, rhs_val):
                if isinstance(val, Identifier):
                    if val.name not in (global_scope | curr_scope):
                        raise_qasm3_error(
                            f"'{type(statement).__name__}' variable '{val.name}' is not defined",
                            error_node=statement,
                            span=duration_var.span,
                        )
                    # Check type only if variable is present in the scope
                    var_obj = None
                    if curr_scope and val.name in curr_scope:
                        var_obj = curr_scope[val.name]
                    elif global_scope and val.name in global_scope:
                        var_obj = global_scope[val.name]
                    if var_obj and not isinstance(var_obj.base_type, (StretchType, DurationType)):
                        raise_qasm3_error(
                            f"'{type(statement).__name__}' variable must be of type "
                            "'stretch' or 'duration'",
                            error_node=statement,
                            span=duration_var.span,
                        )

            if isinstance(lhs_val, (IntegerLiteral, FloatLiteral)) and isinstance(
                rhs_val, (IntegerLiteral, FloatLiteral)
            ):
                raise_qasm3_error(
                    f"Both lhs and rhs of delay values cannot be '{type(lhs_val).__name__}' "
                    f"and '{type(rhs_val).__name__}'",
                    error_node=statement,
                    span=duration_var.span,
                )

        if isinstance(duration_var, Identifier):
            if duration_var.name not in (global_scope | curr_scope):
                raise_qasm3_error(
                    f"'{type(statement).__name__}' variable '{duration_var.name}' is not defined",
                    error_node=statement,
                    span=statement.span,
                )
            # Check type only if variable is present in the scope
            var_obj = None
            if curr_scope and duration_var.name in curr_scope:
                var_obj = curr_scope[duration_var.name]
            elif global_scope and duration_var.name in global_scope:
                var_obj = global_scope[duration_var.name]
            if var_obj and not isinstance(var_obj.base_type, (StretchType, DurationType)):
                raise_qasm3_error(
                    f"{type(statement).__name__} variable must be of type 'stretch' or 'duration'",
                    error_node=statement,
                    span=statement.span,
                )
            var_val = var_obj.value if var_obj is not None else None
            if var_val and var_val <= 0:
                raise_qasm3_error(
                    f"variable '{duration_var.name} = {var_val}' "
                    f"in '{type(statement).__name__}', must be 'greater than 0'",
                    error_node=statement,
                    span=statement.span,
                )

        if isinstance(duration_var, IntegerLiteral):
            raise_qasm3_error(
                f"'{type(statement).__name__}' value must be a '{DurationLiteral.__name__}'.",
                error_node=statement,
                span=statement.span,
            )

    @staticmethod
    def make_complex_binary_expression(value: complex) -> BinaryExpression:
        """
        Make a binary expression from a complex number.
        """
        return BinaryExpression(
            lhs=FloatLiteral(value.real),
            op=(BinaryOperator["+"] if value.imag >= 0 else BinaryOperator["-"]),
            rhs=ImaginaryLiteral(np.abs(value.imag)),
        )
