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
Module for play function validation.

This module contains functions for validating the play function in OpenPulse programs.
"""

from typing import Any

import openpulse.ast as openpulse_ast

from pyqasm.elements import Frame, Waveform
from pyqasm.exceptions import raise_qasm3_error
from pyqasm.pulse.expressions import OPENPULSE_WAVEFORM_FUNCTION_MAP


# pylint: disable-next=3:too-few-public-methods
class PlayValidator:
    """A class for validating the play function in OpenPulse programs."""

    def __init__(self, module, get_identifier_func, get_frame_func, pulse_visitor):
        """Initialize the PlayValidator.

        Args:
            module: The module containing device cycle time information.
            get_identifier_func: Function to get identifier information.
            get_frame_func: Function to get frame information.
            pulse_visitor: The pulse visitor.
        """
        self._module = module
        self._get_identifier = get_identifier_func
        self._get_frame = get_frame_func
        self._pulse_visitor = pulse_visitor

    def _handle_play_function(
        self, statement: openpulse_ast.FunctionCall, stmt_args: Any
    ) -> tuple[Any, Any]:
        """Handle the play function.

        Args:
            statement: The statement that is calling the function.
            stmt_args: The arguments of the play function.
        """
        frame_arg = stmt_args[0]
        waveform_arg = stmt_args[1]
        waveform_duration = None
        frame_obj = None
        if isinstance(frame_arg, openpulse_ast.Identifier):
            frame_obj = self._get_frame(statement, frame_arg.name)
            if not isinstance(frame_obj, Frame):
                raise_qasm3_error(
                    f"Invalid frame argument '{type(frame_arg).__name__}' in play function",
                    error_node=statement,
                    span=statement.span,
                )

        if isinstance(waveform_arg, openpulse_ast.Identifier):
            waveform_obj = self._get_identifier(statement, waveform_arg)
            if not isinstance(waveform_obj, Waveform):
                raise_qasm3_error(
                    f"'{waveform_arg.name}' should be a waveform variable",
                    error_node=statement,
                    span=statement.span,
                )
            waveform_duration = waveform_obj
        elif isinstance(waveform_arg, openpulse_ast.FunctionCall):
            wf_func_name = waveform_arg.name.name
            if wf_func_name not in OPENPULSE_WAVEFORM_FUNCTION_MAP:
                raise_qasm3_error(
                    f"Invalid waveform function '{wf_func_name}'",
                    error_node=statement,
                    span=statement.span,
                )
            self._pulse_visitor._check_waveform_functions(waveform_arg, wf_func_name)
            waveform_duration = self._pulse_visitor._temp_waveform
            self._pulse_visitor._temp_waveform = None
        else:
            raise_qasm3_error(
                f"Invalid waveform argument '{type(waveform_arg).__name__ }' in play function",
                error_node=statement,
                span=statement.span,
            )

        return frame_obj, waveform_duration
