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
Defines a module for handling OpenQASM 3.0 programs.
"""

from openqasm3.ast import Program
from openqasm3.printer import dumps

from pyqasm.modules.base import QasmModule


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
