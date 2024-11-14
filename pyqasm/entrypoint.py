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

from pyqasm.exceptions import ValidationError
from pyqasm.maps import SUPPORTED_QASM_VERSIONS
from pyqasm.modules import Qasm2Module, Qasm3Module, QasmModule

if TYPE_CHECKING:
    import openqasm3.ast


def load(filename: str) -> QasmModule:
    """Loads an OpenQASM program into a `QasmModule` object.

    Args:
        filename (str): The filename of the OpenQASM program to validate.

    Returns:
        QasmModule: An object containing the parsed qasm representation along with
            some useful metadata and methods
    """
    if not isinstance(filename, str):
        raise TypeError("Input 'filename' must be of type 'str'.")
    with open(filename, "r", encoding="utf-8") as file:
        program = file.read()
    return loads(program)


def loads(program: openqasm3.ast.Program | str) -> QasmModule:
    """Loads an OpenQASM program into a `QasmModule` object.

    Args:
        program (openqasm3.ast.Program or str): The OpenQASM program to validate.

    Raises:
        TypeError: If the input is not a string or an `openqasm3.ast.Program` instance.
        ValidationError: If the program fails parsing or semantic validation.

    Returns:
        QasmModule: An object containing the parsed qasm representation along with
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
        raise ValidationError(
            f"Unsupported OpenQASM version: {program.version}. "
            f"Supported versions are: {SUPPORTED_QASM_VERSIONS}"
        )

    # change version string to x.0 format
    program.version = str(float(program.version))

    qasm_module = Qasm3Module if program.version.startswith("3") else Qasm2Module
    module = qasm_module("main", program)

    return module


def dump(module: QasmModule, filename: str = "main.qasm") -> None:
    """Dumps the `QasmModule` object to a file.

    Args:
        module (QasmModule): The module to dump.
        filename (str): The filename to dump to.

    Returns:
        None
    """
    qasm_string = dumps(module)
    with open(filename, "w", encoding="utf-8") as file:
        file.write(qasm_string)


def dumps(module: QasmModule) -> str:
    """Dumps the `QasmModule` object to a string.

    Args:
        module (QasmModule): The module to dump.

    Raises:
        TypeError: If the input is not a `QasmModule` instance

    Returns:
        str: The dumped module as string.
    """
    if not isinstance(module, QasmModule):
        raise TypeError("Input 'module' must be of type pyqasm.modules.base.QasmModule")

    return str(module)
