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

from openqasm3.ast import Pragma, Program, QASMNode
from openqasm3.printer import Printer, PrinterState

from pyqasm.modules.base import QasmModule, QasmVisitor


class Qasm3Printer(Printer):
    """OpenQASM 3 printer that writes pragmas in their '#pragma' form.

    The upstream printer emits the bare 'pragma' keyword. Both forms parse, but tools
    consuming the output (e.g. Amazon Braket for '#pragma braket verbatim') expect the
    hashed form, which is also what they emit.
    """

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
        return dumps(qasm_ast)

    def accept(self, visitor: QasmVisitor) -> None:
        """Accept a visitor for the module.

        Args:
            visitor (QasmVisitor): The visitor to accept.
        """
        unrolled_stmt_list = visitor.visit_basic_block(self._statements)
        final_stmt_list = visitor.finalize(unrolled_stmt_list)

        self._unrolled_ast.statements = self.finalize(final_stmt_list)  # type: ignore[assignment]
