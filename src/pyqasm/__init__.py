# Copyright (C) 2025 qBraid
#
# This file is part of PyQASM
#
# PyQASM is free software released under the GNU General Public License v3
# or later. You can redistribute and/or modify it under the terms of the GPL v3.
# See the LICENSE file in the project root or <https://www.gnu.org/licenses/gpl-3.0.html>.
#
# THERE IS NO WARRANTY for PyQASM, as per Section 15 of the GPL v3.

"""
Top level module containing the main PyQASM functionality.

.. currentmodule:: pyqasm

Functions
----------

.. autosummary::
   :toctree: ../stubs/

   load
   loads
   dump
   dumps

Classes
---------

.. autosummary::
   :toctree: ../stubs/

   Qasm3Module
   Qasm2Module
   QasmModule

Exceptions
-----------

.. autosummary::
   :toctree: ../stubs/

   PyQasmError
   ValidationError
   QasmParsingError

"""
import warnings
from importlib.metadata import version

try:
    # Injected in _version.py during the build process.
    from ._version import __version__  # type: ignore
except (ImportError, ModuleNotFoundError):  # pragma: no cover
    warnings.warn("Importing 'pyqasm' outside a proper installation.", UserWarning)
    __version__ = version("pyqasm")

from .entrypoint import dump, dumps, load, loads
from .exceptions import PyQasmError, QasmParsingError, ValidationError
from .modules import Qasm2Module, Qasm3Module, QasmModule

__all__ = [
    "PyQasmError",
    "ValidationError",
    "QasmParsingError",
    "load",
    "loads",
    "dump",
    "dumps",
    "QasmModule",
    "Qasm2Module",
    "Qasm3Module",
    "__version__",
]
