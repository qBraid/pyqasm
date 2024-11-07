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
Sub modules for handling different versions of OpenQASM.

.. currentmodule:: pyqasm.modules

Classes
---------

.. autosummary::
   :toctree: ../stubs/

   Qasm3Module
   Qasm2Module
   QasmModule

"""

from .base import QasmModule
from .qasm2 import Qasm2Module
from .qasm3 import Qasm3Module

__all__ = [
    "QasmModule",
    "Qasm2Module",
    "Qasm3Module",
]
