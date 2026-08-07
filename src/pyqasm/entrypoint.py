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
Top-level entrypoint functions for pyqasm.

"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import openqasm3

from pyqasm.exceptions import ValidationError
from pyqasm.maps import SUPPORTED_QASM_VERSIONS
from pyqasm.modules import Qasm2Module, Qasm3Module, QasmModule
from pyqasm.preprocess import process_include_statements

if TYPE_CHECKING:
    import openqasm3.ast

# maps each documented loads() kwarg to the module attribute that stores it
_LOADS_KWARG_ATTRS = {
    "device_qubits": "_device_qubits",
    "device_cycle_time": "_device_cycle_time",
    "compiler_angle_type_size": "_compiler_angle_type_size",
    "extern_functions": "_extern_functions",
    "frame_in_def_cal": "_frame_in_def_cal",
    "frame_limit_per_port": "_frame_limit_per_port",
    "play_in_cal_block": "_play_in_cal",
}

# kwargs that must be positive when given; an explicit None counts as not given
_POSITIVE_KWARGS = (
    "device_qubits",
    "device_cycle_time",
    "compiler_angle_type_size",
    "frame_limit_per_port",
)


def _validate_kwargs(kwargs: dict) -> None:
    """Reject unknown kwarg names and non-positive values at the call site,
    instead of silently dropping them (issue #356)."""
    unknown = sorted(set(kwargs) - set(_LOADS_KWARG_ATTRS))
    if unknown:
        raise TypeError(f"loads() got unexpected keyword argument(s): {', '.join(unknown)}")
    for name in _POSITIVE_KWARGS:
        value = kwargs.get(name)
        if value is not None and name in kwargs and value <= 0:
            raise ValueError(f"loads() kwarg '{name}' must be positive, got {value!r}")


def load(filename: str, **kwargs) -> QasmModule:
    """Loads an OpenQASM program into a `QasmModule` object.

    Args:
        filename (str): The filename of the OpenQASM program to validate.

    Returns:
        QasmModule: An object containing the parsed qasm representation along with
            some useful metadata and methods
    """
    if not isinstance(filename, str):
        raise TypeError("Input 'filename' must be of type 'str'.")
    if not os.path.isfile(filename):
        raise FileNotFoundError(f"QASM file '{filename}' not found.")
    program = process_include_statements(filename)
    return loads(program, **kwargs)


def loads(program: openqasm3.ast.Program | str, **kwargs) -> QasmModule:
    """Loads an OpenQASM program into a `QasmModule` object.

    Args:
        program (openqasm3.ast.Program or str): The OpenQASM program to validate.

        **kwargs: Additional arguments to pass to the loads function.

            - **device_qubits** (int): Number of physical qubits available on the target device.

            - **device_cycle_time** (float): The duration of a hardware device cycle, in seconds.

            - **compiler_angle_type_size** (int): The width of the angle type in the compiler.

            - **extern_functions** (dict): Dictionary of extern functions to be added to the module.

            - **frame_in_def_cal** (bool): Whether to allow frames in defcal.

            - **frame_limit_per_port** (int): The maximum number of frames per port.

            - **play_in_cal_block** (bool): Whether to allow play in defcal.

    Raises:
        TypeError: If the input is not a string or an `openqasm3.ast.Program` instance,
            or if an unrecognized keyword argument is passed.
        ValueError: If a numeric keyword argument is zero or negative.
        ValidationError: If the program fails parsing or semantic validation.

    Returns:
        QasmModule: An object containing the parsed qasm representation along with
            some useful metadata and methods
    """
    _validate_kwargs(kwargs)
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
    # presence tests, not truthiness: a falsy value is a caller value, not an omission
    for name, attr in _LOADS_KWARG_ATTRS.items():
        if name in kwargs:
            setattr(module, attr, kwargs[name])
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
