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

from openqasm3.ast import (
    BinaryExpression,
    Box,
    Cast,
    ConstantDeclaration,
    DelayInstruction,
    DurationLiteral,
    DurationType,
    FloatLiteral,
    Identifier,
    IntegerLiteral,
    Statement,
    StretchType,
)

from pyqasm.exceptions import raise_qasm3_error


class PulseValidator:
    """Class with validation functions for Pulse visitor"""

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
            ValidationeError
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
            ValidationeError
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
