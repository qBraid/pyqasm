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
   draw

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

   LoopLimitExceededError
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
from .exceptions import LoopLimitExceededError, PyQasmError, QasmParsingError, ValidationError
from .modules import Qasm2Module, Qasm3Module, QasmModule
from .printer import draw

__all__ = [
    "PyQasmError",
    "ValidationError",
    "LoopLimitExceededError",
    "QasmParsingError",
    "load",
    "loads",
    "dump",
    "dumps",
    "draw",
    "QasmModule",
    "Qasm2Module",
    "Qasm3Module",
    "__version__",
]
