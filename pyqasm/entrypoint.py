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

from .elements import Qasm2Module, Qasm3Module
from .exceptions import ValidationError
from .visitor import BasicQasmVisitor

if TYPE_CHECKING:
    import openqasm3.ast


def load(program: openqasm3.ast.Program | str) -> Qasm3Module:
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
    if program.version not in {"2.0", "3.0", "2", "3"}:
        raise ValidationError(f"Unsupported OpenQASM version: {program.version}")

    qasm_module = Qasm3Module if program.version.startswith("3") else Qasm2Module
    module = qasm_module.from_program(program)

    return module


def validate(program: openqasm3.ast.Program | str) -> None:
    """Validates a given OpenQASM 3 program for semantic correctness.

    Args:
        program (openqasm3.ast.Program or str): The OpenQASM 3 program to validate.

    Raises:
        ValidationError: If the program fails parsing or semantic validation.
    """
    module = load(program)

    try:
        visitor = BasicQasmVisitor(module, check_only=True)
        module.accept(visitor)
    except (TypeError, ValueError) as err:
        raise ValidationError(err) from err


def unroll(
    program: openqasm3.ast.Program | str,
    as_module: bool = False,
    **kwargs,
) -> Qasm3Module | str:
    """Transforms the input program into a linear sequence of qubit and
    classical bit declarations, gate operations, and measurements

    Args:
        program (openqasm3.ast.Program or str): The OpenQASM 3 program to unroll.

    Returns:
        Qasm3Module or str: Returns the flattened program as a string. Or, if
        ``as_module`` is Truem, returns a ``Qasm3Module`` containing the flattened
        program and along with other program metadata as attributes.

    Raises:
        TypeError: If the input is not a supported OpenQASM 3 program type.
        ValueError: If the input program fails to be parsed.
        ValidationError: If the input program fails semantic validation.
    """
    module = load(program)

    visitor = BasicQasmVisitor(module=module, **kwargs)
    module.accept(visitor)

    if as_module:
        return module

    return module.unrolled_qasm
