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
Top level module containing the main PyQASM functionality.

.. currentmodule:: pyqasm

Functions
----------

.. autosummary::
   :toctree: ../stubs/

   validate
   unroll
   load

Classes
---------

.. autosummary::
   :toctree: ../stubs/

   Qasm3Module

Exceptions
-----------

.. autosummary::
   :toctree: ../stubs/

   PyQasmError
   ValidationError

"""
import warnings

try:
    # Injected in _version.py during the build process.
    from ._version import __version__  # type: ignore
except ImportError:  # pragma: no cover
    warnings.warn("Importing 'pyqasm' outside a proper installation.")
    __version__ = "dev"

from .entrypoint import load
from .exceptions import PyQasmError, QasmParsingError, ValidationError
from .modules import Qasm2Module, Qasm3Module

__all__ = [
    "PyQasmError",
    "ValidationError",
    "QasmParsingError",
    "load",
    "Qasm2Module",
    "Qasm3Module",
    "__version__",
]
