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
Module with utility functions for Pulse visitor

"""
import re
from typing import Any, Sequence

import openqasm3.ast as qasm3_ast

from pyqasm.exceptions import raise_qasm3_error


class PulseUtils:
    """Class with utility functions for Pulse visitor"""

    @staticmethod
    def format_calibration_body(result):
        """Format the calibration body"""
        # pylint: disable=import-outside-toplevel
        from openpulse.printer import dumps as pulse_dumps

        body_str = "".join([pulse_dumps(stmt) for stmt in result])
        body_str = re.sub(r"\n(?![\s])", "\n ", body_str)
        body_str = re.sub(r"\n +$", "\n", body_str)
        lines = body_str.splitlines(keepends=True)
        for i, line in enumerate(lines):
            if line.strip() != "":
                if not line.startswith(" "):
                    lines[i] = " " + line
                break
        body_str = "".join(lines)
        return body_str

    @staticmethod
    def process_qubits_for_openpulse_gate(
        operation: Any,
        gate_op: str,
        openpulse_qubit_map: dict,
        global_qreg_size_map: dict,
    ) -> Sequence[qasm3_ast.QuantumGate]:
        """
        Process qubits for OpenPulse gates, handling special qubit
        identifiers and register expansion.

        Args:
            operation: The quantum gate operation to process
            gate_op: The name of the gate operation
            openpulse_qubit_map: Mapping of gates to their valid qubits
            global_qreg_size_map: Mapping of qubit register names to their sizes

        Returns:
            List of processed quantum gate operations

        Raises:
            Qasm3Error: If gate is not found in calibration or qubit is invalid
        """
        stmts: list[qasm3_ast.QuantumGate] = []

        for i, qubit in enumerate(operation.qubits):
            qubit_id = qubit.name.name if hasattr(qubit.name, "name") else qubit.name
            if qubit_id.startswith("$") and qubit_id[1:].isdigit():
                if (
                    gate_op not in openpulse_qubit_map
                    or qubit_id not in openpulse_qubit_map[gate_op]
                ):
                    msg = (
                        f"Openpulse gate '{gate_op}' not found in calibration definition"
                        if gate_op not in openpulse_qubit_map
                        else f"Invalid qubit '{qubit_id}' for gate '{gate_op}'"
                    )
                    raise_qasm3_error(
                        msg,
                        error_node=operation,
                        span=operation.span,
                    )
                operation.qubits[i] = qasm3_ast.IndexedIdentifier(
                    name=qasm3_ast.Identifier("__PYQASM_QUBITS__"),
                    indices=[[qasm3_ast.IntegerLiteral(int(qubit_id[1:]))]],
                )
                stmts.append(operation)
            elif qubit_id in global_qreg_size_map:
                stmts.extend(
                    qasm3_ast.QuantumGate(
                        name=qasm3_ast.Identifier(gate_op),
                        qubits=[
                            qasm3_ast.IndexedIdentifier(
                                name=qasm3_ast.Identifier("__PYQASM_QUBITS__"),
                                indices=[[qasm3_ast.IntegerLiteral(j)]],
                            )
                        ],
                        arguments=operation.arguments,
                        modifiers=operation.modifiers,
                    )
                    for j in range(global_qreg_size_map[qubit_id])
                )
            else:
                raise_qasm3_error(
                    f"Qubit register '{qubit_id}' is not declared",
                    error_node=operation,
                    span=operation.span,
                )

        return stmts
