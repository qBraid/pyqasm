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
Module with validation functions for Pulse visitor

"""
from typing import Any, Optional

import numpy as np
import openqasm3.ast as qasm3_ast
from openqasm3.ast import (
    BinaryExpression,
    BinaryOperator,
    BitstringLiteral,
    BitType,
    Box,
    Cast,
    ComplexType,
    ConstantDeclaration,
    DelayInstruction,
    DurationLiteral,
    DurationType,
    ExternDeclaration,
    FloatLiteral,
    FloatType,
    FunctionCall,
    Identifier,
    ImaginaryLiteral,
    IntegerLiteral,
    IntType,
    Statement,
    StretchType,
    TimeUnit,
)

from pyqasm.exceptions import raise_qasm3_error
from pyqasm.expressions import Qasm3ExprEvaluator
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

    @staticmethod
    def validate_openpulse_gate_parameters(  # pylint: disable=too-many-arguments
        operation: Any,
        gate_op: str,
        gate_def: Any,
        pulse_visitor: Any,
        scope_manager: Any,
        module: Any,
    ) -> Any:
        """
        Validate and process parameters for OpenPulse gates.

        Args:
            operation: The quantum gate operation to validate
            gate_op: The name of the gate operation
            gate_def: The gate definition containing formal arguments
            pulse_visitor: The pulse visitor instance
            scope_manager: The scope manager instance
            module: The module instance

        Returns:
            The validated and processed operation

        Raises:
            Qasm3Error: If parameter count or type mismatch occurs
        """
        if len(gate_def.arguments) != len(operation.arguments):
            raise_qasm3_error(
                f"Parameter count mismatch for gate '{gate_op}'. "
                f"Expected {len(gate_def.arguments)} arguments, but "
                f" got {len(operation.arguments)} instead.",
                error_node=operation,
                span=operation.span,
            )

        for j, (formal_arg, actual_arg) in enumerate(zip(gate_def.arguments, operation.arguments)):
            assert isinstance(formal_arg, qasm3_ast.ClassicalArgument)
            if isinstance(actual_arg, qasm3_ast.Identifier):
                arg_obj = pulse_visitor._get_identifier(operation, actual_arg)
                formal_arg_size = pulse_visitor._check_variable_type_size(
                    formal_arg, formal_arg.name.name, "variable", formal_arg.type
                )
                if not (
                    isinstance(arg_obj.base_type, type(formal_arg.type))
                    and arg_obj.base_size == formal_arg_size
                ):
                    raise_qasm3_error(
                        f"Parameter type mismatch for gate '{gate_op}'. "
                        f"Expected '{type(formal_arg.type).__name__}[{formal_arg_size}]', "
                        f"but got '{type(arg_obj.base_type).__name__}[{arg_obj.base_size}]'.",
                        error_node=operation,
                        span=operation.span,
                    )

                operation = PulseValidator.validate_and_process_extern_function_call(
                    operation,
                    scope_manager.get_global_scope(),
                    module._device_cycle_time,
                )
            else:
                val = Qasm3ExprEvaluator.evaluate_expression(actual_arg)[0]
                valid = False
                if isinstance(actual_arg, qasm3_ast.DurationLiteral):
                    valid = isinstance(
                        formal_arg.type, (qasm3_ast.DurationType, qasm3_ast.StretchType)
                    )
                elif isinstance(val, float) and isinstance(
                    formal_arg.type, (qasm3_ast.FloatType, qasm3_ast.AngleType)
                ):
                    valid = True
                    operation.arguments[j] = qasm3_ast.FloatLiteral(val)  # type: ignore
                elif isinstance(val, int) and isinstance(
                    formal_arg.type, (qasm3_ast.IntType, qasm3_ast.BoolType)
                ):
                    valid = True
                    operation.arguments[j] = qasm3_ast.IntegerLiteral(val)  # type: ignore
                elif isinstance(formal_arg.type, qasm3_ast.ComplexType) and isinstance(
                    val, complex
                ):
                    valid = True
                    operation.arguments[j] = (  # type: ignore
                        PulseValidator.make_complex_binary_expression(val)
                    )
                if not valid:
                    raise_qasm3_error(
                        f"Invalid argument type '{type(actual_arg).__name__}' for "
                        f"parameter '{formal_arg.name.name}' of gate '{gate_op}'",
                        error_node=operation,
                        span=operation.span,
                    )

        return operation

    @staticmethod
    def validate_extern_declaration(module: Any, statement: ExternDeclaration) -> None:
        """
        Validates an extern declaration.
        Args:
            module: The module object
            statement: The extern declaration statement

        Raises:
            ValidationError: If the extern declaration is invalid
        """
        args = module._extern_functions[statement.name.name][0]
        if len(args) != len(statement.arguments):
            raise_qasm3_error(
                f"Parameter count mismatch for 'extern' subroutine '{statement.name.name}'. "
                f"Expected {len(args)} but got {len(statement.arguments)}",
                error_node=statement,
                span=statement.span,
            )

        def _get_type_string(type_obj) -> str:
            """Recursively build type string for nested types"""
            type_name = type(type_obj).__name__.replace("Type", "").lower()
            if getattr(type_obj, "base_type", None) is not None:
                return f"{type_name}[{_get_type_string(type_obj.base_type)}]"
            if getattr(type_obj, "size", None) is not None:
                return f"{type_name}[{type_obj.size.value}]"
            return type_name

        for actual_arg, extern_arg in zip(statement.arguments, args):
            if actual_arg == extern_arg:
                continue
            actual_arg_type = _get_type_string(actual_arg.type)
            if actual_arg_type != str(extern_arg).lower():
                raise_qasm3_error(
                    f"Parameter type mismatch for 'extern' subroutine '{statement.name.name}'. "
                    f"Expected {extern_arg} but got {actual_arg_type}",
                    error_node=statement,
                    span=statement.span,
                )
        return_type = module._extern_functions[statement.name.name][1]
        actual_type_name = _get_type_string(statement.return_type)
        if return_type == statement.return_type:
            return
        if str(return_type).lower() != actual_type_name:
            raise_qasm3_error(
                f"Return type mismatch for 'extern' subroutine '{statement.name.name}'. Expected "
                f"{return_type} but got {actual_type_name}",
                error_node=statement,
                span=statement.span,
            )

    @staticmethod
    def validate_and_process_extern_function_call(  # pylint: disable=too-many-branches
        statement: Any, global_scope: dict, device_cycle_time: float | None
    ) -> Any:
        """Validate and process extern function arguments
        by converting them to appropriate literals.

        Args:
            statement: The statement to process
            global_scope: The global scope of the module
            device_cycle_time: The device cycle time of the module

        Returns:
            The validated and processed statement

        Raises:
            ValidationError: If the function call is invalid
        """

        for i, arg in enumerate(statement.arguments):
            if isinstance(arg, Identifier):
                arg_var = global_scope.get(arg.name)
                assert arg_var is not None

                if arg_var.base_type is not None and isinstance(
                    arg_var.base_type, (DurationType, StretchType)
                ):
                    statement.arguments[i] = DurationLiteral(
                        float(arg_var.value) if arg_var.value is not None else 0.0,
                        unit=(TimeUnit.dt if device_cycle_time else TimeUnit.ns),
                    )
                elif isinstance(arg_var.value, float):
                    statement.arguments[i] = FloatLiteral(arg_var.value)
                elif isinstance(arg_var.value, int):
                    statement.arguments[i] = IntegerLiteral(arg_var.value)
                elif isinstance(arg_var.value, complex):
                    statement.arguments[i] = PulseValidator.make_complex_binary_expression(
                        arg_var.value
                    )
                elif isinstance(arg_var.value, str):
                    width = len(arg_var.value)
                    value = int(arg_var.value, 2)
                    statement.arguments[i] = BitstringLiteral(value, width)

        return statement

    @staticmethod
    def validate_openpulse_func_arg_length(
        statement: FunctionCall, name: str, no_of_args: int
    ) -> None:
        """Validate the argument lengths.

        Args:
            statement (Any): The statement that is calling the function.
            name (str): The name of the function.
            no_of_args (int): The number of arguments of the function.
        """
        # Define argument requirements for each function group
        arg_requirements = {
            "set_phase": 2,
            "shift_phase": 2,
            "set_frequency": 2,
            "shift_frequency": 2,
            "play": 2,
            "constant": 2,
            "phase_shift": 2,
            "scale": 2,
            "mix": 2,
            "sum": 2,
            "capture_v1": 2,
            "capture_v2": 2,
            "capture_v3": 2,
            "capture_v4": 2,
            "get_phase": 1,
            "get_frequency": 1,
            "capture_v0": 1,
            "gaussian": 3,
            "sech": 3,
            "gaussian_square": 4,
            "drag": 4,
            "sine": 4,
            "newframe": (3, 4),
        }

        expected_args = arg_requirements.get(name)
        if expected_args is not None:
            valid = (
                no_of_args in expected_args
                if isinstance(expected_args, tuple)
                else no_of_args == expected_args
            )
            if not valid:
                raise_qasm3_error(
                    f"Invalid number of arguments for {name} function",
                    error_node=statement,
                    span=statement.span,
                )

    @staticmethod
    def validate_capture_function_return_type(
        statement: FunctionCall, f_name: str, _type: Any
    ) -> None:
        """Validate the return type for capture functions.

        Args:
            statement: The AST statement node
            f_name: The name of the capture function
            _type: The return type to validate

        Raises:
            ValidationError: If the return type is invalid for the capture function
        """
        from openpulse.ast import WaveformType  # pylint: disable=import-outside-toplevel

        if f_name == "capture_v1" and not (
            isinstance(_type, ComplexType)
            and isinstance(_type.base_type, FloatType)
            and _type.base_type.size.value == 32  # type: ignore
        ):
            raise_qasm3_error(
                f"Invalid return type '{type(_type).__name__}' " f"for function '{f_name}'",
                error_node=statement,
                span=statement.span,
            )
        if f_name == "capture_v2" and not isinstance(_type, BitType):
            raise_qasm3_error(
                f"Invalid return type '{type(_type).__name__}' " f"for function '{f_name}'",
                error_node=statement,
                span=statement.span,
            )
        if f_name == "capture_v3" and not isinstance(_type, WaveformType):
            raise_qasm3_error(
                f"Invalid return type '{type(_type).__name__}' " f"for function '{f_name}'",
                error_node=statement,
                span=statement.span,
            )
        if f_name == "capture_v4" and not isinstance(_type, IntType):
            raise_qasm3_error(
                f"Invalid return type '{type(_type).__name__}' " "for function '{f_name}'",
                error_node=statement,
                span=statement.span,
            )
