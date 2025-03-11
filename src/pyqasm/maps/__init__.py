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
