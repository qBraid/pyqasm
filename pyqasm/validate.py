# Copyright (C) 2024 qBraid
#
# This file is part of the qBraid-SDK
#
# The qBraid-SDK is free software released under the GNU General Public License v3
# or later. You can redistribute and/or modify it under the terms of the GPL v3.
# See the LICENSE file in the project root or <https://www.gnu.org/licenses/gpl-3.0.html>.
#
# THERE IS NO WARRANTY for the qBraid-SDK, as per Section 15 of the GPL v3.

"""
Module for performing semantic analysis of OpenQASM 3 programs.

"""
from __future__ import annotations

from typing import TYPE_CHECKING, Union

from openqasm3.parser import QASM3ParsingError

from .exceptions import ValidationError

if TYPE_CHECKING:
    import openqasm3.ast


def validate(program: Union[openqasm3.ast.Program, str]) -> None:
    """Validates a given OpenQASM 3 program for semantic correctness.

    Args:
        program (openqasm3.ast.Program or str): The OpenQASM 3 program to validate.

    Raises:
        TypeError: If the input is not a string or an `openqasm3.ast.Program` instance.
        ValidationError: If the program fails parsing or semantic validation.
    """
    if isinstance(program, str):
        try:
            program = openqasm3.parse(program)
        except QASM3ParsingError as err:
            raise ValidationError(f"Failed to parse OpenQASM string: {err}") from err
    elif not isinstance(program, openqasm3.ast.Program):
        raise TypeError("Input quantum program must be of type 'str' or 'openqasm3.ast.Program'.")

    raise NotImplementedError("Semantic validation is not yet implemented.")
