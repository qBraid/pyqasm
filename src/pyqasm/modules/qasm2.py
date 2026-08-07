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
Defines a module for handling OpenQASM 2.0 programs.
"""

import re
from copy import deepcopy

import openqasm3.ast as qasm3_ast
from openqasm3.ast import Include, Program
from openqasm3.printer import dumps

from pyqasm.exceptions import ValidationError, raise_qasm3_error
from pyqasm.modules.base import QasmModule
from pyqasm.modules.qasm3 import Qasm3Module

# the QASM 2.0 <qop> production: a gate application, a measurement or a reset.
# only these may be the body of an 'if'.
_QOP_STATEMENTS = (
    qasm3_ast.QuantumGate,
    qasm3_ast.QuantumMeasurementStatement,
    qasm3_ast.QuantumReset,
)

# statements the user can write in a conditional body that QASM 2.0 has no form for,
# named by the keyword they wrote rather than by the AST class they parsed into
_NON_QOP_KEYWORDS = {
    qasm3_ast.QuantumBarrier: "barrier",
    qasm3_ast.DelayInstruction: "delay",
    qasm3_ast.Box: "box",
}


class Qasm2Module(QasmModule):
    """
    A module representing an openqasm2 quantum program.

    Args:
        name (str): Name of the module.
        program (Program): The original openqasm2 program.
        statements (list[Statement]): list of openqasm2 Statements.
    """

    def __init__(self, name: str, program: Program) -> None:
        super().__init__(name, program)
        self._unrolled_ast = Program(statements=[], version="2.0")
        self._whitelist_statements = {
            qasm3_ast.BranchingStatement,
            qasm3_ast.QubitDeclaration,
            qasm3_ast.ClassicalDeclaration,
            qasm3_ast.Include,
            qasm3_ast.QuantumGateDefinition,
            qasm3_ast.QuantumGate,
            qasm3_ast.QuantumMeasurement,
            qasm3_ast.QuantumMeasurementStatement,
            qasm3_ast.QuantumReset,
            qasm3_ast.QuantumBarrier,
        }

    def _filter_statements(self) -> None:
        """Filter statements according to the whitelist."""
        for stmt in self._statements:
            stmt_type = type(stmt)
            if stmt_type not in self._whitelist_statements:
                raise ValidationError(f"Statement of type {stmt_type} not supported in QASM 2.0")
            if isinstance(stmt, qasm3_ast.BranchingStatement):
                self._filter_branch_body(stmt)
            # TODO: add more filtering here if needed

    def _filter_branch_body(self, statement: qasm3_ast.BranchingStatement) -> None:
        """Filter the body of a conditional against what QASM 2.0 allows there.

        The QASM 2.0 grammar admits only a ``<qop>`` as the body of an ``if`` --
        a gate application, a measurement or a reset. Everything else, ``barrier``
        included, belongs to a different production and cannot be conditioned. The
        parser does not enforce that, so it is enforced here as a whitelist: a
        blacklist would let through whatever statement kinds it had not enumerated.
        """
        for inner_stmt in [*statement.if_block, *statement.else_block]:
            if isinstance(inner_stmt, _QOP_STATEMENTS):
                continue
            if isinstance(inner_stmt, qasm3_ast.BranchingStatement):
                self._filter_branch_body(inner_stmt)
                continue
            if isinstance(inner_stmt, qasm3_ast.QuantumPhase):
                # not something the user wrote: rzz/rxx decompose to a global phase, so this
                # is only reachable by re-filtering an already-unrolled body (see issue #351)
                raise_qasm3_error(
                    "Global phase is not representable in QASM 2.0, so it cannot appear in "
                    "a conditional body; it is introduced by unrolling gates such as 'rzz' "
                    "and 'rxx'",
                    error_node=inner_stmt,
                    span=inner_stmt.span,
                )
            name = _NON_QOP_KEYWORDS.get(type(inner_stmt))
            described = f"'{name}'" if name else f"statement of type {type(inner_stmt).__name__}"
            raise_qasm3_error(
                f"{described} is not supported as the body of an 'if' in QASM 2.0, which "
                "allows only a gate, measurement or reset there",
                error_node=inner_stmt,
                span=inner_stmt.span,
            )

    def _format_declarations(self, qasm_str: str) -> str:
        """Format the unrolled qasm for declarations in openqasm 2.0 format"""
        for declaration_type, replacement_type in [("qubit", "qreg"), ("bit", "creg")]:
            pattern = rf"{declaration_type}\[(\d+)\]\s+(\w+);"
            replacement = rf"{replacement_type} \2[\1];"
            qasm_str = re.sub(pattern, replacement, qasm_str)
        return qasm_str

    def _qasm_ast_to_str(self, qasm_ast: Program) -> str:
        """Convert the qasm AST to a string."""
        # set the version to 2.0
        qasm_ast.version = "2.0"
        raw_qasm = dumps(qasm_ast, old_measurement=True)
        return self._format_declarations(raw_qasm)

    def to_qasm3(self, as_str: bool = False) -> str | Qasm3Module:
        """Convert the module to openqasm3 format.

        Args:
            as_str (bool): Flag to indicate if the conversion should be to a string
                or to a Qasm3Module object. Default is False.

        Returns:
            str | Qasm3Module: The module in openqasm3 format.
        """
        qasm_program = deepcopy(self._original_program)
        # replace the include with stdgates.inc
        for stmt in qasm_program.statements:
            if isinstance(stmt, Include) and stmt.filename == "qelib1.inc":
                stmt.filename = "stdgates.inc"
                break
        qasm_program.version = "3.0"
        return dumps(qasm_program) if as_str else Qasm3Module(self._name, qasm_program)

    def accept(self, visitor) -> None:
        """Accept a visitor for the module.

        Args:
            visitor (QasmVisitor): The visitor to accept.
        """
        self._filter_statements()
        unrolled_stmt_list = visitor.visit_basic_block(self._statements)
        final_stmt_list = visitor.finalize(unrolled_stmt_list)

        self.unrolled_ast.statements = final_stmt_list
