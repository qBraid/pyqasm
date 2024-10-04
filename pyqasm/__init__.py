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
Top level module containing the main PyQASM functionality.

.. currentmodule:: pyqasm

Functions
----------

.. autosummary::
   :toctree: ../stubs/

   validate

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
except ImportError:
    warnings.warn("Importing 'pyqasm' outside a proper installation.")
    __version__ = "dev"

from .exceptions import PyQasmError, ValidationError
from .validate import validate

__all__ = [
    "PyQasmError",
    "ValidationError",
    "validate",
    "__version__",
]
