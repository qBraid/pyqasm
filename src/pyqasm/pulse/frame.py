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
Module for frame validation functions.

This module contains functions for validating different types of frame
declarations in OpenPulse programs.
"""
from typing import Any, Tuple

import openqasm3.ast as qasm3_ast

from pyqasm.elements import Variable
from pyqasm.exceptions import raise_qasm3_error
from pyqasm.expressions import Qasm3ExprEvaluator
from pyqasm.maps.expressions import CONSTANTS_MAP, TIME_UNITS_MAP


class FrameValidator:
    """A class for validating frame declarations in OpenPulse programs."""

    def __init__(self, module, get_identifier_func, pulse_visitor):
        """Initialize the FrameValidator.

        Args:
            module: The module containing device cycle time information.
            get_identifier_func: Function to get identifier information.
            pulse_visitor: The pulse visitor.
        """
        self._module = module
        self._get_identifier = get_identifier_func
        self._pulse_visitor = pulse_visitor

    def validate_get_phase_freq_type(
        self,
        statement: Any,
        function_name: str,
        actual_type: Any,
    ) -> None:
        """Validate that get_phase and get_frequency functions have correct return types.

        Args:
            statement: The statement for error reporting
            function_name: Name of the function being validated
            actual_type: The actual type to validate
            error_context: Context for error message (e.g., "type" or "return type")
        """
        if (function_name == "get_phase" and not isinstance(actual_type, qasm3_ast.AngleType)) or (
            function_name == "get_frequency" and not isinstance(actual_type, qasm3_ast.FloatType)
        ):
            raise_qasm3_error(
                f"Invalid type '{type(actual_type).__name__}' for function '{function_name}'",
                error_node=statement,
                span=statement.span,
            )

    def validate_newframe_function(self, statement: Any, init_expr: Any) -> None:
        """Validate that the frame initialization function is 'newframe'.

        Args:
            statement: The statement for error reporting
            init_expr: The initialization expression
        """
        new_frame = getattr(getattr(init_expr, "name", None), "name", None)
        if new_frame != "newframe":
            raise_qasm3_error(
                f"Invalid frame initialization function '{new_frame}'",
                error_node=statement,
                span=statement.span,
            )

    # pylint: disable-next=too-many-branches,too-many-locals,too-many-statements
    def validate_newframe_arguments(
        self, statement: Any, frame_args: list, time_unit: qasm3_ast.TimeUnit
    ) -> Tuple[
        str, float, qasm3_ast.FloatType, float, qasm3_ast.AngleType, qasm3_ast.DurationLiteral
    ]:
        """Validate all arguments for newframe function.

        Args:
            statement: The statement for error reporting
            frame_args: List of arguments to validate
            time_unit: Time unit for duration literals

        Returns:
            Tuple of (port_name, freq_value, freq_type, phase_value, phase_type, time_value)
        """
        # Port argument
        frame_limit_per_port = self._pulse_visitor._frame_limit_per_port
        ports_usage = self._pulse_visitor._ports_usage
        port_arg = frame_args[0]
        if not isinstance(port_arg, qasm3_ast.Identifier):
            _id_port_var_obj = self._get_identifier(statement, port_arg)
            if _id_port_var_obj is None:
                raise_qasm3_error(
                    f"Invalid or undeclared port argument "
                    f"'{getattr(port_arg, 'name', port_arg)}' in frame",
                    error_node=statement,
                    span=statement.span,
                )
            port_arg = _id_port_var_obj.name
            ports_usage[port_arg.name] = ports_usage.get(port_arg.name, 0) + 1

            if ports_usage[port_arg.name] > frame_limit_per_port:
                raise_qasm3_error(
                    f"Port '{port_arg.name}' has exceeded the "
                    f"frame limit of {frame_limit_per_port}",
                    error_node=statement,
                    span=statement.span,
                )

        # Frequency argument
        freq_arg = frame_args[1]
        freq_arg_value = 0.0
        freq_arg_type = qasm3_ast.FloatType(qasm3_ast.IntegerLiteral(32))

        if isinstance(freq_arg, qasm3_ast.Identifier):
            _id_freq_var_obj = self._get_identifier(statement, freq_arg)
            if _id_freq_var_obj is None:
                _id_freq_var_obj = Variable(
                    name=freq_arg.name,
                    value=None,
                    base_type=qasm3_ast.FloatType(qasm3_ast.IntegerLiteral(32)),
                    base_size=32,
                    is_constant=True,
                )
                self._pulse_visitor._openpulse_scope_manager.add_var_in_scope(_id_freq_var_obj)
            if not getattr(_id_freq_var_obj, "is_constant", False) or not isinstance(
                _id_freq_var_obj.base_type, qasm3_ast.FloatType
            ):
                raise_qasm3_error(
                    f"Frequency argument '{freq_arg.name}' must be a constant float",
                    error_node=statement,
                    span=statement.span,
                )
            freq_arg_value = _id_freq_var_obj.value
            freq_arg_type = _id_freq_var_obj.base_type
            freq_arg_type.size = getattr(_id_freq_var_obj, "base_size", None)
        elif isinstance(freq_arg, qasm3_ast.FloatLiteral):
            freq_arg_value = freq_arg.value
        elif isinstance(freq_arg, qasm3_ast.FunctionCall):
            if freq_arg.name.name == "get_frequency":
                freq_arg_value = self._pulse_visitor._visit_function_call(freq_arg)[0]
        else:
            raise_qasm3_error(
                f"Invalid frequency argument '{freq_arg}' in frame",
                error_node=statement,
                span=statement.span,
            )

        # Phase argument
        phase_arg = frame_args[2]
        phase_arg_value = 0.0
        phase_arg_type = qasm3_ast.AngleType(qasm3_ast.IntegerLiteral(32))

        if isinstance(phase_arg, qasm3_ast.Identifier):
            if phase_arg.name in CONSTANTS_MAP:
                phase_arg_value = CONSTANTS_MAP[phase_arg.name]
            else:
                _id_phase_var_obj = self._get_identifier(statement, phase_arg)
                if (
                    _id_phase_var_obj is None
                    or not getattr(_id_phase_var_obj, "is_constant", False)
                    or not isinstance(_id_phase_var_obj.base_type, qasm3_ast.AngleType)
                ):
                    raise_qasm3_error(
                        f"Phase argument '{phase_arg.name}' must be a constant Angle",
                        error_node=statement,
                        span=statement.span,
                    )
                phase_arg_value = _id_phase_var_obj.value
                phase_arg_type = _id_phase_var_obj.base_type
                phase_arg_type.size = getattr(_id_phase_var_obj, "base_size", None)
        elif isinstance(
            phase_arg,
            (qasm3_ast.BinaryExpression, qasm3_ast.UnaryExpression, qasm3_ast.FloatLiteral),
        ):
            phase_arg_value, _ = Qasm3ExprEvaluator.evaluate_expression(phase_arg)
        elif isinstance(phase_arg, qasm3_ast.FunctionCall):
            if phase_arg.name.name == "get_phase":
                phase_arg_value = self._pulse_visitor._visit_function_call(phase_arg)[0]
        else:
            raise_qasm3_error(
                f"Invalid Phase argument '{phase_arg}' in frame",
                error_node=statement,
                span=statement.span,
            )

        # Time argument (optional)
        time_arg_value = qasm3_ast.DurationLiteral(0, unit=time_unit)
        if len(frame_args) == 4:
            time_arg = frame_args[3]
            if isinstance(time_arg, qasm3_ast.Identifier):
                _id_dur_var_obj = self._get_identifier(statement, time_arg)
                if (
                    _id_dur_var_obj is None
                    or not getattr(_id_dur_var_obj, "is_constant", False)
                    or not isinstance(_id_dur_var_obj.base_type, qasm3_ast.DurationType)
                ):
                    raise_qasm3_error(
                        f"Time argument '{time_arg.name}' must be a constant Duration",
                        error_node=statement,
                        span=statement.span,
                    )
                time_arg_value = qasm3_ast.DurationLiteral(_id_dur_var_obj.value, unit=time_unit)
            elif isinstance(time_arg, qasm3_ast.DurationLiteral):
                time_arg_value = qasm3_ast.DurationLiteral(time_arg.value, unit=time_arg.unit)
            elif isinstance(time_arg, qasm3_ast.IntegerLiteral) and time_arg.value == 0:
                time_arg_value = qasm3_ast.DurationLiteral(0, unit=time_unit)
            else:
                raise_qasm3_error(
                    f"Invalid Time argument '{time_arg}' in frame",
                    error_node=statement,
                    span=statement.span,
                )
            if time_arg_value.value is not None:
                time_arg_value.value = (
                    time_arg_value.value * TIME_UNITS_MAP[time_arg_value.unit.name]["ns"]
                )
                time_arg_value.unit = qasm3_ast.TimeUnit.ns

        return (
            port_arg.name,
            freq_arg_value,
            freq_arg_type,
            phase_arg_value,
            phase_arg_type,
            time_arg_value,
        )
