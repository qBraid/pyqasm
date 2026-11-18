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

import io
from typing import Any

from openqasm3 import properties
from openqasm3.ast import (
    BinaryExpression,
    BinaryOperator,
    IntegerLiteral,
    Pragma,
    Program,
    QASMNode,
    QuantumGate,
    QuantumPhase,
    UnaryExpression,
)
from openqasm3.printer import Printer, PrinterState

from pyqasm.modules.base import QasmModule, QasmVisitor

_COMPACT_OPERATORS = frozenset({BinaryOperator["*"], BinaryOperator["/"], BinaryOperator["**"]})


def _int_literal_arithmetic(expression: QASMNode) -> bool:
    """Whether an expression combines only integer literals with + - * / % **."""
    if isinstance(expression, IntegerLiteral):
        return True
    if isinstance(expression, UnaryExpression):
        return expression.op.name == "-" and _int_literal_arithmetic(expression.expression)
    if isinstance(expression, BinaryExpression):
        return expression.op.name in ("+", "-", "*", "/", "%", "**") and all(
            _int_literal_arithmetic(operand) for operand in (expression.lhs, expression.rhs)
        )
    return False


class Qasm3Printer(Printer):
    """OpenQASM 3 printer with three changes to the upstream printer.

    Pragmas are written in their '#pragma' form. The upstream printer emits the bare
    'pragma' keyword. Both forms parse, but tools consuming the output (e.g. Amazon
    Braket for '#pragma braket verbatim') expect the hashed form.

    With ``compact_gate_arguments``, gate arguments are written without spaces around
    '*', '/' and '**': ``rx(pi/2)`` instead of ``rx(pi / 2)``. Some vendors (e.g. Diraq)
    match rotation angles textually and only accept the compact spelling.

    With ``real_literal_division``, a division between integer literals is written with
    float literals: ``rx(1.0 / 2.0)`` instead of ``rx(1 / 2)``. A program converted from
    OpenQASM 2, which has no integer type, keeps its real division this way.
    """

    def __init__(
        self,
        stream: io.TextIOBase,
        *,
        compact_gate_arguments: bool = False,
        real_literal_division: bool = False,
        **kwargs: Any,
    ) -> None:
        """Create a printer.

        Args:
            stream (io.TextIOBase): The stream to write to.
            compact_gate_arguments (bool): Drop the spaces around '*', '/' and '**' in gate
                arguments. Defaults to False.
            real_literal_division (bool): Write the integer literals of a division between
                integer literals as floats. Defaults to False.
            **kwargs (Any): Printer options, forwarded to `openqasm3.printer.Printer`.
        """
        super().__init__(stream, **kwargs)
        self.compact_gate_arguments = compact_gate_arguments
        # true only while a gate call prints, so classical expressions keep their spacing
        self._printing_gate_expr = False
        self.real_literal_division = real_literal_division
        # true only while a division between integer literals prints
        self._printing_real_division = False

    def visit_QuantumGate(self, node: QuantumGate, context: PrinterState) -> None:
        """Write a gate call, marking its expressions as gate arguments."""
        self._printing_gate_expr = True
        try:
            super().visit_QuantumGate(node, context)
        finally:
            self._printing_gate_expr = False

    def visit_QuantumPhase(self, node: QuantumPhase, context: PrinterState) -> None:
        """Write a gphase call, marking its expressions as gate arguments."""
        self._printing_gate_expr = True
        try:
            super().visit_QuantumPhase(node, context)
        finally:
            self._printing_gate_expr = False

    def visit_BinaryExpression(self, node: BinaryExpression, context: PrinterState) -> None:
        """Write a binary expression, compacting the operator inside gate arguments.

        Mirrors the upstream method, which hardcodes the spaces around the operator.
        """
        if (
            self.real_literal_division
            and not self._printing_real_division
            and node.op.name == "/"
            and _int_literal_arithmetic(node)
        ):
            self._printing_real_division = True
            try:
                self.visit_BinaryExpression(node, context)
            finally:
                self._printing_real_division = False
            return
        our_precedence = properties.precedence(node)
        # All AST nodes that are built into BinaryExpression are currently left associative.
        if properties.precedence(node.lhs) < our_precedence:
            self.stream.write("(")
            self.visit(node.lhs, context)
            self.stream.write(")")
        else:
            self.visit(node.lhs, context)
        compact = (
            self.compact_gate_arguments
            and self._printing_gate_expr
            and node.op in _COMPACT_OPERATORS
        )
        self.stream.write(node.op.name if compact else f" {node.op.name} ")
        if properties.precedence(node.rhs) <= our_precedence:
            self.stream.write("(")
            self.visit(node.rhs, context)
            self.stream.write(")")
        else:
            self.visit(node.rhs, context)

    def visit_IntegerLiteral(self, node: IntegerLiteral, context: PrinterState) -> None:
        """Write an integer literal, as a float inside a division that stays real."""
        if self._printing_real_division:
            self.stream.write(str(float(node.value)))
        else:
            super().visit_IntegerLiteral(node, context)

    def visit_Pragma(self, node: Pragma, context: PrinterState) -> None:
        """Write a pragma node, keeping the '#' that the upstream printer drops.

        Args:
            node (Pragma): The pragma to write.
            context (PrinterState): The printer state, carrying the current indent.
        """
        self._start_line(context)
        self.stream.write(f"#pragma {node.command}")
        self._end_line(context)


def dumps(node: QASMNode, **kwargs: Any) -> str:
    """Return the OpenQASM 3 string representation of ``node``.

    Args:
        node (QASMNode): The node to print, usually a Program.
        **kwargs (Any): Printer options, forwarded to `openqasm3.printer.Printer`.

    Returns:
        str: The printed program.
    """
    out = io.StringIO()
    Qasm3Printer(out, **kwargs).visit(node)
    return out.getvalue()


class Qasm3Module(QasmModule):
    """
    A module representing an openqasm3 quantum program.

    Args:
        name (str): Name of the module.
        program (Program): The original openqasm3 program.
        statements (list[Statement]): list of openqasm3 Statements.
    """

    def __init__(self, name: str, program: Program) -> None:
        super().__init__(name, program)
        self._unrolled_ast = Program(statements=[], version="3.0")

    def _qasm_ast_to_str(self, qasm_ast: Program) -> str:
        """Convert the qasm AST to a string."""
        # set the version to 3.0
        qasm_ast.version = "3.0"
        return dumps(
            qasm_ast,
            compact_gate_arguments=self._compact_gate_arguments,
            real_literal_division=self._real_literal_division,
        )

    def accept(self, visitor: QasmVisitor) -> None:
        """Accept a visitor for the module.

        Args:
            visitor (QasmVisitor): The visitor to accept.
        """
        unrolled_stmt_list = visitor.visit_basic_block(self._statements)
        final_stmt_list = visitor.finalize(unrolled_stmt_list)

        self._unrolled_ast.statements = self.finalize(final_stmt_list)  # type: ignore[assignment]
