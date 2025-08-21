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
    def process_qubits_for_openpulse_gate(  # pylint: disable=too-many-arguments
        operation: Any,
        gate_op: str,
        openpulse_qubit_map: dict,
        global_qreg_size_map: dict,
        pulse_gates_qubits_frame_map: list[dict[str, dict[str, set[Any]]]],
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
        _qubit_set = set()
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
                _qubit_set.add(int(qubit_id[1:]))
                operation.qubits[i] = qasm3_ast.IndexedIdentifier(
                    name=qasm3_ast.Identifier("__PYQASM_QUBITS__"),
                    indices=[[qasm3_ast.IntegerLiteral(int(qubit_id[1:]))]],
                )
                stmts = [operation]
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

        if _qubit_set:
            _gate_qubits_map: dict[str, set[int]] = {operation.name.name: _qubit_set}
            PulseUtils.process_frame_collision_check(
                operation,
                gate_op,
                pulse_gates_qubits_frame_map,
                _gate_qubits_map,
            )

        return stmts

    @staticmethod
    def process_frame_collision_check(
        operation: Any,
        gate_op: str,
        pulse_gates_qubits_frame_map: list[dict[str, dict[str, set[Any]]]],
        current_gate_qubits: dict[str, set[int]],
    ) -> None:
        """
        Process frame collision check
        """
        current_gate_qubit_set = current_gate_qubits[gate_op]
        for _gate_set in pulse_gates_qubits_frame_map:
            if gate_op in _gate_set and _gate_set[gate_op]["qubits"] == current_gate_qubit_set:
                return
        # pylint: disable-next=too-many-nested-blocks
        if len(current_gate_qubit_set) > 1:
            defcal_frame_list = []
            for qubit in current_gate_qubit_set:
                single_qubit_set = {qubit}
                gate_found = False

                for gate_set in pulse_gates_qubits_frame_map:
                    if gate_op in gate_set and gate_set[gate_op]["qubits"] == single_qubit_set:
                        gate_found = True
                        frames = gate_set[gate_op]["frames"]
                        for frame in frames:
                            if frame in defcal_frame_list:
                                raise_qasm3_error(
                                    f"'Frame Collision' occured for frame '{frame}' "
                                    f"in '{gate_op}' gate",
                                    error_node=operation,
                                    span=operation.span,
                                )
                            defcal_frame_list.append(frame)
                        break

                if not gate_found:
                    raise_qasm3_error(
                        f"Invalid qubit order for gate '{gate_op}:{current_gate_qubit_set}'",
                        error_node=operation,
                        span=operation.span,
                    )
