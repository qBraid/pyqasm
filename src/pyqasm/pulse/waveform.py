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

from pyqasm.elements import Waveform
from pyqasm.exceptions import raise_qasm3_error
from pyqasm.expressions import Qasm3ExprEvaluator
from pyqasm.pulse.validator import PulseValidator


class WaveformValidator:
    """A class for validating waveform declarations in OpenPulse programs."""

    def __init__(self, module, get_identifier_func, get_frame_func, pulse_visitor):
        """Initialize the WaveformValidator.

        Args:
            module: The module containing device cycle time information.
            get_identifier_func: Function to get identifier information.
            get_frame_func: Function to get frame information.
        """
        self._module = module
        self._get_identifier = get_identifier_func
        self._get_frame = get_frame_func
        self._pulse_visitor = pulse_visitor

    # pylint: disable-next=too-many-branches,too-many-locals
    def validate_gaussian_sech_waveform(self, statement, wf_func_name, waveforms, waveform_name):
        """Validate gaussian and sech waveform declarations.

        Args:
            statement: The statement containing the waveform declaration.
            wf_func_name: The name of the waveform function.
            waveforms: Dictionary of available waveforms.
            waveform_name: The name of the waveform.
        """
        func_args = statement.arguments
        if len(func_args) != 3:
            raise_qasm3_error(
                f"Invalid number of arguments in '{wf_func_name}'",
                error_node=statement,
                span=statement.span,
            )
        _amp_arg = func_args[0]
        _duration_arg = func_args[1]
        _sigma_arg = func_args[2]

        if isinstance(_amp_arg, qasm3_ast.Identifier):
            _amp_arg_value, _amp_arg_type, _ = self._get_identifier(statement, _amp_arg)
            if not isinstance(_amp_arg_type, qasm3_ast.ComplexType) or not isinstance(
                _amp_arg_type.base_type, qasm3_ast.FloatType
            ):
                raise_qasm3_error(
                    f"Invalid amplitude type '{type(_amp_arg_type).__name__}' "
                    f"for '{_amp_arg.name}' in '{wf_func_name}'",
                    error_node=statement,
                    span=statement.span,
                )
            if _amp_arg_value is not None:
                val = PulseValidator.make_complex_binary_expression(_amp_arg_value)
                statement.arguments[0] = val
            else:
                statement.arguments[0] = qasm3_ast.FloatLiteral(None)
        elif isinstance(_amp_arg, (qasm3_ast.BinaryExpression, qasm3_ast.ImaginaryLiteral)):
            amp_arg, _ = Qasm3ExprEvaluator.evaluate_expression(_amp_arg)
            if not isinstance(amp_arg, complex):
                raise_qasm3_error(
                    f"Invalid amplitude value '{type(_amp_arg).__name__}' in " f"'{wf_func_name}'",
                    error_node=statement,
                    span=statement.span,
                )
        else:
            raise_qasm3_error(
                f"Invalid amplitude initialization '{type(_amp_arg).__name__}' in "
                f"'{wf_func_name}'",
                error_node=statement,
                span=statement.span,
            )

        for idx, arg, arg_name in [
            (1, _duration_arg, "Total duration"),
            (2, _sigma_arg, "Standard deviation"),
        ]:
            if isinstance(arg, qasm3_ast.Identifier):
                arg_value, arg_type, _ = self._get_identifier(statement, arg)
                if not isinstance(arg_type, qasm3_ast.DurationType):
                    raise_qasm3_error(
                        f"Invalid '{arg_name}' type '{type(arg_type).__name__}' for "
                        f"'{arg.name}' in '{wf_func_name}'",
                        error_node=statement,
                        span=statement.span,
                    )
                if arg_value is None:
                    arg_value = 0
                statement.arguments[idx] = qasm3_ast.DurationLiteral(
                    arg_value,
                    unit=(
                        qasm3_ast.TimeUnit.dt
                        if self._module._device_cycle_time
                        else qasm3_ast.TimeUnit.ns
                    ),
                )
            elif not isinstance(arg, qasm3_ast.DurationLiteral):
                raise_qasm3_error(
                    f"Invalid '{arg_name}' initialization '{arg.value}' in " f"'{wf_func_name}'",
                    error_node=statement,
                    span=statement.span,
                )

        waveform_var = Waveform(
            name="",
            amplitude=statement.arguments[0],
            total_duration=statement.arguments[1],
            standard_deviation=statement.arguments[2],
        )
        if waveform_name is not None:
            waveform_var.name = waveform_name
            waveforms[waveform_name] = waveform_var
        else:
            self._pulse_visitor._temp_waveform = waveform_var

    # pylint: disable-next=too-many-branches,too-many-locals
    def validate_gaussian_square_waveform(self, statement, waveforms, waveform_name):
        """Validate gaussian_square waveform declarations.

        Args:
            statement: The statement containing the waveform declaration.
            waveforms: Dictionary of available waveforms.
            waveform_name: The name of the waveform.
        """
        wave_form_args = statement.arguments
        if len(wave_form_args) != 4:
            raise_qasm3_error(
                f"Invalid number of arguments for 'gaussian_square' "
                f"Expected 4, got {len(wave_form_args)}.",
                error_node=statement,
                span=statement.span,
            )
        amp_arg = wave_form_args[0]
        duration_arg = wave_form_args[1]
        square_width_arg = wave_form_args[2]
        std_deviation_arg = wave_form_args[3]

        if isinstance(amp_arg, qasm3_ast.Identifier):
            _amp_arg_value, _amp_arg_type, _ = self._get_identifier(statement, amp_arg)
            if not isinstance(_amp_arg_type, qasm3_ast.ComplexType) or not isinstance(
                _amp_arg_type.base_type, qasm3_ast.FloatType
            ):
                raise_qasm3_error(
                    f"Invalid amplitude type '{type(_amp_arg_type).__name__}' for "
                    f"'{amp_arg.name}' in 'gaussian_square'",
                    error_node=statement,
                    span=statement.span,
                )
            if _amp_arg_value is not None:
                val = PulseValidator.make_complex_binary_expression(_amp_arg_value)
                statement.arguments[0] = val
            else:
                statement.arguments[0] = qasm3_ast.FloatLiteral(None)
        elif isinstance(amp_arg, qasm3_ast.BinaryExpression):
            amp_val, _ = Qasm3ExprEvaluator.evaluate_expression(amp_arg)
            if not isinstance(amp_val, complex):
                raise_qasm3_error(
                    f"Invalid amplitude value '{type(amp_arg).__name__}' in " f"'gaussian_square'",
                    error_node=statement,
                    span=statement.span,
                )
        else:
            raise_qasm3_error(
                f"Invalid amplitude initialization '{type(amp_arg).__name__}' in "
                f"'gaussian_square'",
                error_node=statement,
                span=statement.span,
            )

        for idx, arg, arg_name in [
            (1, duration_arg, "Total duration"),
            (2, square_width_arg, "Square width"),
            (3, std_deviation_arg, "Standard deviation"),
        ]:
            if isinstance(arg, qasm3_ast.Identifier):
                arg_value, arg_type, _ = self._get_identifier(statement, arg)
                if not isinstance(arg_type, qasm3_ast.DurationType):
                    raise_qasm3_error(
                        f"Invalid '{arg_name}' type '{type(arg_type).__name__}' "
                        f"for '{arg.name}' in 'gaussian_square'",
                        error_node=statement,
                        span=statement.span,
                    )
                if arg_value is None:
                    arg_value = 0
                statement.arguments[idx] = qasm3_ast.DurationLiteral(
                    arg_value,
                    unit=(
                        qasm3_ast.TimeUnit.dt
                        if self._module._device_cycle_time
                        else qasm3_ast.TimeUnit.ns
                    ),
                )
            elif not isinstance(arg, qasm3_ast.DurationLiteral):
                raise_qasm3_error(
                    f"Invalid '{arg_name}' initialization "
                    f"'{getattr(arg, 'value', arg)}' in 'gaussian_square'",
                    error_node=statement,
                    span=statement.span,
                )

        waveform_var = Waveform(
            name="",
            amplitude=statement.arguments[0],
            total_duration=statement.arguments[1],
            square_width=statement.arguments[2],
            standard_deviation=statement.arguments[3],
        )
        if waveform_name is not None:
            waveform_var.name = waveform_name
            waveforms[waveform_name] = waveform_var
        else:
            self._pulse_visitor._temp_waveform = waveform_var

    # pylint: disable-next=too-many-branches,too-many-locals
    def validate_drag_waveform(self, statement, waveforms, waveform_name):
        """Validate drag waveform declarations.

        Args:
            statement: The statement containing the waveform declaration.
            waveforms: Dictionary of available waveforms.
            waveform_name: The name of the waveform.
        """
        func_args = statement.arguments
        if len(func_args) != 4:
            raise_qasm3_error(
                f"Invalid number of arguments for 'drag' " f"Expected 4, got {len(func_args)}.",
                error_node=statement,
                span=statement.span,
            )
        amp_arg = func_args[0]
        duration_arg = func_args[1]
        std_deviation_arg = func_args[2]
        beta_arg = func_args[3]

        if isinstance(amp_arg, qasm3_ast.Identifier):
            _amp_arg_value, _amp_arg_type, _ = self._get_identifier(statement, amp_arg)
            if not isinstance(_amp_arg_type, qasm3_ast.ComplexType):
                raise_qasm3_error(
                    f"Invalid amplitude type '{type(_amp_arg_type).__name__}' for "
                    f"'{amp_arg.name}' in 'drag'",
                    error_node=statement,
                    span=statement.span,
                )
            if _amp_arg_value is not None:
                statement.arguments[0] = PulseValidator.make_complex_binary_expression(
                    _amp_arg_value
                )
            else:
                statement.arguments[0] = qasm3_ast.FloatLiteral(None)
        elif isinstance(amp_arg, qasm3_ast.BinaryExpression):
            amp_val, _ = Qasm3ExprEvaluator.evaluate_expression(amp_arg)
            if not isinstance(amp_val, complex):
                raise_qasm3_error(
                    f"Invalid amplitude value '{type(amp_arg).__name__}' in " f"'drag'",
                    error_node=statement,
                    span=statement.span,
                )
        else:
            raise_qasm3_error(
                f"Invalid amplitude initialization '{type(amp_arg).__name__}' in " f"'drag'",
                error_node=statement,
                span=statement.span,
            )

        for idx, arg, arg_name in [
            (1, duration_arg, "Total duration"),
            (2, std_deviation_arg, "Standard deviation"),
        ]:
            if isinstance(arg, qasm3_ast.Identifier):
                arg_value, arg_type, _ = self._get_identifier(statement, arg)
                if not isinstance(arg_type, qasm3_ast.DurationType):
                    raise_qasm3_error(
                        f"Invalid '{arg_name}' type '{type(arg_type).__name__}' for "
                        f"'{arg.name}' in 'drag'",
                        error_node=statement,
                        span=statement.span,
                    )
                if arg_value is None:
                    arg_value = 0
                statement.arguments[idx] = qasm3_ast.DurationLiteral(
                    arg_value,
                    unit=(
                        qasm3_ast.TimeUnit.dt
                        if self._module._device_cycle_time
                        else qasm3_ast.TimeUnit.ns
                    ),
                )
            elif not isinstance(arg, qasm3_ast.DurationLiteral):
                raise_qasm3_error(
                    f"Invalid '{arg_name}' initialization "
                    f"'{getattr(arg, 'value', arg)}' in 'drag'",
                    error_node=statement,
                    span=statement.span,
                )

        if isinstance(beta_arg, qasm3_ast.Identifier):
            beta_value, beta_type, _ = self._get_identifier(statement, beta_arg)
            if not isinstance(beta_type, qasm3_ast.FloatType):
                raise_qasm3_error(
                    f"Invalid 'Y correction amplitude' type "
                    f"'{type(beta_type).__name__}' for '{beta_arg.name}' in "
                    f"'drag'",
                    error_node=statement,
                    span=statement.span,
                )
            statement.arguments[3] = qasm3_ast.FloatLiteral(beta_value)
        elif not isinstance(beta_arg, qasm3_ast.FloatLiteral):
            raise_qasm3_error(
                f"Invalid 'Y correction amplitude' initialization "
                f"'{getattr(beta_arg, 'value', beta_arg)}' in 'drag' "
                f"for waveform",
                error_node=statement,
                span=statement.span,
            )
        waveform_var = Waveform(
            name="",
            amplitude=statement.arguments[0],
            total_duration=statement.arguments[1],
            standard_deviation=statement.arguments[2],
            y_correction_amp=statement.arguments[3],
        )
        if waveform_name is not None:
            waveform_var.name = waveform_name
            waveforms[waveform_name] = waveform_var
        else:
            self._pulse_visitor._temp_waveform = waveform_var

    # pylint: disable-next=too-many-branches,too-many-locals
    def validate_constant_waveform(self, statement, waveforms, waveform_name):
        """Validate constant waveform declarations.

        Args:
            statement: The statement containing the waveform declaration.
            waveforms: Dictionary of available waveforms.
            waveform_name: The name of the waveform.
        """
        func_args = statement.arguments
        if len(func_args) != 2:
            raise_qasm3_error(
                f"Invalid number of arguments for 'constant' " f"Expected 2, got {len(func_args)}.",
                error_node=statement,
                span=statement.span,
            )
        amp_arg = func_args[0]
        duration_arg = func_args[1]

        if isinstance(amp_arg, qasm3_ast.Identifier):
            _amp_arg_value, _amp_arg_type, _ = self._get_identifier(statement, amp_arg)
            if not isinstance(_amp_arg_type, qasm3_ast.ComplexType):
                raise_qasm3_error(
                    f"Invalid amplitude type '{type(_amp_arg_type).__name__}' for "
                    f"'{amp_arg.name}' in 'constant'",
                    error_node=statement,
                    span=statement.span,
                )
            if _amp_arg_value is not None:
                statement.arguments[0] = PulseValidator.make_complex_binary_expression(
                    _amp_arg_value
                )
            else:
                statement.arguments[0] = qasm3_ast.FloatLiteral(None)
        elif isinstance(amp_arg, qasm3_ast.BinaryExpression):
            amp_val, _ = Qasm3ExprEvaluator.evaluate_expression(amp_arg)
            if not isinstance(amp_val, complex):
                raise_qasm3_error(
                    f"Invalid amplitude value '{type(amp_arg).__name__}' in " f"'constant'",
                    error_node=statement,
                    span=statement.span,
                )
        else:
            raise_qasm3_error(
                f"Invalid amplitude initialization '{type(amp_arg).__name__}' in " f"'constant'",
                error_node=statement,
                span=statement.span,
            )

        if isinstance(duration_arg, qasm3_ast.Identifier):
            arg_value, arg_type, _ = self._get_identifier(statement, duration_arg)
            if not isinstance(arg_type, qasm3_ast.DurationType):
                raise_qasm3_error(
                    f"Invalid 'Total duration' type '{type(arg_type).__name__}' for "
                    f"'{duration_arg.name}' in 'constant'",
                    error_node=statement,
                    span=statement.span,
                )
            if arg_value is None:
                arg_value = 0
            statement.arguments[1] = qasm3_ast.DurationLiteral(
                arg_value,
                unit=(
                    qasm3_ast.TimeUnit.dt
                    if self._module._device_cycle_time
                    else qasm3_ast.TimeUnit.ns
                ),
            )
        elif not isinstance(duration_arg, qasm3_ast.DurationLiteral):
            raise_qasm3_error(
                f"Invalid 'Total duration' initialization "
                f"'{getattr(duration_arg, 'value', duration_arg)}' in "
                f"'constant'",
                error_node=statement,
                span=statement.span,
            )
        waveform_var = Waveform(
            name="",
            amplitude=statement.arguments[0],
            total_duration=statement.arguments[1],
        )
        if waveform_name is not None:
            waveform_var.name = waveform_name
            waveforms[waveform_name] = waveform_var
        else:
            self._pulse_visitor._temp_waveform = waveform_var

    # pylint: disable-next=too-many-branches,too-many-locals,too-many-statements
    def validate_sine_waveform(self, statement, waveforms, waveform_name):
        """Validate sine waveform declarations.

        Args:
            statement: The statement containing the waveform declaration.
            waveforms: Dictionary of available waveforms.
            waveform_name: The name of the waveform.
        """
        # sine(complex[float[size]] amp, duration d, float[size] frequency, angle[size] phase)
        sine_args = statement.arguments
        if len(sine_args) != 4:
            raise_qasm3_error(
                f"Invalid number of arguments for 'sine' " f"Expected 4, got {len(sine_args)}.",
                error_node=statement,
                span=statement.span,
            )
        amp_arg = sine_args[0]
        duration_arg = sine_args[1]
        frequency_arg = sine_args[2]
        phase_arg = sine_args[3]

        # Validate amplitude: must be complex[float[size]]
        if isinstance(amp_arg, qasm3_ast.Identifier):
            _amp_arg_value, _amp_arg_type, _ = self._get_identifier(statement, amp_arg)
            if not isinstance(_amp_arg_type, qasm3_ast.ComplexType) or not isinstance(
                _amp_arg_type.base_type, qasm3_ast.FloatType
            ):
                raise_qasm3_error(
                    f"Invalid amplitude type '{type(_amp_arg_type).__name__}' for "
                    f"'{amp_arg.name}' in 'sine'",
                    error_node=statement,
                    span=statement.span,
                )
            if _amp_arg_value is not None:
                statement.arguments[0] = PulseValidator.make_complex_binary_expression(
                    _amp_arg_value
                )
            else:
                statement.arguments[0] = qasm3_ast.FloatLiteral(None)
        elif isinstance(amp_arg, qasm3_ast.BinaryExpression):
            amp_val, _ = Qasm3ExprEvaluator.evaluate_expression(amp_arg)
            if not isinstance(amp_val, complex):
                raise_qasm3_error(
                    f"Invalid amplitude value '{type(amp_arg).__name__}' in 'sine' "
                    f"for waveform",
                    error_node=statement,
                    span=statement.span,
                )
        else:
            raise_qasm3_error(
                f"Invalid amplitude initialization '{type(amp_arg).__name__}' in " f"'sine'",
                error_node=statement,
                span=statement.span,
            )

        # Validate duration: must be duration
        if isinstance(duration_arg, qasm3_ast.Identifier):
            arg_value, arg_type, _ = self._get_identifier(statement, duration_arg)
            if not isinstance(arg_type, qasm3_ast.DurationType):
                raise_qasm3_error(
                    f"Invalid 'Total duration' type '{type(arg_type).__name__}' for "
                    f"'{duration_arg.name}' in 'sine'",
                    error_node=statement,
                    span=statement.span,
                )
            if arg_value is None:
                arg_value = 0
            statement.arguments[1] = qasm3_ast.DurationLiteral(
                arg_value,
                unit=(
                    qasm3_ast.TimeUnit.dt
                    if self._module._device_cycle_time
                    else qasm3_ast.TimeUnit.ns
                ),
            )
        elif not isinstance(duration_arg, qasm3_ast.DurationLiteral):
            raise_qasm3_error(
                f"Invalid 'Total duration' initialization "
                f"'{getattr(duration_arg, 'value', duration_arg)}' in 'sine' "
                f"for waveform",
                error_node=statement,
                span=statement.span,
            )

        # Validate frequency: must be float[size]
        if isinstance(frequency_arg, qasm3_ast.Identifier):
            freq_value, freq_type, _ = self._get_identifier(statement, frequency_arg)
            if not isinstance(freq_type, qasm3_ast.FloatType):
                raise_qasm3_error(
                    f"Invalid 'frequency' type '{type(freq_type).__name__}' for "
                    f"'{frequency_arg.name}' in 'sine'",
                    error_node=statement,
                    span=statement.span,
                )
            # Optionally, could wrap as FloatLiteral if value is available
            if freq_value is not None:
                statement.arguments[2] = qasm3_ast.FloatLiteral(freq_value)
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
            phase_value, phase_type, _ = self._get_identifier(statement, phase_arg)
            if not isinstance(phase_type, qasm3_ast.AngleType):
                raise_qasm3_error(
                    f"Invalid 'phase' type '{type(phase_type).__name__}' for "
                    f"'{phase_arg.name}' in 'sine'",
                    error_node=statement,
                    span=statement.span,
                )
            # Optionally, could wrap as FloatLiteral if value is available
            if phase_value is not None:
                statement.arguments[3] = qasm3_ast.FloatLiteral(phase_value)
        elif not isinstance(phase_arg, qasm3_ast.FloatLiteral):
            raise_qasm3_error(
                f"Invalid 'phase' initialization "
                f"'{getattr(phase_arg, 'value', phase_arg)}' in 'sine' "
                f"for waveform",
                error_node=statement,
                span=statement.span,
            )

        waveform_var = Waveform(
            name="",
            amplitude=statement.arguments[0],
            total_duration=statement.arguments[1],
            frequency=statement.arguments[2],
            phase=statement.arguments[3],
        )
        if waveform_name is not None:
            waveform_var.name = waveform_name
            waveforms[waveform_name] = waveform_var
        else:
            self._pulse_visitor._temp_waveform = waveform_var

    def validate_mix_sum_waveform(self, statement, wf_func_name, waveforms, waveform_name):
        """Validate mix and sum waveform declarations.

        Args:
            statement: The statement containing the waveform declaration.
            wf_func_name: The name of the waveform function.
            waveforms: Dictionary of available waveforms.
            waveform_name: The name of the waveform.
        """
        func_args = statement.arguments
        if len(func_args) != 2:
            raise_qasm3_error(
                f"Invalid number of arguments for '{wf_func_name}' "
                f"Expected 2, got {len(func_args)}.",
                error_node=statement,
                span=statement.span,
            )
        wf1_arg = func_args[0]
        wf2_arg = func_args[1]

        for _, arg, arg_label in [(0, wf1_arg, "Waveform 1"), (1, wf2_arg, "Waveform 2")]:
            if isinstance(arg, qasm3_ast.Identifier):
                arg_name = arg.name
                if arg_name not in waveforms:
                    raise_qasm3_error(
                        f"Waveform '{arg_name}' is not declared",
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
            waveforms=[waveforms[arg.name] for arg in statement.arguments],
        )
        if waveform_name is not None:
            waveform_var.name = waveform_name
            waveforms[waveform_name] = waveform_var
        else:
            self._pulse_visitor._temp_waveform = waveform_var

    def validate_phase_shift_waveform(self, statement, waveforms, waveform_name):
        """Validate phase_shift waveform declarations.

        Args:
            statement: The statement containing the waveform declaration.
            waveforms: Dictionary of available waveforms.
            waveform_name: The name of the waveform.
        """
        func_args = statement.arguments
        if len(func_args) != 2:
            raise_qasm3_error(
                f"Invalid number of arguments for 'phase_shift' "
                f"Expected 2, got {len(func_args)}.",
                error_node=statement,
                span=statement.span,
            )
        wf_arg = func_args[0]
        ang_arg = func_args[1]

        # Validate waveform argument
        if isinstance(wf_arg, qasm3_ast.Identifier):
            wf_name = wf_arg.name
            if wf_name not in waveforms:
                raise_qasm3_error(
                    f"Waveform '{wf_name}' is not declared",
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
            ang_value, ang_type, _ = self._get_identifier(statement, ang_arg)
            if not isinstance(ang_type, qasm3_ast.AngleType):
                raise_qasm3_error(
                    f"Invalid angle type '{type(ang_type).__name__}' for "
                    f"'{ang_arg.name}' in 'phase_shift'",
                    error_node=statement,
                    span=statement.span,
                )
            if ang_value is not None:
                statement.arguments[1] = qasm3_ast.FloatLiteral(ang_value)
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
            waveforms=[waveforms[arg.name] for arg in [statement.arguments[0]]],
            phase=statement.arguments[1],
        )
        if waveform_name is not None:
            waveform_var.name = waveform_name
            waveforms[waveform_name] = waveform_var
        else:
            self._pulse_visitor._temp_waveform = waveform_var

    def validate_scale_waveform(self, statement, waveforms, waveform_name):
        """Validate scale waveform declarations.

        Args:
            statement: The statement containing the waveform declaration.
            waveforms: Dictionary of available waveforms.
            waveform_name: The name of the waveform.
        """
        func_args = statement.arguments
        if len(func_args) != 2:
            raise_qasm3_error(
                f"Invalid number of arguments for 'scale' " f"Expected 2, got {len(func_args)}.",
                error_node=statement,
                span=statement.span,
            )
        wf_arg = func_args[0]
        factor_arg = func_args[1]

        # Validate waveform argument
        if isinstance(wf_arg, qasm3_ast.Identifier):
            wf_name = wf_arg.name
            if wf_name not in waveforms:
                raise_qasm3_error(
                    f"Waveform '{wf_name}' is not declared",
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
            factor_value, factor_type, _ = self._get_identifier(statement, factor_arg)
            if not isinstance(factor_type, qasm3_ast.FloatType):
                raise_qasm3_error(
                    f"Invalid factor type '{type(factor_type).__name__}' for "
                    f"'{factor_arg.name}' in 'scale'",
                    error_node=statement,
                    span=statement.span,
                )
            statement.arguments[1] = qasm3_ast.FloatLiteral(factor_value)
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
            waveforms=[waveforms[arg.name] for arg in [statement.arguments[0]]],
        )
        if waveform_name is not None:
            waveform_var.name = waveform_name
            waveforms[waveform_name] = waveform_var
        else:
            self._pulse_visitor._temp_waveform = waveform_var

    def validate_capture_v3_and_v4_waveform(self, statement):
        """Validate capture_v3 and capture_v4 declarations.

        Args:
            statement: The statement containing the capture_v3 or capture_v4 function.
        """
        func_args = statement.arguments
        if len(func_args) != 2:
            raise_qasm3_error(
                f"Invalid number of arguments for '{statement.name.name}' "
                f"Expected 2, got {len(func_args)}.",
                error_node=statement,
                span=statement.span,
            )
        frame_arg = func_args[0]
        duration_arg = func_args[1]

        # Validate frame argument
        if isinstance(frame_arg, qasm3_ast.Identifier):
            _ = self._get_frame(statement, frame_arg.name)
        else:
            raise_qasm3_error(
                f"Invalid frame argument '{type(frame_arg).__name__}' in '{statement.name.name}'",
                error_node=statement,
                span=statement.span,
            )

        # Validate duration argument
        if isinstance(duration_arg, qasm3_ast.Identifier):
            duration_value, duration_type, _ = self._get_identifier(statement, duration_arg)
            if not isinstance(duration_type, qasm3_ast.DurationType):
                raise_qasm3_error(
                    f"Invalid duration type '{type(duration_type).__name__}' for "
                    f"'{duration_arg.name}' in '{statement.name.name}'",
                    error_node=statement,
                    span=statement.span,
                )
            if duration_value is None:
                duration_value = 0
            statement.arguments[1] = qasm3_ast.DurationLiteral(
                duration_value,
                unit=(
                    qasm3_ast.TimeUnit.dt
                    if self._module._device_cycle_time
                    else qasm3_ast.TimeUnit.ns
                ),
            )
        elif not isinstance(duration_arg, qasm3_ast.DurationLiteral):
            raise_qasm3_error(
                f"Invalid duration initialization "
                f"'{getattr(duration_arg, 'value', duration_arg)}' in '{statement.name.name}'",
                error_node=statement,
                span=statement.span,
            )
