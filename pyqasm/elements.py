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
Module defining Qasm3 Converter elements.

"""
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


# pylint: disable-next=too-many-instance-attributes
class Variable:
    """
    Class representing an openqasm variable.

    Args:
        name (str): Name of the variable.
        base_type (Any): Base type of the variable.
        base_size (int): Base size of the variable.
        dims (list[int]): Dimensions of the variable.
        value (Optional[Union[int, float, list]]): Value of the variable.
        is_constant (bool): Flag indicating if the variable is constant.
        is_register (bool): Flag indicating if the variable is a register.
        readonly(bool): Flag indicating if the variable is readonly.

    """

    # pylint: disable-next=too-many-arguments,too-many-positional-arguments
    def __init__(
        self,
        name: str,
        base_type: Any,
        base_size: int,
        dims: Optional[list[int]] = None,
        value: Optional[Union[int, float, np.ndarray]] = None,
        is_constant: bool = False,
        is_register: bool = False,
        readonly: bool = False,
    ):
        self.name = name
        self.base_type = base_type
        self.base_size = base_size
        self.dims = dims
        self.value = value
        self.is_constant = is_constant
        self.is_register = is_register
        self.readonly = readonly

    def __repr__(self) -> str:
        return (
            f"Variable(name = {self.name}, base_type = {self.base_type}, "
            f"base_size = {self.base_size}, dimensions = {self.dims}, "
            f"value = {self.value}, is_constant = {self.is_constant}, "
            f"readonly = {self.readonly}, is_register = {self.is_register})"
        )
