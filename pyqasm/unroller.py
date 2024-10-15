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
Module containing OpenQASM to QIR conversion functions

"""
from typing import Union

import openqasm3

from .elements import Qasm3Module
from .exceptions import ValidationError
from .visitor import BasicQasmVisitor


def unroll(
    program: Union[openqasm3.ast.Program, str],
    **kwargs,
) -> Qasm3Module:
    """Converts an OpenQASM 3 program to an unrolled qasm program

    Args:
        program (openqasm3.ast.Program or str): The OpenQASM 3 program to convert.

    Returns:
        Qasm3Module: An object containing unrolled qasm representation along with
            some useful metadata and methods

    Raises:
        TypeError: If the input is not a valid OpenQASM 3 program.
        ValidationError: If the conversion fails.
    """
    if isinstance(program, str):
        try:
            program = openqasm3.parse(program)
        except openqasm3.parser.QASM3ParsingError as err:
            raise ValidationError(f"Failed to parse OpenQASM string: {err}") from err

    elif not isinstance(program, openqasm3.ast.Program):
        raise TypeError("Input quantum program must be of type openqasm3.ast.Program or str.")

    module = Qasm3Module.from_program(program)

    visitor = BasicQasmVisitor(module=module, **kwargs)
    module.accept(visitor)

    return module
