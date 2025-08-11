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
Module defining Qasm Converter elements.

"""
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

import numpy as np


class InversionOp(Enum):
    """
    Enum for specifying the inversion action of a gate.
    """

    NO_OP = 1
    INVERT_ROTATION = 2


class Context(Enum):
    """
    Enum for the different contexts in Qasm.
    """

    GLOBAL = "global"
    BLOCK = "block"
    FUNCTION = "function"
    GATE = "gate"
    BOX = "box"
    PULSE = "pulse"


@dataclass(slots=True)
class DepthNode:
    """Base class for depth nodes."""

    reg_name: str
    reg_index: int
    depth: int = 0


@dataclass(slots=True)
class QubitDepthNode(DepthNode):
    """Qubit depth node."""

    num_resets: int = 0
    num_measurements: int = 0
    num_gates: int = 0
    num_barriers: int = 0

    def _total_ops(self) -> int:
        return self.num_resets + self.num_measurements + self.num_gates + self.num_barriers

    def is_idle(self) -> bool:
        return self._total_ops() == 0


@dataclass(slots=True)
class ClbitDepthNode(DepthNode):
    """Classical bit depth node."""

    num_measurements: int = 0

    def is_idle(self) -> bool:
        return self.num_measurements == 0


@dataclass(slots=True)
class Variable:  # pylint: disable=too-many-instance-attributes
    """
    Class representing an OpenQASM variable.

    Attributes:
        name (str): Name of the variable.
        base_type (Any): Base type of the variable.
        base_size (int): Base size of the variable.
        dims (Optional[List[int]]): Dimensions of the variable.
        value (Optional[int | float | np.ndarray]): Value of the variable.
        time_unit (Optional[str]): Time unit associated with the duration variable.
        span (Any): Span of the variable.
        angle_bit_string (Optional[str]): Bit string representation of the angle value.
        shadow (bool): Flag indicating if the current variable is shadowed from its parent scope.
        is_constant (bool): Flag indicating if the variable is constant.
        is_register (bool): Flag indicating if the variable is a register.
        is_alias (bool): Flag indicating if the variable is an alias.
        readonly (bool): Flag indicating if the variable is readonly.
    """

    name: str
    base_type: Any
    base_size: int
    dims: Optional[list[int]] = None
    value: Optional[int | float | np.ndarray] = None
    time_unit: Optional[str] = None
    span: Any = None
    angle_bit_string: Optional[str] = None
    shadow: bool = False
    is_constant: bool = False
    is_qubit: bool = False
    is_alias: bool = False
    readonly: bool = False


@dataclass(slots=True)
class Frame:
    """
    Class representing a frame in OpenQASM/OpenPulse.

    Attributes:
        name (str): The name of the frame.
        port (Any): The port to which the frame is attached. Immutable after initialization.
        frequency (float): The frequency of the frame.
        frequency_type (Any): The type of the frequency of the frame.
        phase (float): The phase of the frame, in radians.
        phase_type (Any): The type of the phase of the frame.
        time (float): The current time of the frame, in duration units.
                      This is manipulated implicitly and cannot be set directly.
    """

    name: str
    port: Any
    frequency: float
    phase: float
    time: Optional[Any] = None
    phase_type: Optional[Any] = None
    frequency_type: Optional[Any] = None


@dataclass(slots=True)
class Waveform:  # pylint: disable=too-many-instance-attributes
    """
    Class representing a waveform in OpenQASM/OpenPulse.

    Attributes:
        name (str): The name of the waveform.
        amplitude (Any): The amplitude of the waveform.
        total_duration (Any): The total duration of the waveform.
        standard_deviation (Optional[Any]): The standard deviation of the waveform.
        square_width (Optional[Any]): The square width of the waveform.
        y_correction_amp (Optional[Any]): The y correction amplitude of the waveform.
        frequency (Optional[Any]): The frequency of the waveform.
        phase (Optional[Any]): The phase of the waveform.
        waveforms (Optional[list[str]]): The waveforms of the waveform.
        amp_factor (Optional[Any]): The amplitude factor of the waveform.
    """

    name: str
    amplitude: Any
    total_duration: Any
    standard_deviation: Optional[Any] = None
    square_width: Optional[Any] = None
    y_correction_amp: Optional[Any] = None
    frequency: Optional[Any] = None
    phase: Optional[Any] = None
    waveforms: Optional[list[Any]] = None
    amp_factor: Optional[Any] = None


class BasisSet(Enum):
    """
    Enum for the different basis sets in Qasm.
    """

    DEFAULT = 0
    ROTATIONAL_CX = 1
    CLIFFORD_T = 2
