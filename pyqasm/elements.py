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
Module defining Qasm3 Converter elements.

"""
import re
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Optional, Union

import numpy as np
import openqasm3.ast as qasm3_ast
from openqasm3.ast import Include, Program, Statement
from openqasm3.printer import dumps

from .exceptions import ValidationError


class InversionOp(Enum):
    """
    Enum for specifying the inversion action of a gate.
    """

    NO_OP = 1
    INVERT_ROTATION = 2


class Context(Enum):
    """
    Enum for the different contexts in Qasm.
    """

    GLOBAL = "global"
    BLOCK = "block"
    FUNCTION = "function"
    GATE = "gate"


# pylint: disable-next=too-many-instance-attributes
class Variable:
    """
    Class representing an openqasm variable.

    Args:
        name (str): Name of the variable.
        base_type (Any): Base type of the variable.
        base_size (int): Base size of the variable.
        dims (list[int]): Dimensions of the variable.
        value (Optional[Union[int, float, list]]): Value of the variable.
        is_constant (bool): Flag indicating if the variable is constant.
        is_register (bool): Flag indicating if the variable is a register.
        readonly(bool): Flag indicating if the variable is readonly.

    """

    # pylint: disable-next=too-many-arguments,too-many-positional-arguments
    def __init__(
        self,
        name: str,
        base_type: Any,
        base_size: int,
        dims: Optional[list[int]] = None,
        value: Optional[Union[int, float, np.ndarray]] = None,
        is_constant: bool = False,
        is_register: bool = False,
        readonly: bool = False,
    ):
        self.name = name
        self.base_type = base_type
        self.base_size = base_size
        self.dims = dims
        self.value = value
        self.is_constant = is_constant
        self.is_register = is_register
        self.readonly = readonly

    def __repr__(self) -> str:
        return (
            f"Variable(name = {self.name}, base_type = {self.base_type}, "
            f"base_size = {self.base_size}, dimensions = {self.dims}, "
            f"value = {self.value}, is_constant = {self.is_constant}, "
            f"readonly = {self.readonly}, is_register = {self.is_register})"
        )


class QasmModule(ABC):
    """Abstract class for a Qasm module

    Args:
        name (str): Name of the module.
        program (Program): The original openqasm3 program.
        statements (list[Statement]): list of openqasm3 Statements.
    """

    def __init__(self, name: str, program: Program, statements: list):
        self._name = name
        self._original_program = program
        self._statements = statements
        self._num_qubits = 0
        self._num_clbits = 0
        self._unrolled_qasm = ""
        self._unrolled_ast = Program(statements=[])

    @property
    def name(self) -> str:
        """Returns the name of the module."""
        return self._name

    @property
    def num_qubits(self) -> int:
        """Returns the number of qubits in the circuit."""
        return self._num_qubits

    def add_qubits(self, num_qubits: int):
        """Add qubits to the module

        Args:
            num_qubits (int): The number of qubits to add to the module

        Returns:
            None
        """
        self._num_qubits += num_qubits

    @property
    def num_clbits(self) -> int:
        """Returns the number of classical bits in the circuit."""
        return self._num_clbits

    @property
    def original_program(self) -> Program:
        """Returns the program AST for the original qasm supplied by the user"""
        return self._original_program

    @property
    def unrolled_ast(self) -> Program:
        """Returns the unrolled AST for the module"""
        return self._unrolled_ast

    @unrolled_ast.setter
    def unrolled_ast(self, value: Program):
        """Setter for the unrolled AST"""
        self._unrolled_ast = value

    @property
    @abstractmethod
    def unrolled_qasm(self) -> str:
        """Abstract property for unrolled_qasm"""

    @unrolled_qasm.setter
    @abstractmethod
    def unrolled_qasm(self, value: str):
        """Abstract setter for unrolled_qasm"""

    def add_classical_bits(self, num_clbits: int):
        """Add classical bits to the module

        Args:
            num_clbits (int): The number of classical bits to add to the module

        Returns:
            None
        """
        self._num_clbits += num_clbits

    @classmethod
    def from_program(cls, program: Program):
        """
        Construct a Qasm3Module from a given openqasm3.ast.Program object
        """
        statements: list[Statement] = []

        for statement in program.statements:
            statements.append(statement)

        return cls(
            name="main",
            program=program,
            statements=statements,
        )

    @abstractmethod
    def accept(self, visitor):
        """Accept a visitor for the module

        Args:
            visitor (BasicQasmVisitor): The visitor to accept
        """


class Qasm2Module(QasmModule):
    """
    A module representing an unrolled openqasm2 quantum program.

    Args:
        name (str): Name of the module.
        program (Program): The original openqasm2 program.
        statements (list[Statement]): list of openqasm2 Statements.
    """

    def __init__(
        self,
        name: str,
        program: Program,
        statements: list,
    ):
        super().__init__(name, program, statements)
        self._unrolled_ast = Program(statements=[Include("stdgates.inc")], version="2")
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

    def _format_declarations(self):
        """Format the unrolled qasm for declarations in openqasm 2.0 format"""
        qasm = self._unrolled_qasm
        for declaration_type, replacement_type in [("qubit", "qreg"), ("bit", "creg")]:
            pattern = rf"{declaration_type}\[(\d+)\]\s+(\w+);"
            replacement = rf"{replacement_type} \2[\1];"
            qasm = re.sub(pattern, replacement, qasm)

        self._unrolled_qasm = qasm

    @property
    def unrolled_qasm(self) -> str:
        """Returns the unrolled qasm for the given module"""
        if self._unrolled_qasm == "":
            self._unrolled_qasm = dumps(self._unrolled_ast, old_measurement=True)
            self._format_declarations()
        return self._unrolled_qasm

    @unrolled_qasm.setter
    def unrolled_qasm(self, value: str):
        """Setter for the unrolled qasm"""
        self._unrolled_qasm = value

    def accept(self, visitor):
        """Accept a visitor for the module

        Args:
            visitor (BasicQasmVisitor): The visitor to accept
        """
        self._filter_statements()
        unrolled_stmt_list = visitor.visit_basic_block(self._statements)
        self.unrolled_ast.statements.extend(unrolled_stmt_list)
        # TODO: some finalizing method here probably


class Qasm3Module(QasmModule):
    """
    A module representing an unrolled openqasm3 quantum program.

    Args:
        name (str): Name of the module.
        program (Program): The original openqasm3 program.
        statements (list[Statement]): list of openqasm3 Statements.
    """

    def __init__(
        self,
        name: str,
        program: Program,
        statements: list,
    ):
        super().__init__(name, program, statements)
        self._unrolled_ast = Program(statements=[Include("stdgates.inc")], version="3")

    @property
    def unrolled_qasm(self) -> str:
        """Returns the unrolled qasm for the given module"""
        if self._unrolled_qasm == "":
            self._unrolled_qasm = dumps(self._unrolled_ast)
        return self._unrolled_qasm

    @unrolled_qasm.setter
    def unrolled_qasm(self, value: str):
        """Setter for the unrolled qasm"""
        self._unrolled_qasm = value

    def accept(self, visitor):
        """Accept a visitor for the module

        Args:
            visitor (BasicQasmVisitor): The visitor to accept
        """
        unrolled_stmt_list = visitor.visit_basic_block(self._statements)
        self.unrolled_ast.statements.extend(unrolled_stmt_list)
        # TODO: some finalizing method here probably
