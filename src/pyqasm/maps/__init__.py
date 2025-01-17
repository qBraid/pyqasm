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
Module mapping supported QASM gates/operations to lower level gate operations.

"""

from openqasm3.ast import (
    ClassicalDeclaration,
    QuantumBarrier,
    QuantumGate,
    QuantumGateDefinition,
    QuantumMeasurementStatement,
    QuantumReset,
    QubitDeclaration,
    SubroutineDefinition,
)

# Reference : https://openqasm.com/language/classical.html#the-switch-statement
# Paragraph 14
SWITCH_BLACKLIST_STMTS = {
    QubitDeclaration,
    ClassicalDeclaration,
    SubroutineDefinition,
    QuantumGateDefinition,
}

SUPPORTED_QASM_VERSIONS = {"3.0", "3", "2", "2.0"}

QUANTUM_STATEMENTS = (QuantumGate, QuantumBarrier, QuantumReset, QuantumMeasurementStatement)
