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
from abc import ABCMeta, abstractmethod
from enum import Enum
from typing import Any, Optional, Union

import numpy as np
from openqasm3.ast import BitType, ClassicalDeclaration, Program, QubitDeclaration, Statement


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


class _ProgramElement(metaclass=ABCMeta):
    """Abstract class for program elements"""

    @classmethod
    def from_element_list(cls, elements):
        """Create a list of elements from a list of elements"""
        return [cls(elem) for elem in elements]

    @abstractmethod
    def accept(self, visitor):
        """Accept a visitor for the element"""


class _Register(_ProgramElement):

    def __init__(self, register: Union[QubitDeclaration, ClassicalDeclaration]):
        self._register: Union[QubitDeclaration, ClassicalDeclaration] = register

    def accept(self, visitor):
        visitor.visit_register(self._register)

    def __str__(self) -> str:
        return f"Register({self._register})"


class _Statement(_ProgramElement):

    def __init__(self, statement: Statement):
        self._statement = statement

    def accept(self, visitor):
        visitor.visit_statement(self._statement)

    def __str__(self) -> str:
        return f"Statement({self._statement})"


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
        elements,
    ):
        self._name = name
        self._num_qubits = num_qubits
        self._num_clbits = num_clbits
        self._elements = elements
        self._unrolled_qasm = ""
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
        return self._unrolled_qasm

    @unrolled_qasm.setter
    def unrolled_qasm(self, value: str):
        """Setter for the unrolled qasm"""
        self._unrolled_qasm = value

    def unrolled_qasm_as_list(self):
        """Returns the unrolled qasm as a list of lines"""
        return self.unrolled_qasm.split("\n")

    def add_qasm_statement(self, statement: str):
        """Add a qasm statement to the unrolled qasm

        Args:
            statement (str): The qasm statement to add to the unrolled qasm

        Returns:
            None
        """

        if len(self.unrolled_qasm) == 0:
            self.unrolled_qasm = "OPENQASM 3.0;\n"
            self.unrolled_qasm += 'include "stdgates.inc";\n'
            # add comments about total number of qubits and clbits
            self.unrolled_qasm += f"// Total number of qubits: {self.num_qubits}\n"
            self.unrolled_qasm += f"// Total number of clbits: {self.num_clbits}\n"

        self.unrolled_qasm += statement

    @classmethod
    def from_program(cls, program: Program):
        """
        Construct a Qasm3Module from a given openqasm3.ast.Program object
        """
        elements: list[Union[_Register, _Statement]] = []

        num_qubits = 0
        num_clbits = 0
        for statement in program.statements:
            if isinstance(statement, QubitDeclaration):
                size = 1
                if statement.size:
                    size = statement.size.value  # type: ignore[attr-defined]
                num_qubits += size
                elements.append(_Register(statement))

            elif isinstance(statement, ClassicalDeclaration) and isinstance(
                statement.type, BitType
            ):
                size = 1
                if statement.type.size:
                    size = statement.type.size.value  # type: ignore[attr-defined]
                num_clbits += size
                elements.append(_Register(statement))
                # as bit arrays are just 0 / 1 values, we can treat them as
                # classical variables too. Thus, need to add them to normal
                # statements too.
                elements.append(_Statement(statement))
            else:
                elements.append(_Statement(statement))

        return cls(
            name="main",
            num_qubits=num_qubits,
            num_clbits=num_clbits,
            program=program,
            elements=elements,
        )

    def accept(self, visitor):
        """Accept a visitor for the module

        Args:
            visitor (BasicQasmVisitor): The visitor to accept
        """
        for element in self._elements:
            element.accept(visitor)

        # TODO: some finalizing method here probably
