# Copyright (C) 2024 qBraid
#
# This file is part of the pyqasm
#
# The pyqasm is free software released under the GNU General Public License v3
# or later. You can redistribute and/or modify it under the terms of the GPL v3.
# See the LICENSE file in the project root or <https://www.gnu.org/licenses/gpl-3.0.html>.
#
# THERE IS NO WARRANTY for the pyqasm, as per Section 15 of the GPL v3.

# pylint: disable=too-many-arguments

"""
Module defining Qasm3 Converter elements.

"""
from enum import Enum
from typing import Any, Optional, Union

import numpy as np
from openqasm3.ast import (
    BitType,
    ClassicalDeclaration,
    Include,
    Program,
    QubitDeclaration,
    Statement,
)
from openqasm3.printer import dumps


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
        readonly(bool): Flag indicating if the variable is readonly.

    """

    def __init__(
        self,
        name: str,
        base_type: Any,
        base_size: int,
        dims: Optional[list[int]] = None,
        value: Optional[Union[int, float, np.ndarray]] = None,
        is_constant: bool = False,
        readonly: bool = False,
    ):
        self.name = name
        self.base_type = base_type
        self.base_size = base_size
        self.dims = dims
        self.value = value
        self.is_constant = is_constant
        self.readonly = readonly


class Qasm3Module:
    """
    A module representing an unrolled openqasm quantum program.

    Args:
        name (str): Name of the module.
        module (Module): QIR Module instance.
        num_qubits (int): Number of qubits in the circuit.
        num_clbits (int): Number of classical bits in the circuit.
        original_program (Program): The original openqasm3 program.
        elements (list[Statement]): list of openqasm3 Statements.
    """

    def __init__(
        self,
        name: str,
        num_qubits: int,
        num_clbits: int,
        program: Program,
        statements,
    ):
        self._name = name
        self._num_qubits = num_qubits
        self._num_clbits = num_clbits
        self._statements = statements
        self._unrolled_qasm = ""
        self._unrolled_ast = Program(statements=[Include("stdgates.inc")], version="3")
        self._original_program = program

    @property
    def name(self) -> str:
        """Returns the name of the module."""
        return self._name

    @property
    def num_qubits(self) -> int:
        """Returns the number of qubits in the circuit."""
        return self._num_qubits

    @property
    def num_clbits(self) -> int:
        """Returns the number of classical bits in the circuit."""
        return self._num_clbits

    @property
    def original_program(self) -> Program:
        """Returns the program AST for the original qasm supplied by the user"""
        return self._original_program

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

    @property
    def unrolled_ast(self) -> Program:
        """Returns the unrolled AST for the given module"""
        return self._unrolled_ast

    @unrolled_ast.setter
    def unrolled_ast(self, value: Program):
        """Setter for the unrolled AST"""
        self._unrolled_ast = value

    def unrolled_qasm_as_list(self):
        """Returns the unrolled qasm as a list of lines"""
        return self.unrolled_qasm.split("\n")

    def add_qasm_statement(self, statement: Statement):
        """Add a qasm statement to the unrolled ast

        Args:
            statement (str): The qasm statement to add to the unrolled ast

        Returns:
            None
        """
        self._unrolled_ast.statements.append(statement)

    @classmethod
    def from_program(cls, program: Program):
        """
        Construct a Qasm3Module from a given openqasm3.ast.Program object
        """
        statements: list[Statement] = []

        num_qubits = 0
        num_clbits = 0
        for statement in program.statements:
            if isinstance(statement, QubitDeclaration):
                size = 1
                if statement.size:
                    size = statement.size.value  # type: ignore[attr-defined]
                num_qubits += size
            elif isinstance(statement, ClassicalDeclaration) and isinstance(
                statement.type, BitType
            ):
                size = 1
                if statement.type.size:
                    size = statement.type.size.value  # type: ignore[attr-defined]
                num_clbits += size
            statements.append(statement)

        return cls(
            name="main",
            num_qubits=num_qubits,
            num_clbits=num_clbits,
            program=program,
            statements=statements,
        )

    def accept(self, visitor):
        """Accept a visitor for the module

        Args:
            visitor (BasicQasmVisitor): The visitor to accept
        """
        self.unrolled_ast.statements.extend(visitor.visit_basic_block(self._statements))
        # TODO: some finalizing method here probably
