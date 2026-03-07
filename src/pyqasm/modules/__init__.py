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
