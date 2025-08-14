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
Module for waveform validation functions.

This module contains functions for validating different types of waveform
declarations in OpenPulse programs.
"""

import openqasm3.ast as qasm3_ast

from pyqasm.elements import Capture, Variable, Waveform
from pyqasm.exceptions import raise_qasm3_error
from pyqasm.expressions import Qasm3ExprEvaluator
from pyqasm.maps.expressions import TIME_UNITS_MAP
from pyqasm.pulse.validator import PulseValidator


class WaveformValidator:
    """A class for validating waveform declarations in OpenPulse programs."""

    def __init__(self, module, get_identifier_func, get_frame_func, pulse_visitor):
        """Initialize the WaveformValidator.

        Args:
            module: The qasm3 module.
            get_identifier_func: Function to get identifier information.
            get_frame_func: Function to get frame information.
            pulse_visitor: The pulse visitor.
        """
        self._module = module
        self._get_identifier = get_identifier_func
        self._get_frame = get_frame_func
        self._pulse_visitor = pulse_visitor

    def _validate_amplitude_argument(self, statement, amp_arg, func_name):
        """Validate amplitude argument for waveform functions.

        Args:
            statement: The statement containing the waveform declaration.
            amp_arg: The amplitude argument to validate.
            func_name: The name of the waveform function.
        """
        if isinstance(amp_arg, qasm3_ast.Identifier):
            _amp_arg_obj = self._get_identifier(statement, amp_arg)
            if not isinstance(_amp_arg_obj.base_type, qasm3_ast.ComplexType) or not isinstance(
                _amp_arg_obj.base_type.base_type, qasm3_ast.FloatType
            ):
                raise_qasm3_error(
                    f"Invalid amplitude type '{type(_amp_arg_obj.base_type).__name__}' "
                    f"for '{amp_arg.name}' in '{func_name}'",
                    error_node=statement,
                    span=statement.span,
                )
            if _amp_arg_obj.value is not None:
                val = PulseValidator.make_complex_binary_expression(_amp_arg_obj.value)
                statement.arguments[0] = val
            else:
                statement.arguments[0] = qasm3_ast.FloatLiteral(None)
        elif isinstance(amp_arg, (qasm3_ast.BinaryExpression, qasm3_ast.ImaginaryLiteral)):
            amp_arg_val, _ = Qasm3ExprEvaluator.evaluate_expression(amp_arg)
            if not isinstance(amp_arg_val, complex):
                raise_qasm3_error(
                    f"Invalid amplitude value '{type(amp_arg).__name__}' in " f"'{func_name}'",
                    error_node=statement,
                    span=statement.span,
                )
        else:
            raise_qasm3_error(
                f"Invalid amplitude initialization '{type(amp_arg).__name__}' in " f"'{func_name}'",
                error_node=statement,
                span=statement.span,
            )

    def _validate_amplitude_argument_simple(self, statement, amp_arg, func_name):
        """Validate amplitude argument for waveform functions.

        Args:
            statement: The statement containing the waveform declaration.
            amp_arg: The amplitude argument to validate.
            func_name: The name of the waveform function.
        """
        if isinstance(amp_arg, qasm3_ast.Identifier):
            _amp_arg_obj = self._get_identifier(statement, amp_arg)
            if not isinstance(_amp_arg_obj.base_type, qasm3_ast.ComplexType):
                raise_qasm3_error(
                    f"Invalid amplitude type '{type(_amp_arg_obj.base_type).__name__}' for "
                    f"'{amp_arg.name}' in '{func_name}'",
                    error_node=statement,
                    span=statement.span,
                )
            if _amp_arg_obj.value is not None:
                statement.arguments[0] = PulseValidator.make_complex_binary_expression(
                    _amp_arg_obj.value
                )
            else:
                statement.arguments[0] = qasm3_ast.FloatLiteral(None)
        elif isinstance(amp_arg, qasm3_ast.BinaryExpression):
            amp_val, _ = Qasm3ExprEvaluator.evaluate_expression(amp_arg)
            if not isinstance(amp_val, complex):
                raise_qasm3_error(
                    f"Invalid amplitude value '{type(amp_arg).__name__}' in " f"'{func_name}'",
                    error_node=statement,
                    span=statement.span,
                )
        else:
            raise_qasm3_error(
                f"Invalid amplitude initialization '{type(amp_arg).__name__}' in " f"'{func_name}'",
                error_node=statement,
                span=statement.span,
            )

    # pylint: disable-next=too-many-arguments
    def _validate_duration_argument(self, statement, arg, arg_name, func_name, idx):
        """Validate duration argument for waveform functions.

        Args:
            statement: The statement containing the waveform declaration.
            arg: The duration argument to validate.
            arg_name: The name of the argument for error messages.
            func_name: The name of the waveform function.
            idx: The index of the argument in statement.arguments.
        """
        if isinstance(arg, qasm3_ast.Identifier):
            arg_obj = self._get_identifier(statement, arg)
            if not isinstance(arg_obj.base_type, qasm3_ast.DurationType):
                raise_qasm3_error(
                    f"Invalid '{arg_name}' type '{type(arg_obj.base_type).__name__}' for "
                    f"'{arg.name}' in '{func_name}'",
                    error_node=statement,
                    span=statement.span,
                )
            if arg_obj.value is None:
                arg_obj.value = 0
                arg_obj.time_unit = qasm3_ast.TimeUnit.ns
            statement.arguments[idx] = qasm3_ast.DurationLiteral(
                arg_obj.value,
                unit=qasm3_ast.TimeUnit[arg_obj.time_unit],
            )
        elif not isinstance(arg, qasm3_ast.DurationLiteral):
            raise_qasm3_error(
                f"Invalid '{arg_name}' initialization "
                f"'{getattr(arg, 'value', arg)}' in "
                f"'{func_name}'",
                error_node=statement,
                span=statement.span,
            )

    def _validate_standard_deviation(self, statement, arg_obj, arg_name, func_name):
        """Validate standard deviation argument.

        Args:
            statement: The statement containing the waveform declaration.
            arg_obj: The argument object to validate.
            arg_name: The name of the argument for error messages.
            func_name: The name of the waveform function.
        """
        if arg_name == "Standard deviation" and isinstance(arg_obj, Variable):
            if arg_obj.value < 0:
                raise_qasm3_error(
                    f"Invalid '{arg_name}' value '{arg_obj.value}' in " f"'{func_name}'",
                    error_node=statement,
                    span=statement.span,
                )

    def _convert_duration_to_ns(self, statement):
        """Convert duration to nanoseconds.

        Args:
            statement: The statement containing the duration to convert.
        """
        total_duration = statement.arguments[1]
        total_duration.value = total_duration.value * TIME_UNITS_MAP[total_duration.unit.name]["ns"]
        total_duration.unit = qasm3_ast.TimeUnit.ns
        statement.arguments[1] = total_duration

    def _create_and_store_waveform(self, statement, waveform_name, **kwargs):
        """Create and store waveform in scope.

        Args:
            statement: The statement containing the waveform declaration.
            waveform_name: The name of the waveform.
            **kwargs: Additional arguments for Waveform constructor.
        """
        waveform_var = Waveform(
            name="",
            amplitude=statement.arguments[0],
            total_duration=statement.arguments[1],
            **kwargs,
        )
        if waveform_name is not None:
            waveform_var.name = waveform_name
            self._pulse_visitor._openpulse_scope_manager.update_var_in_scope(waveform_var)
        else:
            self._pulse_visitor._temp_waveform = waveform_var

    # pylint: disable-next=too-many-branches,too-many-locals
    def validate_gaussian_sech_waveform(self, statement, wf_func_name, waveform_name):
        """Validate gaussian and sech waveform declarations.

        Args:
            statement: The statement containing the waveform declaration.
            wf_func_name: The name of the waveform function.
            waveform_name: The name of the waveform.
        """
        func_args = statement.arguments
        PulseValidator.validate_openpulse_func_arg_length(statement, wf_func_name, len(func_args))
        _amp_arg = func_args[0]
        _duration_arg = func_args[1]
        _sigma_arg = func_args[2]

        self._validate_amplitude_argument(statement, _amp_arg, wf_func_name)

        for idx, arg, arg_name in [
            (1, _duration_arg, "Total duration"),
            (2, _sigma_arg, "Standard deviation"),
        ]:
            self._validate_duration_argument(statement, arg, arg_name, wf_func_name, idx)
            if arg_name == "Standard deviation" and isinstance(arg, qasm3_ast.Identifier):
                arg_obj = self._get_identifier(statement, arg)
                self._validate_standard_deviation(statement, arg_obj, arg_name, wf_func_name)
        self._convert_duration_to_ns(statement)

        self._create_and_store_waveform(
            statement, waveform_name, standard_deviation=statement.arguments[2]
        )

    # pylint: disable-next=too-many-branches,too-many-locals
    def validate_gaussian_square_waveform(self, statement, waveform_name):
        """Validate gaussian_square waveform declarations.

        Args:
            statement: The statement containing the waveform declaration.
            waveform_name: The name of the waveform.
        """
        wave_form_args = statement.arguments
        PulseValidator.validate_openpulse_func_arg_length(
            statement, "gaussian_square", len(wave_form_args)
        )
        amp_arg = wave_form_args[0]
        duration_arg = wave_form_args[1]
        square_width_arg = wave_form_args[2]
        std_deviation_arg = wave_form_args[3]

        self._validate_amplitude_argument_simple(statement, amp_arg, "gaussian_square")

        for idx, arg, arg_name in [
            (1, duration_arg, "Total duration"),
            (2, square_width_arg, "Square width"),
            (3, std_deviation_arg, "Standard deviation"),
        ]:
            self._validate_duration_argument(statement, arg, arg_name, "gaussian_square", idx)
            if arg_name == "Standard deviation" and isinstance(arg, qasm3_ast.Identifier):
                arg_obj = self._get_identifier(statement, arg)
                self._validate_standard_deviation(statement, arg_obj, arg_name, "gaussian_square")
        self._convert_duration_to_ns(statement)

        self._create_and_store_waveform(
            statement,
            waveform_name,
            square_width=statement.arguments[2],
            standard_deviation=statement.arguments[3],
        )

    # pylint: disable-next=too-many-branches,too-many-locals
    def validate_drag_waveform(self, statement, waveform_name):
        """Validate drag waveform declarations.

        Args:
            statement: The statement containing the waveform declaration.
            waveform_name: The name of the waveform.
        """
        func_args = statement.arguments
        PulseValidator.validate_openpulse_func_arg_length(statement, "drag", len(func_args))
        amp_arg = func_args[0]
        duration_arg = func_args[1]
        std_deviation_arg = func_args[2]
        beta_arg = func_args[3]

        self._validate_amplitude_argument_simple(statement, amp_arg, "drag")

        for idx, arg, arg_name in [
            (1, duration_arg, "Total duration"),
            (2, std_deviation_arg, "Standard deviation"),
        ]:
            self._validate_duration_argument(statement, arg, arg_name, "drag", idx)
            if arg_name == "Standard deviation" and isinstance(arg, qasm3_ast.Identifier):
                arg_obj = self._get_identifier(statement, arg)
                self._validate_standard_deviation(statement, arg_obj, arg_name, "drag")
        self._convert_duration_to_ns(statement)

        if isinstance(beta_arg, qasm3_ast.Identifier):
            beta_arg_obj = self._get_identifier(statement, beta_arg)
            if not isinstance(beta_arg_obj.base_type, qasm3_ast.FloatType):
                raise_qasm3_error(
                    f"Invalid 'Y correction amplitude' type "
                    f"'{type(beta_arg_obj.base_type).__name__}' for '{beta_arg.name}' in "
                    f"'drag'",
                    error_node=statement,
                    span=statement.span,
                )
            statement.arguments[3] = qasm3_ast.FloatLiteral(beta_arg_obj.value)
        elif not isinstance(beta_arg, qasm3_ast.FloatLiteral):
            raise_qasm3_error(
                f"Invalid 'Y correction amplitude' initialization "
                f"'{getattr(beta_arg, 'value', beta_arg)}' in 'drag' "
                f"for waveform",
                error_node=statement,
                span=statement.span,
            )
        total_duration = statement.arguments[1]
        total_duration.value = total_duration.value * TIME_UNITS_MAP[total_duration.unit.name]["ns"]
        total_duration.unit = qasm3_ast.TimeUnit.ns
        statement.arguments[1] = total_duration
        self._create_and_store_waveform(
            statement,
            waveform_name,
            standard_deviation=statement.arguments[2],
            y_correction_amp=statement.arguments[3],
        )

    # pylint: disable-next=too-many-branches,too-many-locals
    def validate_constant_waveform(self, statement, waveform_name):
        """Validate constant waveform declarations.

        Args:
            statement: The statement containing the waveform declaration.
            waveform_name: The name of the waveform.
        """
        func_args = statement.arguments
        PulseValidator.validate_openpulse_func_arg_length(statement, "constant", len(func_args))
        amp_arg = func_args[0]
        duration_arg = func_args[1]

        self._validate_amplitude_argument_simple(statement, amp_arg, "constant")

        self._validate_duration_argument(statement, duration_arg, "Total duration", "constant", 1)
        self._convert_duration_to_ns(statement)

        self._create_and_store_waveform(statement, waveform_name)

    # pylint: disable-next=too-many-branches,too-many-locals,too-many-statements
    def validate_sine_waveform(self, statement, waveform_name):
        """Validate sine waveform declarations.

        Args:
            statement: The statement containing the waveform declaration.
            waveform_name: The name of the waveform.
        """
        # sine(complex[float[size]] amp, duration d, float[size] frequency, angle[size] phase)
        sine_args = statement.arguments
        PulseValidator.validate_openpulse_func_arg_length(statement, "sine", len(sine_args))
        amp_arg = sine_args[0]
        duration_arg = sine_args[1]
        frequency_arg = sine_args[2]
        phase_arg = sine_args[3]

        # Validate amplitude: must be complex[float[size]]
        self._validate_amplitude_argument(statement, amp_arg, "sine")

        # Validate duration: must be duration
        self._validate_duration_argument(statement, duration_arg, "Total duration", "sine", 1)

        # Validate frequency: must be float[size]
        if isinstance(frequency_arg, qasm3_ast.Identifier):
            freq_arg_obj = self._get_identifier(statement, frequency_arg)
            if not isinstance(freq_arg_obj.base_type, qasm3_ast.FloatType):
                raise_qasm3_error(
                    f"Invalid 'frequency' type '{type(freq_arg_obj.base_type).__name__}' for "
                    f"'{frequency_arg.name}' in 'sine'",
                    error_node=statement,
                    span=statement.span,
                )
            # Optionally, could wrap as FloatLiteral if value is available
            if freq_arg_obj.value is not None:
                statement.arguments[2] = qasm3_ast.FloatLiteral(freq_arg_obj.value)
        elif not isinstance(frequency_arg, qasm3_ast.FloatLiteral):
            raise_qasm3_error(
                f"Invalid 'frequency' initialization "
                f"'{getattr(frequency_arg, 'value', frequency_arg)}' in 'sine' "
                f"for waveform",
                error_node=statement,
                span=statement.span,
            )

        # Validate phase: must be angle[size]
        if isinstance(phase_arg, qasm3_ast.Identifier):
            phase_arg_obj = self._get_identifier(statement, phase_arg)
            if not isinstance(phase_arg_obj.base_type, qasm3_ast.AngleType):
                raise_qasm3_error(
                    f"Invalid 'phase' type '{type(phase_arg_obj.base_type).__name__}' for "
                    f"'{phase_arg.name}' in 'sine'",
                    error_node=statement,
                    span=statement.span,
                )
            # Optionally, could wrap as FloatLiteral if value is available
            if phase_arg_obj.value is not None:
                statement.arguments[3] = qasm3_ast.FloatLiteral(phase_arg_obj.value)
        elif not isinstance(phase_arg, qasm3_ast.FloatLiteral):
            raise_qasm3_error(
                f"Invalid 'phase' initialization "
                f"'{getattr(phase_arg, 'value', phase_arg)}' in 'sine' "
                f"for waveform",
                error_node=statement,
                span=statement.span,
            )
        self._convert_duration_to_ns(statement)

        self._create_and_store_waveform(
            statement, waveform_name, frequency=statement.arguments[2], phase=statement.arguments[3]
        )

    def validate_mix_sum_waveform(self, statement, wf_func_name, waveform_name):
        """Validate mix and sum waveform declarations.

        Args:
            statement: The statement containing the waveform declaration.
            wf_func_name: The name of the waveform function.
            waveform_name: The name of the waveform.
        """
        func_args = statement.arguments
        PulseValidator.validate_openpulse_func_arg_length(statement, wf_func_name, len(func_args))
        wf1_arg = func_args[0]
        wf2_arg = func_args[1]

        for _, arg, arg_label in [(0, wf1_arg, "Waveform 1"), (1, wf2_arg, "Waveform 2")]:
            if isinstance(arg, qasm3_ast.Identifier):
                arg_name = arg.name
                arg_obj = self._get_identifier(statement, arg)
                if arg_obj is None or not isinstance(arg_obj, Waveform):
                    raise_qasm3_error(
                        f"'{arg_name}' should be a waveform variable",
                        error_node=statement,
                        span=statement.span,
                    )
            else:
                raise_qasm3_error(
                    f"Invalid '{arg_label}' initialization '{type(arg).__name__}' in "
                    f"'{wf_func_name}'",
                    error_node=statement,
                    span=statement.span,
                )
        waveform_var = Waveform(
            name="",
            amplitude=None,
            total_duration=qasm3_ast.DurationLiteral(0, unit=qasm3_ast.TimeUnit.ns),
            waveforms=[self._get_identifier(statement, arg) for arg in statement.arguments],
        )
        if waveform_name is not None:
            waveform_var.name = waveform_name
            self._pulse_visitor._openpulse_scope_manager.update_var_in_scope(waveform_var)
        else:
            self._pulse_visitor._temp_waveform = waveform_var

    def validate_phase_shift_waveform(self, statement, waveform_name):
        """Validate phase_shift waveform declarations.

        Args:
            statement: The statement containing the waveform declaration.
            waveform_name: The name of the waveform.
        """
        func_args = statement.arguments
        PulseValidator.validate_openpulse_func_arg_length(statement, "phase_shift", len(func_args))
        wf_arg = func_args[0]
        ang_arg = func_args[1]

        # Validate waveform argument
        if isinstance(wf_arg, qasm3_ast.Identifier):
            wf_name = wf_arg.name
            wf_obj = self._get_identifier(statement, wf_arg)
            if wf_obj is None or not isinstance(wf_obj, Waveform):
                raise_qasm3_error(
                    f"'{wf_name}' should be a waveform variable",
                    error_node=statement,
                    span=statement.span,
                )
        else:
            raise_qasm3_error(
                f"Invalid waveform argument '{type(wf_arg).__name__}' in 'phase_shift'",
                error_node=statement,
                span=statement.span,
            )

        # Validate angle argument
        if isinstance(ang_arg, qasm3_ast.Identifier):
            ang_arg_obj = self._get_identifier(statement, ang_arg)
            if not isinstance(ang_arg_obj.base_type, qasm3_ast.AngleType):
                raise_qasm3_error(
                    f"Invalid angle type '{type(ang_arg_obj.base_type).__name__}' for "
                    f"'{ang_arg.name}' in 'phase_shift'",
                    error_node=statement,
                    span=statement.span,
                )
            if ang_arg_obj.value is not None:
                statement.arguments[1] = qasm3_ast.FloatLiteral(ang_arg_obj.value)
        elif not isinstance(ang_arg, qasm3_ast.FloatLiteral):
            raise_qasm3_error(
                f"Invalid angle initialization "
                f"'{getattr(ang_arg, 'value', ang_arg)}' in 'phase_shift'",
                error_node=statement,
                span=statement.span,
            )
        waveform_var = Waveform(
            name="",
            amplitude=None,
            total_duration=qasm3_ast.DurationLiteral(0, unit=qasm3_ast.TimeUnit.ns),
            waveforms=[self._get_identifier(statement, arg) for arg in [statement.arguments[0]]],
            phase=statement.arguments[1],
        )
        if waveform_name is not None:
            waveform_var.name = waveform_name
            self._pulse_visitor._openpulse_scope_manager.update_var_in_scope(waveform_var)
        else:
            self._pulse_visitor._temp_waveform = waveform_var

    def validate_scale_waveform(self, statement, waveform_name):
        """Validate scale waveform declarations.

        Args:
            statement: The statement containing the waveform declaration.
            waveform_name: The name of the waveform.
        """
        func_args = statement.arguments
        PulseValidator.validate_openpulse_func_arg_length(statement, "scale", len(func_args))
        wf_arg = func_args[0]
        factor_arg = func_args[1]

        # Validate waveform argument
        if isinstance(wf_arg, qasm3_ast.Identifier):
            wf_name = wf_arg.name
            wf_obj = self._get_identifier(statement, wf_arg)
            if wf_obj is None or not isinstance(wf_obj, Waveform):
                raise_qasm3_error(
                    f"'{wf_name}' should be a waveform variable",
                    error_node=statement,
                    span=statement.span,
                )
        else:
            raise_qasm3_error(
                f"Invalid waveform argument '{type(wf_arg).__name__}' in 'scale'",
                error_node=statement,
                span=statement.span,
            )

        # Validate factor argument
        if isinstance(factor_arg, qasm3_ast.Identifier):
            factor_arg_obj = self._get_identifier(statement, factor_arg)
            if not isinstance(factor_arg_obj.base_type, qasm3_ast.FloatType):
                raise_qasm3_error(
                    f"Invalid factor type '{type(factor_arg_obj.base_type).__name__}' for "
                    f"'{factor_arg.name}' in 'scale'",
                    error_node=statement,
                    span=statement.span,
                )
            statement.arguments[1] = qasm3_ast.FloatLiteral(factor_arg_obj.value)
        elif not isinstance(factor_arg, qasm3_ast.FloatLiteral):
            raise_qasm3_error(
                f"Invalid factor initialization "
                f"'{getattr(factor_arg, 'value', factor_arg)}' in 'scale'",
                error_node=statement,
                span=statement.span,
            )
        waveform_var = Waveform(
            name="",
            amplitude=None,
            total_duration=qasm3_ast.DurationLiteral(0, unit=qasm3_ast.TimeUnit.ns),
            amp_factor=statement.arguments[1],
            waveforms=[self._get_identifier(statement, arg) for arg in [statement.arguments[0]]],
        )
        if waveform_name is not None:
            waveform_var.name = waveform_name
            self._pulse_visitor._openpulse_scope_manager.update_var_in_scope(waveform_var)
        else:
            self._pulse_visitor._temp_waveform = waveform_var

    def validate_capture_v3_and_v4_waveform(self, statement, waveform_name):
        """Validate capture_v3 and capture_v4 declarations.

        Args:
            statement: The statement containing the capture_v3 or capture_v4 function.
            waveform_name: The name of the waveform.
        """
        func_args = statement.arguments
        PulseValidator.validate_openpulse_func_arg_length(
            statement, statement.name.name, len(func_args)
        )
        frame_arg = func_args[0]
        duration_arg = func_args[1]

        # Validate frame argument
        frame_obj = None
        if isinstance(frame_arg, qasm3_ast.Identifier):
            frame_obj = self._get_frame(statement, frame_arg.name)
        else:
            raise_qasm3_error(
                f"Invalid frame argument '{type(frame_arg).__name__}' in '{statement.name.name}'",
                error_node=statement,
                span=statement.span,
            )

        # Validate duration argument
        self._validate_duration_argument(
            statement, duration_arg, "duration", statement.name.name, 1
        )
        self._convert_duration_to_ns(statement)

        if frame_obj is not None:
            frame_obj.time.value += statement.arguments[1].value

        if statement.name.name == "capture_v3":
            self._create_and_store_waveform(statement, waveform_name)

    def validate_capture_v1_v2_waveform(self, statement, waveform_name):
        """Validate capture_v1 and capture_v2 function calls.

        Args:
            statement: The statement containing the capture_v1 or capture_v2 function.
        """
        frame_arg = statement.arguments[0]
        frame_obj = None
        if isinstance(frame_arg, qasm3_ast.Identifier):
            frame_obj = self._get_frame(statement, frame_arg.name)
        else:
            raise_qasm3_error(
                f"Invalid frame argument '{type(frame_arg).__name__}' "
                f"in '{statement.name.name}' function",
                error_node=statement,
                span=statement.span,
            )
        waveform_arg = statement.arguments[1]
        waveform_obj = None
        if isinstance(waveform_arg, qasm3_ast.Identifier):
            waveform_obj = self._get_identifier(statement, waveform_arg)
            if waveform_obj is None or not isinstance(waveform_obj, Waveform):
                raise_qasm3_error(
                    f"'{waveform_arg.name}' should be a waveform variable",
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

        capture_var = Capture(
            name="",
            frame=frame_obj,
            waveform=waveform_obj,
        )
        if waveform_name is not None:
            capture_var.name = waveform_name
            self._pulse_visitor._openpulse_scope_manager.update_var_in_scope(capture_var)
        else:
            self._pulse_visitor._temp_waveform = capture_var
