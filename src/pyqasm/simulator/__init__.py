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
Module containing the PyQASM statevector simulator.

.. currentmodule:: pyqasm.simulator

Classes
---------

.. autosummary::
   :toctree: ../stubs/

   Simulator
   SimulatorResult

"""

from .statevector import Simulator, SimulatorResult

__all__ = ["Simulator", "SimulatorResult"]
