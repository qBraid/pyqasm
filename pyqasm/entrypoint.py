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
Top-level entrypoint functions for pyqasm.

"""
from __future__ import annotations

from typing import TYPE_CHECKING

import openqasm3

from .exceptions import ValidationError
from .maps import SUPPORTED_QASM_VERSIONS
from .modules import Qasm2Module, Qasm3Module, QasmModule

if TYPE_CHECKING:
    import openqasm3.ast


def load(program: openqasm3.ast.Program | str) -> QasmModule:
    """Loads an OpenQASM 3 program into a `Qasm3Module` object.

    Args:
        program (openqasm3.ast.Program or str): The OpenQASM 3 program to validate.

    Raises:
        TypeError: If the input is not a string or an `openqasm3.ast.Program` instance.
        ValidationError: If the program fails parsing or semantic validation.

    Returns:
        Qasm3Module: An object containing the parsed qasm representation along with
            some useful metadata and methods
    """
    if isinstance(program, str):
        try:
            program = openqasm3.parse(program)
        except openqasm3.parser.QASM3ParsingError as err:
            raise ValidationError(f"Failed to parse OpenQASM string: {err}") from err
    elif not isinstance(program, openqasm3.ast.Program):
        raise TypeError("Input quantum program must be of type 'str' or 'openqasm3.ast.Program'.")
    if program.version not in SUPPORTED_QASM_VERSIONS:
        raise ValidationError(f"Unsupported OpenQASM version: {program.version}")

    # change version string to x.0 format
    program.version = str(float(program.version))

    qasm_module = Qasm3Module if program.version.startswith("3") else Qasm2Module
    module = qasm_module.from_program(program)

    return module
