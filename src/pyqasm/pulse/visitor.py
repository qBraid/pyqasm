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

# pylint: disable=too-many-lines


"""
Module defining OpenPulse Visitor.

"""
import logging
from typing import Any, Optional

import openqasm3.ast as qasm3_ast

from pyqasm.elements import Capture, Frame, Variable, Waveform
from pyqasm.exceptions import (
    raise_qasm3_error,
)
from pyqasm.expressions import Qasm3ExprEvaluator
from pyqasm.maps.expressions import (
    CONSTANTS_MAP,
    FUNCTION_MAP,
    TIME_UNITS_MAP,
)
from pyqasm.pulse.expressions import (
    OPENPULSE_CAPTURE_FUNCTION_MAP,
    OPENPULSE_FRAME_FUNCTION_MAP,
    OPENPULSE_WAVEFORM_FUNCTION_MAP,
)
from pyqasm.pulse.frame import FrameValidator
from pyqasm.pulse.play import PlayValidator
from pyqasm.pulse.validator import PulseValidator
from pyqasm.pulse.waveform import WaveformValidator

logger = logging.getLogger(__name__)
logger.propagate = False


# pylint: disable-next=too-many-instance-attributes
class OpenPulseVisitor:
    """A visitor for basic OpenPulse program elements.

    This class is designed to traverse and interact with elements in an OpenPulse program.

    Args:
        visitor: The QasmVisitor instance that provides scope and context information.
        check_only: If True, only check the program without executing it. Defaults to False.
    """

    def __init__(
        self,
        qasm_visitor,
        check_only: bool = False,
    ):
        self._qasm_visitor = qasm_visitor
        self._module = qasm_visitor._module
        self._qasm3_scope_manager = qasm_visitor._scope_manager
        self._openpulse_scope_manager = qasm_visitor._openpulse_scope_manager
        self._check_only: bool = check_only
        self._ports_usage: dict[str, int] = {}
        self._is_def_cal: bool = False
        self._temp_waveform: Waveform | None = None  # type: ignore
        self._current_block_time: qasm3_ast.DurationLiteral = qasm3_ast.DurationLiteral(
            0,
            unit=(
                qasm3_ast.TimeUnit.dt if self._module._device_cycle_time else qasm3_ast.TimeUnit.ns
            ),
        )
        self._waveform_validator = WaveformValidator(
            self._module, self._get_identifier, self._get_frame, self
        )
        self._frame_validator = FrameValidator(self._module, self._get_identifier, self)
        self._play_validator = PlayValidator(
            self._module, self._get_identifier, self._get_frame, self
        )

    def _update_current_block_time(self, duration: float) -> None:
        """Update the current block time.

        Args:
            duration (float): The duration to update the current block time.
        """
        self._current_block_time = qasm3_ast.DurationLiteral(
            self._current_block_time.value + duration,
            unit=(
                qasm3_ast.TimeUnit.dt if self._module._device_cycle_time else qasm3_ast.TimeUnit.ns
            ),
        )

    def _get_frame(self, statement: Any, frame: str) -> Frame:
        """Get the frame from the global scope.

        Args:
            frame (str): The frame to get.
            statement (Any): The statement that is calling the function.
        """
        frame_obj = self._openpulse_scope_manager.get_from_visible_scope(frame)
        if not isinstance(frame_obj, Frame) or frame_obj is None:
            raise_qasm3_error(
                f"Frame '{frame}' not declared",
                error_node=statement,
                span=statement.span,
            )
        return frame_obj

    def _update_frame_time(self, statement: Any, frame: str, time: float) -> None:
        """Update the time of a frame.

        Args:
            statement (Any): The statement that is calling the function.
            frame (str): The frame to update the time of.
            time (float): The time to update the frame to.
        """
        frame_obj = self._get_frame(statement, frame)
        self._update_current_block_time(time)
        frame_obj.time = self._current_block_time

    def _get_identifier(self, statement: Any, identifier: qasm3_ast.Identifier | str) -> Any:
        """Get the value of an identifier.

        Args:
            identifier (qasm3_ast.Identifier): The identifier to get the value of.
            statement (Any): The statement that is calling the function.
        """
        if isinstance(identifier, str):
            identifier = qasm3_ast.Identifier(name=identifier)
        _id_var_obj = self._openpulse_scope_manager.get_from_all_scopes(
            identifier.name
        ) or self._qasm3_scope_manager.get_from_all_scopes(identifier.name)
        if _id_var_obj is None:
            raise_qasm3_error(
                f"{type(_id_var_obj).__name__} '{identifier.name}' not declared",
                error_node=statement,
                span=statement.span,
            )
        return _id_var_obj

    def _check_identifier(self, statement: Any, identifier: qasm3_ast.Identifier) -> None:
        """Check if an identifier is declared."""
        _id_var_obj = self._openpulse_scope_manager.get_from_global_scope(
            identifier.name
        ) or self._qasm3_scope_manager.get_from_visible_scope(identifier.name)
        if isinstance(_id_var_obj, Waveform):
            if _id_var_obj.is_constant:
                raise_qasm3_error(
                    f"Waveform '{identifier.name}' is constant",
                    error_node=statement,
                    span=statement.span,
                )
            return
        if _id_var_obj is not None:
            raise_qasm3_error(
                f"{type(_id_var_obj).__name__} '{identifier.name}' is already declared",
                error_node=statement,
                span=statement.span,
            )

    def _set_shift_phase(  # pylint: disable=too-many-arguments
        self,
        statement: Any,
        frame: str,
        phase: qasm3_ast.FloatLiteral | qasm3_ast.Identifier,
        set_phase: bool = False,
        shift_phase: bool = False,
    ) -> None:
        """Set or shift the phase of a frame.

        Args:
            statement (Any): The statement that is calling the function.
            frame (str): The frame to set or shift the phase of.
            phase (qasm3_ast.FloatLiteral | qasm3_ast.Identifier): The phase to set or shift.
            set_phase (bool): If True, set the phase of the frame.
            shift_phase (bool): If True, shift the phase of the frame.
        """
        frame_obj = self._get_frame(statement, frame)
        if isinstance(phase, qasm3_ast.Identifier):
            _phase_arg_obj = self._get_identifier(statement, phase)
            if (
                not isinstance(frame_obj.phase_type, type(_phase_arg_obj.base_type))
                or _phase_arg_obj.base_size != frame_obj.phase_type.size
            ):
                raise_qasm3_error(
                    f"Phase argument '{phase.name}' must be a AngleType "
                    f"with same size in frame '{frame}'",
                    error_node=statement,
                    span=statement.span,
                )
            if set_phase:
                frame_obj.phase = _phase_arg_obj.value
            if shift_phase:
                frame_obj.phase = (frame_obj.phase + _phase_arg_obj.value) % (
                    2 * CONSTANTS_MAP["pi"]
                )
        elif isinstance(phase, qasm3_ast.FloatLiteral):
            if set_phase:
                frame_obj.phase = phase.value
            if shift_phase:
                frame_obj.phase = (frame_obj.phase + phase.value) % (2 * CONSTANTS_MAP["pi"])

        statement.arguments[1] = qasm3_ast.FloatLiteral(frame_obj.phase)

    def _set_shift_frequency(  # pylint: disable=too-many-arguments
        self,
        statement: Any,
        frame: str,
        frequency: qasm3_ast.FloatLiteral | qasm3_ast.Identifier,
        set_frequency: bool = False,
        shift_frequency: bool = False,
    ) -> None:
        """Set or shift the frequency of a frame.
        Args:
            statement (Any): The statement that is calling the function.
            frame (Frame): The frame to set or shift the frequency of frame.
            frequency (qasm3_ast.FloatLiteral | qasm3_ast.Identifier): The frequency to
                                                                       set or shift.
            set_frequency (bool): If True, set the frequency of the frame.
            shift_frequency (bool): If True, shift the frequency of the frame.
        """
        frame_obj = self._get_frame(statement, frame)
        if isinstance(frequency, qasm3_ast.Identifier):
            _freq_arg_obj = self._get_identifier(statement, frequency)
            if (
                not isinstance(frame_obj.frequency_type, type(_freq_arg_obj.base_type))
                or _freq_arg_obj.base_size != frame_obj.frequency_type.size.value
            ):
                raise_qasm3_error(
                    f"Frequency argument '{frequency.name}' must be a "
                    f"FloatType with same size in frame '{frame}'",
                    error_node=statement,
                    span=statement.span,
                )
            if set_frequency:
                frame_obj.frequency = _freq_arg_obj.value
            if shift_frequency:
                frame_obj.frequency += _freq_arg_obj.value
        elif isinstance(frequency, qasm3_ast.FloatLiteral):
            if set_frequency:
                frame_obj.frequency = frequency.value
            if shift_frequency:
                frame_obj.frequency += frequency.value

        statement.arguments[1] = qasm3_ast.FloatLiteral(frame_obj.frequency)

    def _get_phase_frequency(
        self, statement: Any, frame: str, get_phase: bool = False, get_frequency: bool = False
    ) -> qasm3_ast.FloatLiteral:
        """Get the phase or frequency of a frame.

        Args:
            statement (Any): The statement that is calling the function.
            frame (str): The frame to get the phase or frequency of frame.
            get_phase (bool): If True, get the phase of the frame.
            get_frequency (bool): If True, get the frequency of the frame.
        """
        frame_obj = self._get_frame(statement, frame)
        if get_phase:
            return qasm3_ast.FloatLiteral(frame_obj.phase)
        if get_frequency:
            return qasm3_ast.FloatLiteral(frame_obj.frequency)
        return qasm3_ast.FloatLiteral(0)

    def _check_waveform_functions(
        self, statement: Any, wf_func_name: str, waveform_name: Optional[str | Any] = None
    ) -> None:
        """Validate the waveform functions.

        Args:
            statement (Any): The statement that is calling the function.
            wf_func_name (str): The name of the waveform function.
            waveform_name (Optional[str|Any]): The name or index identifier of the waveform.
        """
        # Use a dispatch dictionary to mimic the structure of visit statement
        waveform_validators = {
            "gaussian": lambda: self._waveform_validator.validate_gaussian_sech_waveform(
                statement, "gaussian", waveform_name
            ),
            "sech": lambda: self._waveform_validator.validate_gaussian_sech_waveform(
                statement, "sech", waveform_name
            ),
            "gaussian_square": lambda: self._waveform_validator.validate_gaussian_square_waveform(
                statement, waveform_name
            ),
            "drag": lambda: self._waveform_validator.validate_drag_waveform(
                statement, waveform_name
            ),
            "constant": lambda: self._waveform_validator.validate_constant_waveform(
                statement, waveform_name
            ),
            "sine": lambda: self._waveform_validator.validate_sine_waveform(
                statement, waveform_name
            ),
            "mix": lambda: self._waveform_validator.validate_mix_sum_waveform(
                statement, "mix", waveform_name
            ),
            "sum": lambda: self._waveform_validator.validate_mix_sum_waveform(
                statement, "sum", waveform_name
            ),
            "phase_shift": lambda: self._waveform_validator.validate_phase_shift_waveform(
                statement, waveform_name
            ),
            "scale": lambda: self._waveform_validator.validate_scale_waveform(
                statement, waveform_name
            ),
            "capture_v3": lambda: self._waveform_validator.validate_capture_v3_and_v4_waveform(
                statement, waveform_name
            ),
            "capture_v4": lambda: self._waveform_validator.validate_capture_v3_and_v4_waveform(
                statement, waveform_name
            ),
            "capture_v1": lambda: self._waveform_validator.validate_capture_v1_v2_waveform(
                statement, waveform_name
            ),
            "capture_v2": lambda: self._waveform_validator.validate_capture_v1_v2_waveform(
                statement, waveform_name
            ),
        }

        waveform_validators[wf_func_name]()

    def _handle_scope_sync(
        self, statement: Any, return_value: Any = None, is_assignment: bool = False
    ) -> None:
        """Handle synchronization between QASM and OpenPulse scopes.

        Args:
            statement: The statement being processed
            return_value: Return value from function calls
            is_assignment: True if this is an assignment, False if declaration
        """
        qasm_scope = self._qasm3_scope_manager.get_curr_scope()
        if not qasm_scope:
            return

        pulse_scope = self._openpulse_scope_manager.get_global_scope()
        var_name, var_obj = list(qasm_scope.items())[-1]
        if not isinstance(var_obj, Variable):
            return
        # Check scope conflicts based on operation type
        if is_assignment:
            # For assignment: variable must exist in pulse scope
            if var_name not in pulse_scope:
                raise_qasm3_error(
                    f"Variable '{var_name}' not declared in OpenPulse scope",
                    error_node=statement,
                    span=statement.span,
                )
            # Update existing variable
            var_obj.value = return_value if return_value is not None else var_obj.value
            self._openpulse_scope_manager.update_var_in_scope(var_obj)
        else:
            # For declaration: variable must NOT exist in pulse scope
            if var_name in pulse_scope:
                raise_qasm3_error(
                    f"Variable '{var_name}' already declared in OpenPulse scope",
                    error_node=statement,
                    span=statement.span,
                )
            # Add new variable
            var_obj.value = return_value if return_value is not None else var_obj.value
            self._openpulse_scope_manager.add_var_in_scope(var_obj)

    def _visit_barrier(self, barrier: qasm3_ast.QuantumBarrier) -> list[qasm3_ast.QuantumBarrier]:
        """Visit a barrier statement element.

        Args:
            statement (qasm3_ast.QuantumBarrier): The barrier statement to visit.

        Returns:
            None
        """
        if barrier.qubits:
            for qubit in barrier.qubits:
                if isinstance(qubit, qasm3_ast.Identifier):
                    frame = self._openpulse_scope_manager.get_from_global_scope(qubit.name)
                    if frame is None:
                        raise_qasm3_error(
                            f"Frame '{qubit.name}' not found in openpulse scope",
                            error_node=barrier,
                            span=barrier.span,
                        )
                    frame.time = self._current_block_time

        return [barrier]

    def _visit_classical_assignment(  # pylint: disable=too-many-branches
        self, statement: qasm3_ast.ClassicalAssignment
    ) -> list[qasm3_ast.Statement]:
        """Visit a classical assignment element.

        Args:
            statement (ClassicalAssignment): The classical assignment to visit.
        """
        r_value = statement.rvalue
        l_value = statement.lvalue
        if isinstance(l_value, qasm3_ast.Identifier):
            arg_obj = self._get_identifier(statement, l_value)
            lvar_name = l_value.name
        if isinstance(l_value, qasm3_ast.IndexedIdentifier):
            arg_obj = self._get_identifier(statement, l_value.name)
            lvar_name = l_value.name.name
            assert isinstance(l_value.indices[0], list)
            bit_id = Qasm3ExprEvaluator.evaluate_expression(l_value.indices[0][0])[0]
            lvar_name = f"{lvar_name}[{bit_id}]"

        return_value = None
        if isinstance(r_value, qasm3_ast.FunctionCall):
            f_name = r_value.name.name
            if f_name in ["get_phase", "get_frequency"]:
                self._frame_validator.validate_get_phase_freq_type(
                    r_value, f_name, arg_obj.base_type
                )
                return_value, _ = self._visit_function_call(r_value)
                statement.rvalue = return_value if return_value is not None else statement.rvalue
            elif f_name in OPENPULSE_WAVEFORM_FUNCTION_MAP:
                if not isinstance(arg_obj, Waveform):
                    raise_qasm3_error(
                        f"Invalid return type '{type(arg_obj.base_type).__name__}' "
                        f"for function '{f_name}'",
                        error_node=statement,
                        span=statement.span,
                    )
                self._check_waveform_functions(statement.rvalue, f_name, lvar_name)
            elif f_name in ["newframe"]:
                if not isinstance(arg_obj, Frame):
                    raise_qasm3_error(
                        f"Invalid return type '{type(arg_obj).__name__}' "
                        f"for function '{f_name}'",
                        error_node=statement,
                        span=statement.span,
                    )
                (
                    port_name,
                    freq_arg_value,
                    freq_arg_type,
                    phase_arg_value,
                    phase_arg_type,
                    time_arg_value,
                ), _ = self._visit_function_call(r_value)

                if len(r_value.arguments) == 3:
                    r_value.arguments.insert(3, time_arg_value)  # type: ignore

                self._update_current_block_time(time_arg_value.value)

                self._openpulse_scope_manager.update_var_in_scope(
                    Frame(
                        name=lvar_name,
                        port=port_name,
                        frequency=freq_arg_value,
                        frequency_type=freq_arg_type,
                        phase=phase_arg_value,
                        phase_type=phase_arg_type,
                        time=time_arg_value,
                    )
                )

                if not self._qasm_visitor._check_only:
                    r_value.arguments[1] = qasm3_ast.FloatLiteral(freq_arg_value)  # type: ignore
                    r_value.arguments[2] = qasm3_ast.FloatLiteral(phase_arg_value)  # type: ignore
                    r_value.arguments[3] = self._current_block_time  # type: ignore
            elif f_name in OPENPULSE_CAPTURE_FUNCTION_MAP:
                PulseValidator.validate_capture_function_return_type(
                    r_value, f_name, arg_obj.base_type
                )
                if f_name == "capture_v2" and isinstance(l_value, qasm3_ast.IndexedIdentifier):
                    self._openpulse_scope_manager.add_var_in_scope(
                        Capture(name=lvar_name, frame=None)
                    )
                self._check_waveform_functions(statement.rvalue, f_name, lvar_name)
            elif f_name in FUNCTION_MAP:
                self._qasm_visitor.visit_statement(statement)
        else:
            self._qasm_visitor._visit_classical_assignment(statement)
        self._handle_scope_sync(statement, return_value, True)

        return [statement]

    def _visit_classical_declaration(  # pylint: disable=too-many-branches, too-many-statements, too-many-locals
        self, statement: qasm3_ast.ClassicalDeclaration
    ) -> list[qasm3_ast.Statement]:
        """Visit a classical operation element.

        Args:
            statement (ClassicalType): The classical operation to visit.

        Returns:
            None
        """
        from openpulse.ast import (  # pylint: disable=import-outside-toplevel
            FrameType,
            PortType,
            WaveformType,
        )

        if isinstance(statement.type, PortType):
            if statement.identifier:
                _port_name = statement.identifier.name
                self._check_identifier(statement, statement.identifier)
                self._openpulse_scope_manager.add_var_in_scope(
                    Variable(
                        name=_port_name,
                        value=None,
                        base_type=PortType(),
                        base_size=1,
                    )
                )

        elif isinstance(statement.type, FrameType):
            _frame_name = ""
            if statement.identifier:
                _frame_name = statement.identifier.name
                self._check_identifier(statement, statement.identifier)

            if isinstance(statement.init_expression, qasm3_ast.FunctionCall):
                (
                    port_name,
                    freq_arg_value,
                    freq_arg_type,
                    phase_arg_value,
                    phase_arg_type,
                    time_arg_value,
                ), _ = self._visit_function_call(statement.init_expression)

                if len(statement.init_expression.arguments) == 3:
                    statement.init_expression.arguments.insert(3, time_arg_value)  # type: ignore

                self._current_block_time = qasm3_ast.DurationLiteral(
                    self._current_block_time.value + time_arg_value.value,
                    unit=self._current_block_time.unit,
                )

                frame_var = Frame(
                    name=_frame_name,
                    port=port_name,
                    frequency=freq_arg_value,
                    frequency_type=freq_arg_type,
                    phase=phase_arg_value,
                    phase_type=phase_arg_type,
                    time=self._current_block_time,
                )
                self._openpulse_scope_manager.add_var_in_scope(frame_var)

                if not self._qasm_visitor._check_only:
                    statement.init_expression.arguments[1] = qasm3_ast.FloatLiteral(
                        freq_arg_value
                    )  # type: ignore
                    statement.init_expression.arguments[2] = qasm3_ast.FloatLiteral(
                        phase_arg_value
                    )  # type: ignore
                    statement.init_expression.arguments[3] = (
                        self._current_block_time
                    )  # type: ignore
            else:
                self._openpulse_scope_manager.add_var_in_scope(
                    Frame(
                        name=_frame_name,
                        port=None,
                        frequency=0.0,
                        phase=0.0,
                        time=qasm3_ast.DurationLiteral(0.0, unit=qasm3_ast.TimeUnit.ns),
                    )
                )

        # Full waveform implementation is yet to be done by openpulse
        elif isinstance(statement.type, WaveformType):
            _waveform_name = None
            if isinstance(statement.identifier, qasm3_ast.Identifier):
                _waveform_name = statement.identifier.name
                self._check_identifier(statement, statement.identifier)

            if statement.init_expression:
                if isinstance(statement.init_expression, qasm3_ast.FunctionCall):
                    wf_func_name = statement.init_expression.name.name
                    if wf_func_name not in OPENPULSE_WAVEFORM_FUNCTION_MAP:
                        raise_qasm3_error(
                            f"Invalid waveform function '{wf_func_name}'",
                            error_node=statement,
                            span=statement.span,
                        )
                    if not self._openpulse_scope_manager.check_in_scope(_waveform_name):
                        self._openpulse_scope_manager.add_var_in_scope(
                            Waveform(
                                name=_waveform_name,
                                amplitude=None,
                                total_duration=qasm3_ast.DurationLiteral(
                                    0.0, unit=qasm3_ast.TimeUnit.ns
                                ),
                            )
                        )
                    self._check_waveform_functions(
                        statement.init_expression, wf_func_name, _waveform_name
                    )
                    # TODO: _waveforms should store return value of waveform functions,
                    # but current functions are not supported by openpulse

        elif statement.init_expression:
            return_value = None
            if isinstance(statement.init_expression, qasm3_ast.FunctionCall):
                f_name = statement.init_expression.name.name
                _id = statement.identifier
                _type = statement.type
                if f_name in ["get_phase", "get_frequency"]:
                    self._frame_validator.validate_get_phase_freq_type(statement, f_name, _id)
                    return_value, _ = self._visit_function_call(statement.init_expression)
                if f_name in OPENPULSE_CAPTURE_FUNCTION_MAP:
                    self._openpulse_scope_manager.add_var_in_scope(
                        Capture(name=_id.name, frame=None)
                    )
                    PulseValidator.validate_capture_function_return_type(
                        statement.init_expression, f_name, _type
                    )
                    self._check_waveform_functions(statement.init_expression, f_name, _id.name)
                if f_name in FUNCTION_MAP:
                    self._qasm_visitor.visit_statement(statement)
                statement.init_expression = (
                    return_value if return_value is not None else statement.init_expression
                )
            else:
                self._qasm_visitor.visit_statement(statement)
            self._handle_scope_sync(statement, return_value, False)
        else:
            self._qasm_visitor.visit_statement(statement)
            self._handle_scope_sync(statement, None, False)

        return [statement]

    def _visit_function_call(  # pylint: disable=too-many-branches, too-many-statements
        self, statement: qasm3_ast.FunctionCall
    ) -> tuple[Any, list[qasm3_ast.Statement | qasm3_ast.FunctionCall]]:
        """Visit a function call element.

        Args:
            statement (qasm3_ast.FunctionCall): The function call to visit.
        Returns:
            None

        """
        # evaluate expressions to get name
        _return_value: Any = None
        function_name = statement.name.name
        stmt_args = statement.arguments
        PulseValidator.validate_openpulse_func_arg_length(statement, function_name, len(stmt_args))

        frame_manipulators = {
            "set_phase": lambda args: self._set_shift_phase(
                statement, args[0].name, args[1], set_phase=True
            ),
            "shift_phase": lambda args: self._set_shift_phase(
                statement,
                args[0].name,
                (
                    qasm3_ast.FloatLiteral(Qasm3ExprEvaluator.evaluate_expression(args[1])[0])
                    if not isinstance(args[1], qasm3_ast.Identifier)
                    else args[1]
                ),
                shift_phase=True,
            ),
            "set_frequency": lambda args: self._set_shift_frequency(
                statement, args[0].name, args[1], set_frequency=True
            ),
            "shift_frequency": lambda args: self._set_shift_frequency(
                statement, args[0].name, args[1], shift_frequency=True
            ),
        }

        if function_name in (*OPENPULSE_FRAME_FUNCTION_MAP, "get_phase", "get_frequency"):
            frame_arg = stmt_args[0]
            if isinstance(frame_arg, qasm3_ast.Identifier):
                if function_name in ["get_phase", "get_frequency"]:
                    _return_value = self._get_phase_frequency(
                        statement,
                        frame_arg.name,
                        get_phase=function_name == "get_phase",
                        get_frequency=function_name == "get_frequency",
                    )
                else:
                    frame_manipulators[function_name](stmt_args)
            else:
                raise_qasm3_error(
                    f"Invalid frame argument '{frame_arg}' in {function_name} function",
                    error_node=statement,
                    span=statement.span,
                )

        if function_name == "newframe":
            if self._is_def_cal and not self._module._frame_in_def_cal:
                raise_qasm3_error(
                    "Frame initialization in defcal block is not allowed",
                    error_node=statement,
                    span=statement.span,
                )
            time_unit = (
                qasm3_ast.TimeUnit.dt if self._module._device_cycle_time else qasm3_ast.TimeUnit.ns
            )
            _return_value = self._frame_validator.validate_newframe_arguments(
                statement, stmt_args, time_unit
            )

        if statement.name.name == "play":
            if not self._is_def_cal and not self._module._play_in_cal:
                raise_qasm3_error(
                    "Play function is only allowed in defcal block",
                    error_node=statement,
                    span=statement.span,
                )

            frame_obj, waveform_duration = self._play_validator._handle_play_function(
                statement, stmt_args
            )
            self._update_frame_time(
                statement, frame_obj.name, waveform_duration.total_duration.value
            )
            # implicit phase tracking
            if self._module._implicit_phase_tracking:
                _curr_freq = self._get_phase_frequency(
                    statement, frame_arg.name, get_frequency=True  # type: ignore
                )
                self._set_shift_phase(
                    statement,
                    frame_arg.name,  # type: ignore
                    2
                    * CONSTANTS_MAP["pi"]
                    * _curr_freq.value  # type: ignore
                    * (
                        waveform_duration.value
                        * (
                            TIME_UNITS_MAP["ns"]["s"]
                            if not self._module.device_cycle_time
                            else self._module.device_cycle_time
                        )
                    ),
                )

        if statement.name.name in ["capture_v1", "capture_v2"]:
            self._check_waveform_functions(statement, statement.name.name)

        if statement.name.name in ["capture_v3", "capture_v4"]:
            self._check_waveform_functions(statement, statement.name.name)

        if self._check_only:
            return _return_value, []

        statement = qasm3_ast.ExpressionStatement(expression=statement)  # type: ignore

        return _return_value, [statement]

    def visit_statement(self, statement: qasm3_ast.Statement) -> list[qasm3_ast.Statement]:
        """Visit a statement element.

        Args:
            statement (qasm3_ast.Statement): The statement to visit.

        Returns:
            None
        """
        logger.debug("Visiting statement '%s'", str(statement))
        result = []
        visit_map = {
            qasm3_ast.QuantumBarrier: self._visit_barrier,
            qasm3_ast.ClassicalDeclaration: self._visit_classical_declaration,
            qasm3_ast.ExpressionStatement: lambda x: self._visit_function_call(x.expression),
            qasm3_ast.DelayInstruction: self._qasm_visitor._visit_delay_statement,
            qasm3_ast.ClassicalAssignment: self._visit_classical_assignment,
            qasm3_ast.ConstantDeclaration: self._visit_classical_declaration,
        }

        visitor_function = visit_map.get(type(statement))

        if visitor_function:
            if isinstance(statement, qasm3_ast.ExpressionStatement):
                # these return a tuple of return value and list of statements
                _, ret_stmts = visitor_function(statement)  # type: ignore[operator]
                result.extend(ret_stmts)
            else:
                result.extend(visitor_function(statement))  # type: ignore[operator]
        else:
            if isinstance(statement, qasm3_ast.ReturnStatement):
                if statement.expression:
                    if isinstance(statement.expression, qasm3_ast.Identifier):
                        if (
                            not statement.expression.name
                            in self._openpulse_scope_manager.get_curr_scope()
                        ):
                            raise_qasm3_error(
                                f"Return Variable '{statement.expression.name}' not "
                                "declared in OpenPulse scope",
                                error_node=statement,
                                span=statement.span,
                            )
                        result.append(statement)
            else:
                raise_qasm3_error(
                    f"Unsupported statement of type {type(statement)}",
                    error_node=statement,
                    span=statement.span,
                )
        return result

    def visit_basic_block(
        self,
        stmt_list: list[qasm3_ast.Statement],
        is_def_cal: bool,
    ) -> list[qasm3_ast.Statement]:
        """Visit a basic block of statements.

        Args:
            stmt_list (list[qasm3_ast.Statement]): The list of statements to visit.
            is_def_cal (bool): is the given statements from def_cal block.

        Returns:
            list[qasm3_ast.Statement]: The list of unrolled statements.
        """
        result = []
        self._is_def_cal = is_def_cal
        for stmt in stmt_list:
            result.extend(self.visit_statement(stmt))
        return result
