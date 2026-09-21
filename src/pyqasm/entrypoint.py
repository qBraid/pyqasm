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
from pyqasm.preprocess import (
    process_include_sources,
    process_include_statements,
    rewrite_opaque_declarations,
)

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

# kwargs consumed by the entrypoint itself rather than stored on the module
_PREPROCESS_KWARGS = ("include_dir",)

# kwargs that must be positive when given; an explicit None counts as not given
_POSITIVE_KWARGS = (
    "device_qubits",
    "device_cycle_time",
    "compiler_angle_type_size",
    "frame_limit_per_port",
)


def _validate_kwargs(kwargs: dict, func: str = "loads") -> None:
    """Reject unknown kwarg names and unusable values at the call site, instead of
    silently dropping them (issue #356).

    Args:
        kwargs (dict): The keyword arguments the caller passed.
        func (str): The entrypoint to name in error messages.

    Raises:
        TypeError: If a kwarg name is unrecognised, or a positive-only kwarg is not
            a real number.
        ValueError: If a positive-only kwarg is zero or negative.
    """
    unknown = sorted(set(kwargs) - set(_LOADS_KWARG_ATTRS) - set(_PREPROCESS_KWARGS))
    if unknown:
        raise TypeError(f"{func}() got unexpected keyword argument(s): {', '.join(unknown)}")
    include_dir = kwargs.get("include_dir")
    if include_dir is not None and not isinstance(include_dir, str):
        raise TypeError(
            f"{func}() kwarg 'include_dir' must be a path, got {type(include_dir).__name__}"
        )
    for name in _POSITIVE_KWARGS:
        value = kwargs.get(name)
        if value is None:
            continue
        # bool is a subclass of int, so True would otherwise pass as a count of 1
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(f"{func}() kwarg '{name}' must be a number, got {type(value).__name__}")
        if value <= 0:
            raise ValueError(f"{func}() kwarg '{name}' must be positive, got {value!r}")


def load(filename: str, **kwargs) -> QasmModule:
    """Loads an OpenQASM program into a `QasmModule` object.

    Args:
        filename (str): The filename of the OpenQASM program to validate.

        **kwargs: Forwarded to :func:`loads`; see it for the supported names.
            ``include_dir`` is consumed here, and is tried before the directory of the
            including file.

    Raises:
        TypeError: If ``filename`` is not a string, or if an unrecognized keyword
            argument is passed.
        FileNotFoundError: If the file does not exist, or an included file is not found.
        ValueError: If a numeric keyword argument is zero or negative.
        ValidationError: If the program fails parsing or semantic validation.

    Returns:
        QasmModule: An object containing the parsed qasm representation along with
            some useful metadata and methods
    """
    if not isinstance(filename, str):
        raise TypeError("Input 'filename' must be of type 'str'.")
    if not os.path.isfile(filename):
        raise FileNotFoundError(f"QASM file '{filename}' not found.")
    # validate here as well so the message names load(), the function the caller invoked
    _validate_kwargs(kwargs, func="load")
    # consumed here, so loads() does not walk the already-inlined program again
    program = process_include_statements(filename, kwargs.pop("include_dir", None))
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

            - **include_dir** (str): Directory holding the program's custom include files.
              A program given as a string has no filesystem location of its own, so this
              is the only way to resolve its includes. Omit it and custom includes are
              left unresolved and passed through, as before; pass it and an include the
              directory does not hold raises a ``ValidationError`` naming it.

            Passing an explicit ``None`` for any of these means "not passed": the
            module default is kept. Pass ``False`` to turn off a boolean kwarg.

    Raises:
        TypeError: If the input is not a string or an `openqasm3.ast.Program` instance,
            if an unrecognized keyword argument is passed, or if a numeric keyword
            argument is not a real number.
        ValueError: If a numeric keyword argument is zero or negative, or if
            ``include_dir`` is passed with an already-parsed `openqasm3.ast.Program`.
        ValidationError: If the program fails parsing or semantic validation, or if a
            custom include is not found in ``include_dir``.

    Returns:
        QasmModule: An object containing the parsed qasm representation along with
            some useful metadata and methods
    """
    _validate_kwargs(kwargs)
    include_dir = kwargs.pop("include_dir", None)
    opaque_gates: set[str] = set()
    if isinstance(program, str):
        if include_dir is not None:
            program = process_include_sources(program, include_dir)
        # after include resolution, so an opaque in a vendor include is rewritten too
        program, opaque_gates = rewrite_opaque_declarations(program)
        try:
            program = openqasm3.parse(program)
        except openqasm3.parser.QASM3ParsingError as err:
            raise ValidationError(f"Failed to parse OpenQASM string: {err}") from err
    elif not isinstance(program, openqasm3.ast.Program):
        raise TypeError("Input quantum program must be of type 'str' or 'openqasm3.ast.Program'.")
    elif include_dir is not None:
        # a parsed Program has no include statements left to resolve
        raise ValueError(
            "loads() kwarg 'include_dir' needs the program as a string; an "
            "'openqasm3.ast.Program' has already been parsed."
        )
    if program.version not in SUPPORTED_QASM_VERSIONS:
        raise ValidationError(
            f"Unsupported OpenQASM version: {program.version}. "
            f"Supported versions are: {SUPPORTED_QASM_VERSIONS}"
        )

    # change version string to x.0 format
    program.version = str(float(program.version))

    qasm_module = Qasm3Module if program.version.startswith("3") else Qasm2Module
    module = qasm_module("main", program)
    module._opaque_gates = opaque_gates
    # `is not None`, not truthiness: a falsy value is a caller value, not an omission.
    # An explicit None means "not passed", so defaults like extern_functions={} and
    # frame_in_def_cal=True are never clobbered.
    for name, attr in _LOADS_KWARG_ATTRS.items():
        if kwargs.get(name) is not None:
            # setattr would happily create a phantom attribute if the module renamed one
            assert hasattr(module, attr), f"module has no attribute '{attr}' for kwarg '{name}'"
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
