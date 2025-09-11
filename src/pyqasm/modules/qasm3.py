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
Defines a module for handling OpenQASM 3.0 programs.
"""

import openqasm3.ast as qasm3_ast
from openqasm3.ast import Program
from openqasm3.printer import dumps

from pyqasm.modules.base import QasmModule, offset_statement_qubits


class Qasm3Module(QasmModule):
    """
    A module representing an openqasm3 quantum program.

    Args:
        name (str): Name of the module.
        program (Program): The original openqasm3 program.
        statements (list[Statement]): list of openqasm3 Statements.
    """

    def __init__(self, name: str, program: Program):
        super().__init__(name, program)
        self._unrolled_ast = Program(statements=[], version="3.0")

    def _qasm_ast_to_str(self, qasm_ast):
        """Convert the qasm AST to a string"""
        # set the version to 3.0
        qasm_ast.version = "3.0"
        return dumps(qasm_ast)

    def accept(self, visitor):
        """Accept a visitor for the module

        Args:
            visitor (QasmVisitor): The visitor to accept
        """
        unrolled_stmt_list = visitor.visit_basic_block(self._statements)
        final_stmt_list = visitor.finalize(unrolled_stmt_list)

        self._unrolled_ast.statements = final_stmt_list

    def merge(self, other: QasmModule, device_qubits: int | None = None) -> QasmModule:
        """Merge two modules as OpenQASM 3.0 without mixing versions.

        If ``other`` is QASM2, it will be converted to QASM3 before merging.
        The merged program keeps version "3.0".
        """
        if not isinstance(other, QasmModule):
            raise TypeError(f"Expected QasmModule instance, got {type(other).__name__}")

        # Convert right to QASM3 if it supports conversion; otherwise copy
        convert = getattr(other, "to_qasm3", None)
        right_mod = convert(as_str=False) if callable(convert) else other.copy()  # type: ignore[assignment]

        left_mod = self.copy()

        # Unroll with consolidation so both use __PYQASM_QUBITS__
        unroll_kwargs: dict[str, object] = {"consolidate_qubits": True}
        if device_qubits is not None:
            unroll_kwargs["device_qubits"] = device_qubits

        left_mod.unroll(**unroll_kwargs)
        right_mod.unroll(**unroll_kwargs)

        left_qubits = left_mod.num_qubits
        total_qubits = left_qubits + right_mod.num_qubits

        merged_program = Program(statements=[], version="3.0")

        # Unique includes first
        include_names: list[str] = []
        for module in (left_mod, right_mod):
            for stmt in module.unrolled_ast.statements:
                if isinstance(stmt, qasm3_ast.Include) and stmt.filename not in include_names:
                    include_names.append(stmt.filename)
        for name in include_names:
            merged_program.statements.append(qasm3_ast.Include(filename=name))

        # Consolidated qubit declaration
        merged_program.statements.append(
            qasm3_ast.QubitDeclaration(
                size=qasm3_ast.IntegerLiteral(value=total_qubits),
                qubit=qasm3_ast.Identifier(name="__PYQASM_QUBITS__"),
            )
        )

        # Append left ops
        for stmt in left_mod.unrolled_ast.statements:
            if isinstance(stmt, (qasm3_ast.QubitDeclaration, qasm3_ast.Include)):
                continue
            merged_program.statements.append(stmt)

        # Append right ops with index offset
        for stmt in right_mod.unrolled_ast.statements:
            if isinstance(stmt, (qasm3_ast.QubitDeclaration, qasm3_ast.Include)):
                continue
            # right_mod is a copy, so it's safe to modify statements in place
            offset_statement_qubits(stmt, left_qubits)
            merged_program.statements.append(stmt)

        merged_module = Qasm3Module(name=f"{left_mod.name}_merged_{right_mod.name}", program=merged_program)
        merged_module.unrolled_ast = Program(statements=list(merged_program.statements), version="3.0")
        merged_module._external_gates = list({*left_mod._external_gates, *right_mod._external_gates})
        merged_module._user_operations = list(left_mod.history) + list(right_mod.history)
        merged_module._user_operations.append(f"merge(other={right_mod.name})")
        merged_module.validate()
        return merged_module
