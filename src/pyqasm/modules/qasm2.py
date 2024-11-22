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
Defines a module for handling OpenQASM 2.0 programs.
"""

import re
from copy import deepcopy
from typing import Union

import openqasm3.ast as qasm3_ast
from openqasm3.ast import Include, Program
from openqasm3.printer import dumps

from pyqasm.exceptions import ValidationError
from pyqasm.modules.base import QasmModule
from pyqasm.modules.qasm3 import Qasm3Module


class Qasm2Module(QasmModule):
    """
    A module representing an openqasm2 quantum program.

    Args:
        name (str): Name of the module.
        program (Program): The original openqasm2 program.
        statements (list[Statement]): list of openqasm2 Statements.
    """

    def __init__(self, name: str, program: Program):
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

    def _filter_statements(self):
        """Filter statements according to the whitelist"""
        for stmt in self._statements:
            stmt_type = type(stmt)
            if stmt_type not in self._whitelist_statements:
                raise ValidationError(f"Statement of type {stmt_type} not supported in QASM 2.0")
            # TODO: add more filtering here if needed

    def _format_declarations(self, qasm_str):
        """Format the unrolled qasm for declarations in openqasm 2.0 format"""
        for declaration_type, replacement_type in [("qubit", "qreg"), ("bit", "creg")]:
            pattern = rf"{declaration_type}\[(\d+)\]\s+(\w+);"
            replacement = rf"{replacement_type} \2[\1];"
            qasm_str = re.sub(pattern, replacement, qasm_str)
        return qasm_str

    def _qasm_ast_to_str(self, qasm_ast):
        """Convert the qasm AST to a string"""
        # set the version to 2.0
        qasm_ast.version = "2.0"
        raw_qasm = dumps(qasm_ast, old_measurement=True)
        return self._format_declarations(raw_qasm)

    def to_qasm3(self, as_str: bool = False) -> Union[str, Qasm3Module]:
        """Convert the module to openqasm3 format

        Args:
            as_str (bool): Flag to indicate if the conversion should be to a string
                           or to a Qasm3Module object.
                           Default is False.

        Returns:
            Union[str, Qasm3Module]: The module in openqasm3 format.
        """
        qasm_program = deepcopy(self._original_program)
        # replace the include with stdgates.inc
        for stmt in qasm_program.statements:
            if isinstance(stmt, Include) and stmt.filename == "qelib1.inc":
                stmt.filename = "stdgates.inc"
                break
        qasm_program.version = "3.0"
        return dumps(qasm_program) if as_str else Qasm3Module(self._name, qasm_program)

    def accept(self, visitor):
        """Accept a visitor for the module

        Args:
            visitor (QasmVisitor): The visitor to accept
        """
        self._filter_statements()
        unrolled_stmt_list = visitor.visit_basic_block(self._statements)
        final_stmt_list = visitor.finalize(unrolled_stmt_list)

        self.unrolled_ast.statements = final_stmt_list
