# Copyright (C) 2024 qBraid
#
# This file is part of pyqasm
#
# Pyqasm is free software released under the GNU General Public License v3
# or later. You can redistribute and/or modify it under the terms of the GPL v3.
# See the LICENSE file in the project root or <https://www.gnu.org/licenses/gpl-3.0.html>.
#
# THERE IS NO WARRANTY for pyqasm, as per Section 15 of the GPL v3.

"""
Module defining Qasm Converter elements.

"""
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional, Union

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


@dataclass
class DepthNode:
    """Base class for depth nodes."""

    reg_name: str
    reg_index: int
    depth: int = 0


@dataclass
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


@dataclass
class ClbitDepthNode(DepthNode):
    """Classical bit depth node."""

    num_measurements: int = 0

    def is_idle(self) -> bool:
        return self.num_measurements == 0


@dataclass
class Variable:  # pylint: disable=too-many-instance-attributes
    """
    Class representing an OpenQASM variable.

    Attributes:
        name (str): Name of the variable.
        base_type (Any): Base type of the variable.
        base_size (int): Base size of the variable.
        dims (Optional[List[int]]): Dimensions of the variable.
        value (Optional[Union[int, float, np.ndarray]]): Value of the variable.
        is_constant (bool): Flag indicating if the variable is constant.
        is_register (bool): Flag indicating if the variable is a register.
        readonly (bool): Flag indicating if the variable is readonly.
    """

    name: str
    base_type: Any
    base_size: int
    dims: Optional[list[int]] = None
    value: Optional[Union[int, float, np.ndarray]] = None
    is_constant: bool = False
    is_register: bool = False
    readonly: bool = False
