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
Module defining Qasm modules
"""

import re
from abc import ABC, abstractmethod
from copy import deepcopy
from typing import Optional

import openqasm3.ast as qasm3_ast
from openqasm3.ast import Include, Program, Statement
from openqasm3.printer import dumps

from .elements import ClbitDepthNode, QubitDepthNode
from .exceptions import UnrollError, ValidationError
from .visitor import QasmVisitor


class QasmModule(ABC):  # pylint: disable=too-many-instance-attributes
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
        self._num_qubits = -1
        self._qubit_depths: dict[tuple[str, int], QubitDepthNode] = {}
        self._num_clbits = -1
        self._clbit_depths: dict[tuple[str, int], ClbitDepthNode] = {}
        self._has_measurements: Optional[bool] = None
        self._validated_program = False
        self._unrolled_qasm = ""
        self._unrolled_ast = Program(statements=[Include("stdgates.inc")])

    @property
    def name(self) -> str:
        """Returns the name of the module."""
        return self._name

    @property
    def num_qubits(self) -> int:
        """Returns the number of qubits in the circuit."""
        if self._num_qubits == -1:
            self._num_qubits = 0
            self.validate()
        return self._num_qubits

    @num_qubits.setter
    def num_qubits(self, value: int):
        """Setter for the number of qubits"""
        self._num_qubits = value

    def _add_qubits(self, num_qubits: int):
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
        if self._num_clbits == -1:
            self._num_clbits = 0
            self.validate()
        return self._num_clbits

    @num_clbits.setter
    def num_clbits(self, value: int):
        """Setter for the number of classical bits"""
        self._num_clbits = value

    def _add_classical_bits(self, num_clbits: int):
        """Add classical bits to the module

        Args:
            num_clbits (int): The number of classical bits to add to the module

        Returns:
            None
        """
        self._num_clbits += num_clbits

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
    def unrolled_qasm(self) -> str:
        """Returns the unrolled qasm for the given module"""
        return self._qasm_ast_to_str(self._unrolled_ast)

    @unrolled_qasm.setter
    def unrolled_qasm(self, value: str):
        """Setter for the unrolled qasm"""
        self._unrolled_qasm = value

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

    def has_measurements(self):
        """Check if the module has any measurement operations."""
        if self._has_measurements is None:
            self._has_measurements = False
            # try to check in the unrolled version as that will a better indicator of
            # the presence of measurements
            stmts_to_check = (
                self._unrolled_ast.statements
                if len(self._unrolled_ast.statements) > 1
                else self._statements
            )
            for stmt in stmts_to_check:
                if isinstance(stmt, qasm3_ast.QuantumMeasurementStatement):
                    self._has_measurements = True
                    break
        return self._has_measurements

    def remove_measurements(self, in_place: bool = True):
        """Remove the measurement operations

        Args:
            in_place (bool): Flag to indicate if the removal should be done in place.

        Returns:
            QasmModule: The module with the measurements removed if in_place is False
        """
        stmt_list = (
            self._statements
            if len(self._unrolled_ast.statements) == 1
            else self._unrolled_ast.statements
        )
        stmts_without_meas = [
            stmt
            for stmt in stmt_list
            if not isinstance(stmt, qasm3_ast.QuantumMeasurementStatement)
        ]
        curr_module = self

        if not in_place:
            curr_module = self.copy()

        for qubit in curr_module._qubit_depths.values():
            qubit.num_measurements = 0
        for clbit in curr_module._clbit_depths.values():
            clbit.num_measurements = 0

        curr_module._has_measurements = False
        curr_module._statements = stmts_without_meas
        curr_module._unrolled_ast.statements = stmts_without_meas
        curr_module._unrolled_qasm = self._qasm_ast_to_str(curr_module._unrolled_ast)

        return curr_module

    def remove_barriers(self, in_place: bool = True):
        """Remove the barrier operations

        Args:
            in_place (bool): Flag to indicate if the removal should be done in place.

        Returns:
            QasmModule: The module with the barriers removed if in_place is False
        """
        stmt_list = (
            self._statements
            if len(self._unrolled_ast.statements) == 1
            else self._unrolled_ast.statements
        )
        stmts_without_barriers = [
            stmt for stmt in stmt_list if not isinstance(stmt, qasm3_ast.QuantumBarrier)
        ]
        curr_module = self
        if not in_place:
            curr_module = self.copy()

        for qubit in curr_module._qubit_depths.values():
            qubit.num_barriers = 0

        curr_module._statements = stmts_without_barriers
        curr_module._unrolled_ast.statements = stmts_without_barriers
        curr_module._unrolled_qasm = self._qasm_ast_to_str(curr_module._unrolled_ast)

        return curr_module

    def depth(self):
        """Calculate the depth of the unrolled openqasm program.

        Args:
            None

        Returns:
            int: The depth of the current "unrolled" openqasm program
        """
        # 1. Since the program will be unrolled before its execution on a QC, it makes sense to
        # calculate the depth of the unrolled program.

        # We are performing operations in place, thus we need to calculate depth
        # at "each instance of the function call".
        # TODO: optimize by tracking whether the program changed since we
        # last calculated the depth

        qasm_module = self.copy()
        qasm_module._qubit_depths = {}
        qasm_module._clbit_depths = {}
        qasm_module.unroll()

        max_depth = 0
        max_qubit_depth, max_clbit_depth = 0, 0

        # calculate the depth using the qubit and clbit depths
        if len(qasm_module._qubit_depths) != 0:
            max_qubit_depth = max(qubit.depth for qubit in qasm_module._qubit_depths.values())
        if len(qasm_module._clbit_depths) != 0:
            max_clbit_depth = max(clbit.depth for clbit in qasm_module._clbit_depths.values())
        max_depth = max(max_qubit_depth, max_clbit_depth)
        return max_depth

    def validate(self):
        """Validate the module"""
        if self._validated_program is True:
            return
        try:
            self.num_qubits, self.num_clbits = 0, 0
            visitor = QasmVisitor(self, check_only=True)
            self.accept(visitor)
        except (ValidationError, NotImplementedError) as err:
            self.num_qubits, self.num_clbits = -1, -1
            raise err
        self._validated_program = True

    def unroll(self, **kwargs):
        """Unroll the module into basic qasm operations"""
        if not kwargs:
            kwargs = {}
        try:
            self.num_qubits, self.num_clbits = 0, 0
            visitor = QasmVisitor(module=self, **kwargs)
            self.accept(visitor)
        except (ValidationError, UnrollError) as err:
            # reset the unrolled ast and qasm
            self.num_qubits, self.num_clbits = -1, -1
            self._unrolled_qasm = ""
            self._unrolled_ast = Program(
                statements=[Include("stdgates.inc")], version=self.original_program.version
            )
            raise err

    def copy(self):
        """Return a deep copy of the module"""
        return deepcopy(self)

    @abstractmethod
    def _qasm_ast_to_str(self, qasm_ast):
        """Convert the qasm AST to a string"""

    @abstractmethod
    def accept(self, visitor):
        """Accept a visitor for the mßodule

        Args:
            visitor (QasmVisitor): The visitor to accept
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
        self._unrolled_ast = Program(statements=[Include("qelib1.inc")], version="2.0")
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

    def accept(self, visitor):
        """Accept a visitor for the module

        Args:
            visitor (QasmVisitor): The visitor to accept
        """
        self._filter_statements()
        unrolled_stmt_list = visitor.visit_basic_block(self._statements)
        self.unrolled_ast.statements = [Include("qelib1.inc")]  # pylint: disable=W0201
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
        self._unrolled_ast = Program(statements=[Include("stdgates.inc")], version="3.0")

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
        self.unrolled_ast.statements = [Include("stdgates.inc")]  # pylint: disable=W0201
        self.unrolled_ast.statements.extend(unrolled_stmt_list)
        # TODO: some finalizing method here probably
