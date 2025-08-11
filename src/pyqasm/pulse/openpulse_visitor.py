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

import openpulse.ast as pulse_ast
import openqasm3.ast as qasm3_ast

from pyqasm.elements import Frame, Variable, Waveform
from pyqasm.exceptions import (
    raise_qasm3_error,
)
from pyqasm.expressions import Qasm3ExprEvaluator
from pyqasm.maps.expressions import (
    CONSTANTS_MAP,
    OPENPULSE_CAPTURE_FUNCTION_MAP,
    OPENPULSE_WAVEFORM_FUNCTION_MAP,
    TIME_UNITS_MAP,
)
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
        self._frames: dict[str, Frame] = {}
        self._ports_usage: dict[str, int] = {}  # should be given by user
        self._port_to_qubit_map: dict[str, list[int]] = {}
        self._waveforms: dict[str, Waveform] = {}
        self._is_def_cal: bool = False
        self._frame_in_def_cal: bool = True  # yet to be implemented
        self._frame_limit_per_port: int = 5  # yet to be implemented
        self._implicit_phase_tracking: bool = False  # yet to be implemented
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
        if frame_obj is None:
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

    def _get_identifier(
        self, statement: Any, identifier: pulse_ast.Identifier
    ) -> tuple[Any, Any, Any]:
        """Get the value of an identifier.

        Args:
            identifier (pulse_ast.Identifier): The identifier to get the value of.
            statement (Any): The statement that is calling the function.
        """
        _id_var_obj = self._openpulse_scope_manager.get_from_visible_scope(
            identifier.name
        ) or self._qasm3_scope_manager.get_from_global_scope(identifier.name)
        if _id_var_obj is None:
            raise_qasm3_error(
                f"Identifier '{identifier.name}' not declared",
                error_node=statement,
                span=statement.span,
            )
        return _id_var_obj.value, _id_var_obj.base_type, _id_var_obj.base_size

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
            _phase_value, _base_type, _base_size = self._get_identifier(statement, phase)
            if (
                not isinstance(frame_obj.phase_type, type(_base_type))
                or _base_size != frame_obj.phase_type.size
            ):
                raise_qasm3_error(
                    f"Phase argument '{phase.name}' must be a AngleType "
                    f"with same size in frame '{frame}'",
                    error_node=statement,
                    span=statement.span,
                )
            if set_phase:
                frame_obj.phase = _phase_value
            if shift_phase:
                frame_obj.phase = (frame_obj.phase + _phase_value) % (2 * CONSTANTS_MAP["pi"])
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
            _freq_value, _base_type, _base_size = self._get_identifier(statement, frequency)
            if (
                not isinstance(frame_obj.frequency_type, type(_base_type))
                or _base_size != frame_obj.frequency_type.size
            ):
                raise_qasm3_error(
                    f"Frequency argument '{frequency.name}' must be a "
                    f"FloatType with same size in frame '{frame}'",
                    error_node=statement,
                    span=statement.span,
                )
            if set_frequency:
                frame_obj.frequency = _freq_value
            if shift_frequency:
                frame_obj.frequency += _freq_value
        elif isinstance(frequency, qasm3_ast.FloatLiteral):
            if set_frequency:
                frame_obj.frequency = frequency.value
            if shift_frequency:
                frame_obj.frequency += frequency.value
        else:
            raise_qasm3_error(
                f"Invalid frequency argument '{frequency}' in "
                f"{"set_frequency" if set_frequency else "shift_frequency"} function",
                error_node=statement,
                span=statement.span,
            )
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

    def _validate_frame_manipulators(self, statement: Any, name: str, no_of_args: int) -> None:
        """Validate the frame manipulators.

        Args:
            statement (Any): The statement that is calling the function.
            name (str): The name of the function.
            no_of_args (int): The number of arguments of the function.
        """
        if (
            name in ["set_phase", "shift_phase", "set_frequency", "shift_frequency"]
            and no_of_args != 2
        ):
            raise_qasm3_error(
                f"Invalid number of arguments for {name} function",
                error_node=statement,
                span=statement.span,
            )
        if name in ["get_phase", "get_frequency"] and no_of_args != 1:
            raise_qasm3_error(
                f"Invalid number of arguments for {name} function",
                error_node=statement,
                span=statement.span,
            )

    def _check_waveform_functions(
        self, statement: Any, wf_func_name: str, waveform_name: Optional[str] = None
    ) -> None:
        """Validate the waveform functions.

        Args:
            statement (Any): The statement that is calling the function.
            wf_func_name (str): The name of the waveform function.
            waveform_name (Optional[str]): The name of the waveform.
        """
        if wf_func_name in ("gaussian", "sech"):
            self._waveform_validator.validate_gaussian_sech_waveform(
                statement, wf_func_name, self._waveforms, waveform_name
            )

        if wf_func_name == "gaussian_square":
            self._waveform_validator.validate_gaussian_square_waveform(
                statement, self._waveforms, waveform_name
            )

        if wf_func_name == "drag":
            self._waveform_validator.validate_drag_waveform(
                statement, self._waveforms, waveform_name
            )

        if wf_func_name == "constant":
            self._waveform_validator.validate_constant_waveform(
                statement, self._waveforms, waveform_name
            )

        if wf_func_name == "sine":
            self._waveform_validator.validate_sine_waveform(
                statement, self._waveforms, waveform_name
            )

        if wf_func_name in ("mix", "sum"):
            self._waveform_validator.validate_mix_sum_waveform(
                statement, wf_func_name, self._waveforms, waveform_name
            )

        if wf_func_name == "phase_shift":
            self._waveform_validator.validate_phase_shift_waveform(
                statement, self._waveforms, waveform_name
            )

        if wf_func_name == "scale":
            self._waveform_validator.validate_scale_waveform(
                statement, self._waveforms, waveform_name
            )

        if wf_func_name == "capture_v3":
            self._waveform_validator.validate_capture_v3_and_v4_waveform(statement)

    def _visit_barrier(self, barrier: pulse_ast.QuantumBarrier) -> list[pulse_ast.QuantumBarrier]:
        """Visit a barrier statement element.

        Args:
            statement (pulse_ast.QuantumBarrier): The barrier statement to visit.

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

    def _visit_classical_assignment(
        self, statement: pulse_ast.ClassicalAssignment
    ) -> list[pulse_ast.Statement]:
        """Visit a classical assignment element.

        Args:
            statement (ClassicalAssignment): The classical assignment to visit.
        """
        r_value = statement.rvalue
        l_value = statement.lvalue
        if isinstance(r_value, pulse_ast.FunctionCall):
            f_name = r_value.name.name
            return_value, _ = self._visit_function_call(r_value)
            _id = l_value.identifier  # type: ignore
            _, _type, _ = self._get_identifier(statement, _id)
            if _type:
                self._qasm_visitor.visit_statement(statement)
            if _type is not None:
                if (f_name in ["get_phase"] and not isinstance(_type, pulse_ast.AngleType)) or (
                    f_name in ["get_frequency"] and not isinstance(_type, pulse_ast.FloatType)
                ):
                    raise_qasm3_error(
                        f"Invalid type '{_type}' for identifier '{_id.name}'",
                        error_node=r_value,
                        span=r_value.span,
                    )
            statement.rvalue = return_value if return_value is not None else statement.rvalue
        else:
            self._qasm_visitor.visit_statement(statement)

        return [statement]

    def _visit_classical_declaration(  # pylint: disable=too-many-branches, too-many-statements, too-many-locals
        self, statement: pulse_ast.ClassicalDeclaration
    ) -> list[pulse_ast.Statement]:
        """Visit a classical operation element.

        Args:
            statement (ClassicalType): The classical operation to visit.

        Returns:
            None
        """

        if isinstance(statement.type, pulse_ast.PortType):
            if statement.identifier:
                _port_name = statement.identifier.name
                if _port_name in self._port_to_qubit_map:
                    raise_qasm3_error(
                        f"Port '{_port_name}' already declared",
                        error_node=statement,
                        span=statement.span,
                    )
                self._port_to_qubit_map[_port_name] = []

        elif isinstance(statement.type, pulse_ast.FrameType):
            _frame_name = ""
            freq_arg_value = 0.0
            freq_arg_type = qasm3_ast.FloatType(qasm3_ast.IntegerLiteral(32))
            phase_arg_value = 0.0
            phase_arg_type = qasm3_ast.AngleType(qasm3_ast.IntegerLiteral(32))
            time_arg_value = qasm3_ast.DurationLiteral(
                0,
                unit=(
                    qasm3_ast.TimeUnit.dt
                    if self._module._device_cycle_time
                    else qasm3_ast.TimeUnit.ns
                ),
            )
            if statement.identifier:
                _frame_name = statement.identifier.name
                if _frame_name in self._frames:
                    raise_qasm3_error(
                        f"Frame '{_frame_name}' already declared",
                        error_node=statement,
                        span=statement.span,
                    )

            if statement.init_expression:
                _frame_args = statement.init_expression.arguments  # type: ignore
                if not 3 <= len(_frame_args) <= 4:
                    raise_qasm3_error(
                        f"Invalid number of arguments for frame '{_frame_name}'",
                        error_node=statement,
                        span=statement.span,
                    )

                new_frame = statement.init_expression.name.name  # type: ignore
                if new_frame is None or new_frame != "newframe":
                    raise_qasm3_error(
                        f"Invalid frame initialization function '{new_frame}'",
                        error_node=statement,
                        span=statement.span,
                    )

                _port_arg = _frame_args[0]
                if not isinstance(_port_arg, pulse_ast.Identifier):
                    raise_qasm3_error(
                        f"Invalid port argument '{_port_arg}' in frame '{_frame_name}'",
                        error_node=statement,
                        span=statement.span,
                    )
                else:
                    if _port_arg.name not in self._port_to_qubit_map:
                        raise_qasm3_error(
                            f"Port '{_port_arg.name}' not declared",
                            error_node=statement,
                            span=statement.span,
                        )
                self._ports_usage[_port_arg.name] = self._ports_usage.get(_port_arg.name, 0) + 1
                if self._ports_usage[_port_arg.name] > self._frame_limit_per_port:
                    raise_qasm3_error(
                        f"Port '{_port_arg.name}' has exceeded the frame "
                        f"limit of {self._frame_limit_per_port}",
                        error_node=statement,
                        span=statement.span,
                    )
                freq_arg = _frame_args[1]
                if isinstance(freq_arg, pulse_ast.Identifier):
                    _id_freq_var_obj = self._qasm3_scope_manager.get_from_visible_scope(
                        freq_arg.name
                    )
                    if _id_freq_var_obj is None:
                        new_var_obj = Variable(
                            name=freq_arg.name,
                            value=None,
                            base_type=qasm3_ast.FloatType(qasm3_ast.IntegerLiteral(32)),
                            base_size=32,
                            is_constant=True,
                        )
                        self._openpulse_scope_manager.add_var_in_scope(new_var_obj)
                        _id_freq_var_obj = new_var_obj

                    if not _id_freq_var_obj.is_constant or not isinstance(
                        _id_freq_var_obj.base_type, qasm3_ast.FloatType
                    ):
                        raise_qasm3_error(
                            f"Frequency argument '{freq_arg.name}' must be a constant float",
                            error_node=statement,
                            span=statement.span,
                        )
                    freq_arg_value = _id_freq_var_obj.value
                    freq_arg_type = _id_freq_var_obj.base_type
                    freq_arg_type.size = _id_freq_var_obj.base_size
                elif isinstance(freq_arg, pulse_ast.FloatLiteral):
                    freq_arg_value = freq_arg.value
                else:
                    raise_qasm3_error(
                        f"Invalid frequency argument '{freq_arg}' in frame '{_frame_name}'",
                        error_node=statement,
                        span=statement.span,
                    )

                phase_arg = _frame_args[2]
                if isinstance(phase_arg, pulse_ast.Identifier):
                    if phase_arg.name in CONSTANTS_MAP:
                        phase_arg_value = CONSTANTS_MAP[phase_arg.name]
                    else:
                        _id_phase_var_obj = self._qasm3_scope_manager.get_from_visible_scope(
                            phase_arg.name
                        )
                        if (
                            _id_phase_var_obj is None
                            or not _id_phase_var_obj.is_constant
                            or not isinstance(_id_phase_var_obj.base_type, qasm3_ast.AngleType)
                        ):
                            raise_qasm3_error(
                                f"Phase argument '{phase_arg.name}' must be a constant Angle",
                                error_node=statement,
                                span=statement.span,
                            )
                        phase_arg_value = _id_phase_var_obj.value
                        phase_arg_type = _id_phase_var_obj.base_type
                        phase_arg_type.size = _id_phase_var_obj.base_size
                elif isinstance(
                    phase_arg,
                    (pulse_ast.BinaryExpression, pulse_ast.UnaryExpression, qasm3_ast.FloatLiteral),
                ):
                    phase_arg_value, _ = Qasm3ExprEvaluator.evaluate_expression(phase_arg)
                else:
                    raise_qasm3_error(
                        f"Invalid Phase argument '{freq_arg}' in frame '{_frame_name}'",
                        error_node=statement,
                        span=statement.span,
                    )

                if len(_frame_args) == 4:
                    time_arg = _frame_args[3]
                    if isinstance(time_arg, pulse_ast.Identifier):
                        _id_dur_var_obj = self._qasm3_scope_manager.get_from_visible_scope(
                            time_arg.name
                        )
                        if (
                            _id_dur_var_obj is None
                            or not _id_dur_var_obj.is_constant
                            or not isinstance(_id_dur_var_obj.base_type, qasm3_ast.DurationType)
                        ):
                            raise_qasm3_error(
                                f"Time argument '{time_arg.name}' must be a constant Duration",
                                error_node=statement,
                                span=statement.span,
                            )
                        time_arg_value = qasm3_ast.DurationLiteral(
                            _id_dur_var_obj.value,
                            unit=(
                                qasm3_ast.TimeUnit.dt
                                if self._module._device_cycle_time
                                else qasm3_ast.TimeUnit.ns
                            ),
                        )
                    elif isinstance(time_arg, qasm3_ast.DurationLiteral):
                        time_arg_value = qasm3_ast.DurationLiteral(
                            time_arg.value,
                            unit=time_arg.unit,
                        )
                    elif isinstance(time_arg, qasm3_ast.IntegerLiteral) and time_arg.value == 0:
                        time_arg_value = qasm3_ast.DurationLiteral(
                            0,
                            unit=(
                                qasm3_ast.TimeUnit.dt
                                if self._module._device_cycle_time
                                else qasm3_ast.TimeUnit.ns
                            ),
                        )
                    else:
                        raise_qasm3_error(
                            f"Invalid Time argument '{time_arg}' in frame '{_frame_name}'",
                            error_node=statement,
                            span=statement.span,
                        )
                if len(_frame_args) == 3:
                    statement.init_expression.arguments.insert(3, time_arg_value)  # type: ignore
                self._current_block_time = qasm3_ast.DurationLiteral(
                    self._current_block_time.value + time_arg_value.value,
                    unit=self._current_block_time.unit,
                )
                if not self._qasm_visitor._check_only:
                    statement.init_expression.arguments[3] = (  # type: ignore
                        self._current_block_time
                    )

                frame_obj = Frame(
                    name=_frame_name,
                    port=_port_arg.name,
                    frequency=freq_arg_value,
                    frequency_type=freq_arg_type,
                    phase=phase_arg_value,
                    phase_type=phase_arg_type,
                    time=time_arg_value,
                )
                self._openpulse_scope_manager.add_frame_in_scope(frame_obj)
                self._frames[_frame_name] = frame_obj

                if not self._qasm_visitor._check_only and freq_arg_value is not None:
                    statement.init_expression.arguments[1] = qasm3_ast.FloatLiteral(  # type: ignore
                        freq_arg_value
                    )
                    statement.init_expression.arguments[2] = qasm3_ast.FloatLiteral(  # type: ignore
                        phase_arg_value
                    )

        # Full waveform implementation is yet to be done by openpulse
        elif isinstance(statement.type, pulse_ast.WaveformType):
            _waveform_name = None
            if statement.identifier:
                _waveform_name = statement.identifier.name
                if _waveform_name in self._waveforms:
                    raise_qasm3_error(
                        f"Waveform '{_waveform_name}' already declared.",
                        error_node=statement,
                        span=statement.span,
                    )
            else:
                raise_qasm3_error(
                    f"Invalid waveform declaration '{_waveform_name}'",
                    error_node=statement,
                    span=statement.span,
                )

            if statement.init_expression:
                if isinstance(statement.init_expression, pulse_ast.FunctionCall):
                    wf_func_name = statement.init_expression.name.name
                    if wf_func_name not in OPENPULSE_WAVEFORM_FUNCTION_MAP:
                        raise_qasm3_error(
                            f"Invalid waveform function '{wf_func_name}'",
                            error_node=statement,
                            span=statement.span,
                        )
                    self._check_waveform_functions(
                        statement.init_expression, wf_func_name, _waveform_name
                    )
                    # TODO: _waveforms should store return value of waveform functions,
                    # but current functions are not supported by openpulse

        elif statement.init_expression:
            return_value = None
            if isinstance(statement.init_expression, pulse_ast.FunctionCall):
                f_name = statement.init_expression.name.name
                return_value, _ = self._visit_function_call(statement.init_expression)
                _id = statement.identifier
                _type = statement.type
                if _id or _type:
                    self._qasm_visitor.visit_statement(statement)
                if _type is not None:
                    if (f_name in ["get_phase"] and not isinstance(_type, pulse_ast.AngleType)) or (
                        f_name in ["get_frequency"] and not isinstance(_type, pulse_ast.FloatType)
                    ):
                        raise_qasm3_error(
                            f"Invalid return type '{type(_type).__name__}' for function '{f_name}'",
                            error_node=statement,
                            span=statement.span,
                        )
                    if f_name in OPENPULSE_CAPTURE_FUNCTION_MAP:
                        if f_name == "capture_v1" and not (
                            isinstance(_type, pulse_ast.ComplexType)
                            and isinstance(_type.base_type, qasm3_ast.FloatType)
                            and _type.base_type.size.value == 32  # type: ignore
                        ):
                            raise_qasm3_error(
                                f"Invalid return type '{type(_type).__name__}' "
                                f"for function '{f_name}'",
                                error_node=statement,
                                span=statement.span,
                            )
                        if f_name == "capture_v2" and not (
                            isinstance(statement.type, pulse_ast.BitType)
                        ):
                            raise_qasm3_error(
                                f"Invalid return type '{type(_type).__name__}' "
                                f"for function '{f_name}'",
                                error_node=statement,
                                span=statement.span,
                            )
                        if f_name == "capture_v3" and not (
                            isinstance(_type, pulse_ast.WaveformType)
                        ):
                            raise_qasm3_error(
                                f"Invalid return type '{type(_type).__name__}' "
                                f"for function '{f_name}'",
                                error_node=statement,
                                span=statement.span,
                            )
                        if f_name == "capture_v4" and not isinstance(_type, pulse_ast.IntType):
                            raise_qasm3_error(
                                f"Invalid return type '{type(_type).__name__}' "
                                "for function '{f_name}'",
                                error_node=statement,
                                span=statement.span,
                            )

                statement.init_expression = (
                    return_value if return_value is not None else statement.init_expression
                )
            else:
                self._qasm_visitor.visit_statement(statement)
            qasm_scope = self._qasm3_scope_manager.get_curr_scope()
            pulse_scope = self._openpulse_scope_manager.get_global_scope()
            # Only take the last variable in qasm_scope (if any)
            if qasm_scope:
                var_name, var_value = list(qasm_scope.items())[-1]
                if var_name in pulse_scope:
                    raise_qasm3_error(
                        f"Variable '{var_name}' already declared in OpenPulse scope",
                        error_node=statement,
                        span=statement.span,
                    )
                var_value.value = (
                    return_value.value if return_value is not None else var_value.value
                )
                pulse_scope[var_name] = var_value
        else:
            self._qasm_visitor.visit_statement(statement)
            qasm_scope = self._qasm3_scope_manager.get_curr_scope()
            pulse_scope = self._openpulse_scope_manager.get_global_scope()
            # Only take the last variable in qasm_scope (if any)
            if qasm_scope:
                var_name, var_value = list(qasm_scope.items())[-1]
                if var_name in pulse_scope:
                    raise_qasm3_error(
                        f"Variable '{var_name}' already declared in OpenPulse scope",
                        error_node=statement,
                        span=statement.span,
                    )
                # var_value.value = None
                pulse_scope[var_name] = var_value

        return [statement]

    def _visit_function_call(  # pylint: disable=too-many-branches, too-many-statements
        self, statement: pulse_ast.FunctionCall
    ) -> tuple[Any, list[pulse_ast.Statement | qasm3_ast.FunctionCall]]:
        """Visit a function call element.

        Args:
            statement (pulse_ast.FunctionCall): The function call to visit.
        Returns:
            None

        """
        # evaluate expressions to get name
        # Handle frame manipulation functions
        _return_value = None

        frame_manipulators = {
            "set_phase": lambda args: self._set_shift_phase(
                statement, args[0].name, args[1], set_phase=True
            ),
            "shift_phase": lambda args: self._set_shift_phase(
                statement,
                args[0].name,
                (
                    qasm3_ast.FloatLiteral(Qasm3ExprEvaluator.evaluate_expression(args[1])[0])
                    if not isinstance(args[1], pulse_ast.Identifier)
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

        if statement.name.name in frame_manipulators or statement.name.name in [
            "get_phase",
            "get_frequency",
        ]:
            stmt_args = statement.arguments
            self._validate_frame_manipulators(statement, statement.name.name, len(stmt_args))
            frame_arg = stmt_args[0]
            if isinstance(frame_arg, pulse_ast.Identifier):
                if statement.name.name in ["get_phase", "get_frequency"]:
                    _return_value = self._get_phase_frequency(
                        statement,
                        frame_arg.name,
                        get_phase=statement.name.name == "get_phase",
                        get_frequency=statement.name.name == "get_frequency",
                    )
                else:
                    frame_manipulators[statement.name.name](stmt_args)
            else:
                raise_qasm3_error(
                    f"Invalid frame argument '{frame_arg}' in {statement.name.name} function",
                    error_node=statement,
                    span=statement.span,
                )

        if statement.name.name == "play":
            if not self._is_def_cal:
                raise_qasm3_error(
                    "Play function is only allowed in defcal block",
                    error_node=statement,
                    span=statement.span,
                )
            play_args = statement.arguments
            if len(play_args) != 2:
                raise_qasm3_error(
                    "Invalid number of arguments for play function",
                    error_node=statement,
                    span=statement.span,
                )
            frame_arg = play_args[0]
            waveform_arg = play_args[1]
            waveform_duration = qasm3_ast.DurationLiteral(
                1 * TIME_UNITS_MAP["ns"]["s"], qasm3_ast.TimeUnit.ns
            )
            if isinstance(frame_arg, pulse_ast.Identifier):
                _ = self._get_frame(statement, frame_arg.name)
            else:
                raise_qasm3_error(
                    f"Invalid frame argument '{type(frame_arg).__name__}' in play function",
                    error_node=statement,
                    span=statement.span,
                )

            if isinstance(waveform_arg, pulse_ast.Identifier):
                if waveform_arg.name not in self._waveforms:
                    raise_qasm3_error(
                        f"Waveform '{waveform_arg.name}' not declared",
                        error_node=statement,
                        span=statement.span,
                    )
                waveform_duration = self._waveforms[waveform_arg.name].total_duration
                self._update_frame_time(
                    statement, frame_arg.name, waveform_duration.value  # type: ignore
                )  # type: ignore
            elif isinstance(waveform_arg, pulse_ast.FunctionCall):
                wf_func_name = waveform_arg.name.name
                if wf_func_name not in OPENPULSE_WAVEFORM_FUNCTION_MAP:
                    raise_qasm3_error(
                        f"Invalid waveform function '{wf_func_name}'",
                        error_node=statement,
                        span=statement.span,
                    )
                self._check_waveform_functions(waveform_arg, wf_func_name)
                waveform_duration = self._temp_waveform.total_duration  # type: ignore
                self._update_frame_time(
                    statement, frame_arg.name, waveform_duration.value  # type: ignore
                )
                self._temp_waveform = None
            else:
                raise_qasm3_error(
                    f"Invalid waveform argument '{type(waveform_arg).__name__ }' in play function",
                    error_node=statement,
                    span=statement.span,
                )
            # implicit phase tracking
            if self._implicit_phase_tracking:
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
            capture_args = statement.arguments
            if len(capture_args) != 2:
                raise_qasm3_error(
                    f"Invalid number of arguments for '{statement.name.name}' function",
                    error_node=statement,
                    span=statement.span,
                )
            frame_arg = capture_args[0]
            if isinstance(frame_arg, pulse_ast.Identifier):
                _ = self._get_frame(statement, frame_arg.name)
            else:
                raise_qasm3_error(
                    f"Invalid frame argument '{type(frame_arg).__name__}' "
                    f"in '{statement.name.name}' function",
                    error_node=statement,
                    span=statement.span,
                )
            waveform_arg = capture_args[1]
            if isinstance(waveform_arg, pulse_ast.Identifier):
                if waveform_arg.name not in self._waveforms:
                    raise_qasm3_error(
                        f"Waveform '{waveform_arg.name}' not declared",
                        error_node=statement,
                        span=statement.span,
                    )
            else:
                raise_qasm3_error(
                    f"Invalid waveform argument '{type(waveform_arg).__name__}' "
                    f"in '{statement.name.name}' function",
                    error_node=statement,
                    span=statement.span,
                )

        if statement.name.name in ["capture_v3", "capture_v4"]:
            capture_args = statement.arguments
            if len(capture_args) != 2:
                raise_qasm3_error(
                    f"Invalid number of arguments for '{statement.name.name}' function",
                    error_node=statement,
                    span=statement.span,
                )
            self._waveform_validator.validate_capture_v3_and_v4_waveform(statement)

        if self._check_only:
            return _return_value, []

        statement = qasm3_ast.ExpressionStatement(expression=statement)  # type: ignore

        return _return_value, [statement]

    def _visit_delay_instruction(
        self, statement: pulse_ast.DelayInstruction
    ) -> list[pulse_ast.Statement]:
        """Visit a delay instruction statement.

        Args:
            statement (pulse_ast.DelayInstruction): The delay instruction statement to visit.
        Returns:
            None
        """
        self._qasm_visitor.visit_statement(statement)
        # implicit phase tracking

        return [statement]

    def visit_statement(self, statement: pulse_ast.Statement) -> list[pulse_ast.Statement]:
        """Visit a statement element.

        Args:
            statement (pulse_ast.Statement): The statement to visit.

        Returns:
            None
        """
        logger.debug("Visiting statement '%s'", str(statement))
        result = []
        visit_map = {
            pulse_ast.QuantumBarrier: self._visit_barrier,
            pulse_ast.ClassicalDeclaration: self._visit_classical_declaration,
            pulse_ast.ExpressionStatement: lambda x: self._visit_function_call(x.expression),
            pulse_ast.DelayInstruction: self._visit_delay_instruction,
            pulse_ast.ClassicalAssignment: self._visit_classical_assignment,
            pulse_ast.ConstantDeclaration: self._visit_classical_declaration,
        }

        visitor_function = visit_map.get(type(statement))

        if visitor_function:
            if isinstance(statement, pulse_ast.ExpressionStatement):
                # these return a tuple of return value and list of statements
                _, ret_stmts = visitor_function(statement)  # type: ignore[operator]
                result.extend(ret_stmts)
            else:
                result.extend(visitor_function(statement))  # type: ignore[operator]
        else:
            raise_qasm3_error(
                f"Unsupported statement of type {type(statement)}",
                error_node=statement,
                span=statement.span,
            )
        return result

    def visit_basic_block(
        self,
        stmt_list: list[pulse_ast.Statement],
        is_def_cal: bool,
    ) -> list[pulse_ast.Statement]:
        """Visit a basic block of statements.

        Args:
            stmt_list (list[pulse_ast.Statement]): The list of statements to visit.
            is_def_cal (bool): is the given statements from def_cal block.

        Returns:
            list[pulse_ast.Statement]: The list of unrolled statements.
        """
        result = []
        self._is_def_cal = is_def_cal
        for stmt in stmt_list:
            result.extend(self.visit_statement(stmt))
        return result
