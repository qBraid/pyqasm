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
Definition of the base Qasm module
"""

from abc import ABC, abstractmethod
from copy import deepcopy
from typing import Optional

import openqasm3.ast as qasm3_ast
from openqasm3.ast import Program

from pyqasm.analyzer import Qasm3Analyzer
from pyqasm.elements import ClbitDepthNode, QubitDepthNode
from pyqasm.exceptions import UnrollError, ValidationError
from pyqasm.maps import QUANTUM_STATEMENTS
from pyqasm.visitor import QasmVisitor


class QasmModule(ABC):  # pylint: disable=too-many-instance-attributes
    """Abstract class for a Qasm module

    Args:
        name (str): Name of the module.
        program (Program): The original openqasm3 program.
        statements (list[Statement]): list of openqasm3 Statements.
    """

    def __init__(self, name: str, program: Program):
        self._name = name
        self._original_program = program
        self._statements = program.statements
        self._num_qubits = -1
        self._num_clbits = -1
        self._qubit_depths: dict[tuple[str, int], QubitDepthNode] = {}
        self._clbit_depths: dict[tuple[str, int], ClbitDepthNode] = {}
        self._qubit_registers: dict[str, int] = {}
        self._classical_registers: dict[str, int] = {}
        self._has_measurements: Optional[bool] = None
        self._has_barriers: Optional[bool] = None
        self._validated_program = False
        self._unrolled_ast = Program(statements=[])

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

    def _add_qubit_register(self, reg_name: str, num_qubits: int):
        """Add qubits to the module

        Args:
            num_qubits (int): The number of qubits to add to the module

        Returns:
            None
        """
        self._qubit_registers[reg_name] = num_qubits
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

    def _add_classical_register(self, reg_name: str, num_clbits: int):
        """Add classical bits to the module

        Args:
            num_clbits (int): The number of classical bits to add to the module

        Returns:
            None
        """
        self._classical_registers[reg_name] = num_clbits
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

    def has_measurements(self) -> bool:
        """Check if the module has any measurement operations."""
        if self._has_measurements is None:
            self._has_measurements = False
            # try to check in the unrolled version as that will a better indicator of
            # the presence of measurements
            stmts_to_check = (
                self._unrolled_ast.statements
                if len(self._unrolled_ast.statements) > 0
                else self._statements
            )
            for stmt in stmts_to_check:
                if isinstance(stmt, qasm3_ast.QuantumMeasurementStatement):
                    self._has_measurements = True
                    break
        return self._has_measurements

    def remove_measurements(self, in_place: bool = True) -> Optional["QasmModule"]:
        """Remove the measurement operations

        Args:
            in_place (bool): Flag to indicate if the removal should be done in place.

        Returns:
            QasmModule: The module with the measurements removed if in_place is False
        """
        stmt_list = (
            self._statements
            if len(self._unrolled_ast.statements) == 0
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

        return curr_module

    def has_barriers(self) -> bool:
        """Check if the module has any barrier operations.

        Args:
            None

        Returns:
            bool: True if the module has barrier operations, False otherwise
        """
        if self._has_barriers is None:
            self._has_barriers = False
            # try to check in the unrolled version as that will a better indicator of
            # the presence of barriers
            stmts_to_check = (
                self._unrolled_ast.statements
                if len(self._unrolled_ast.statements) > 0
                else self._statements
            )
            for stmt in stmts_to_check:
                if isinstance(stmt, qasm3_ast.QuantumBarrier):
                    self._has_barriers = True
                    break
        return self._has_barriers

    def remove_barriers(self, in_place: bool = True) -> Optional["QasmModule"]:
        """Remove the barrier operations

        Args:
            in_place (bool): Flag to indicate if the removal should be done in place.

        Returns:
            QasmModule: The module with the barriers removed if in_place is False
        """
        stmt_list = (
            self._statements
            if len(self._unrolled_ast.statements) == 0
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

        curr_module._has_barriers = False
        curr_module._statements = stmts_without_barriers
        curr_module._unrolled_ast.statements = stmts_without_barriers

        return curr_module

    def remove_includes(self, in_place=True) -> Optional["QasmModule"]:
        """Remove the include statements from the module

        Args:
            in_place (bool): Flag to indicate if the removal should be done in place.

        Returns:
            QasmModule: The module with the includes removed if in_place is False, None otherwise
        """
        stmt_list = (
            self._statements
            if len(self._unrolled_ast.statements) == 0
            else self._unrolled_ast.statements
        )
        stmts_without_includes = [
            stmt for stmt in stmt_list if not isinstance(stmt, qasm3_ast.Include)
        ]
        curr_module = self
        if not in_place:
            curr_module = self.copy()

        curr_module._statements = stmts_without_includes
        curr_module._unrolled_ast.statements = stmts_without_includes

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

    def _remap_qubits(self, reg_name: str, size: int, idle_indices: list[int]):
        """Remap the qubits in a register after removing idle qubits and update the operations
        using this register accordingly"""

        used_indices = [idx for idx in range(size) if idx not in idle_indices]
        new_size = size - len(idle_indices)
        idx_map = {used_indices[i]: i for i in range(new_size)}  # old_idx : new_idx

        # Example -
        # reg_name = "q", original_size = 5, idle_indices = [1, 3]
        # used_indices = [0, 2, 4], new_size = 3
        # idx_map = {0: 0, 2: 1, 4: 2}

        # update the qubit register size
        self._qubit_registers[reg_name] = new_size

        # update the qubit declaration in the unrolled ast
        for stmt in self._unrolled_ast.statements:
            if isinstance(stmt, qasm3_ast.QubitDeclaration):
                if stmt.qubit.name == reg_name:
                    stmt.size.value = new_size  # type: ignore[union-attr]
                    break

        # update the qubit depths
        for idx in used_indices:
            qubit = self._qubit_depths[(reg_name, idx)]
            qubit.reg_index = idx_map[idx]
            self._qubit_depths[(reg_name, idx_map[idx])] = deepcopy(qubit)
            del self._qubit_depths[(reg_name, idx)]

        # update the operations that use the qubits
        for operation in self._unrolled_ast.statements:
            if isinstance(operation, QUANTUM_STATEMENTS):
                bit_list = Qasm3Analyzer.get_op_bit_list(operation)
                for bit in bit_list:
                    assert isinstance(bit, qasm3_ast.IndexedIdentifier)
                    if bit.name.name == reg_name:
                        old_idx = bit.indices[0][0].value  # type: ignore[union-attr,index]
                        bit.indices[0][0].value = idx_map[old_idx]  # type: ignore[union-attr,index]

    def _get_idle_qubit_indices(self) -> dict[str, list[int]]:
        """Get the indices of the idle qubits in the module

        Returns:
            dict[str, list[int]]: A dictionary mapping the register name to the list of idle qubit
                                  indices in that register
        """
        idle_qubits = [qubit for qubit in self._qubit_depths.values() if qubit.is_idle()]

        # re-map the idle qubits as {reg_name: [indices]}
        qubit_indices: dict[str, list[int]] = {}
        for qubit in idle_qubits:
            if qubit.reg_name not in qubit_indices:
                qubit_indices[qubit.reg_name] = []
            qubit_indices[qubit.reg_name].append(qubit.reg_index)

        return qubit_indices

    def populate_idle_qubits(self, in_place: bool = True):
        """Populate the idle qubits in the module with identity gates

        Note: unrolling is not performed while calling this function

        Args:
            in_place (bool): Flag to indicate if the population should be done in place.

        Returns:
            QasmModule: The module with the idle qubits populated. If in_place is False, a new
                        module with the populated idle qubits is returned.

        """
        qasm_module = self if in_place else self.copy()
        qasm_module.validate()

        idle_qubit_indices = qasm_module._get_idle_qubit_indices()

        id_gate_list = []
        for reg_name, idle_indices in idle_qubit_indices.items():
            for idx in idle_indices:
                # increment the depth of the idle qubits by 1
                qasm_module._qubit_depths[(reg_name, idx)].depth += 1

                # add an identity gate to the qubits that are idle
                id_gate = qasm3_ast.QuantumGate(
                    modifiers=[],
                    name=qasm3_ast.Identifier(name="id"),
                    arguments=[],
                    qubits=[
                        qasm3_ast.IndexedIdentifier(
                            name=qasm3_ast.Identifier(name=reg_name),
                            indices=[[qasm3_ast.IntegerLiteral(value=idx)]],
                        )
                    ],
                )
                id_gate_list.append(id_gate)

        qasm_module.original_program.statements.extend(id_gate_list)
        qasm_module._statements = qasm_module.original_program.statements

        return qasm_module

    def remove_idle_qubits(self, in_place: bool = True):
        """Remove idle qubits from the module. Either collapse the size of a partially used
        quantum register OR remove the unused quantum register entirely.

        Will unroll the module if not already done.

        Args:
            in_place (bool): Flag to indicate if the removal should be done in place.

        Returns:
            QasmModule: The module the idle qubits removed. If in_place is False, a new module
                        with the reversed qubit order is returned.
        """

        qasm_module = self if in_place else self.copy()
        qasm_module.unroll()

        idle_qubit_indices = qasm_module._get_idle_qubit_indices()

        for reg_name, idle_indices in idle_qubit_indices.items():
            # we have removed the idle qubits, so we can remove them from depth map
            for idle_idx in idle_indices:
                del qasm_module._qubit_depths[(reg_name, idle_idx)]

            size = self._qubit_registers[reg_name]

            if len(idle_indices) == size:  # all qubits are idle

                # remove the declaration from the unrolled ast
                for stmt in qasm_module._unrolled_ast.statements:
                    if isinstance(stmt, qasm3_ast.QubitDeclaration):
                        if stmt.qubit.name == reg_name:
                            qasm_module._unrolled_ast.statements.remove(stmt)
                            qasm_module._statements.remove(stmt)
                            break

                del qasm_module._qubit_registers[reg_name]
                # we do not need to change any other operation as there will be no qubit usage
                # if the complete register was unused

            elif len(idle_indices) != 0:  # partially used register
                qasm_module._remap_qubits(reg_name, size, idle_indices)

            # update the number of qubits
            self._num_qubits -= len(idle_indices)

        # the original ast will need to be updated to the unrolled ast as if we call the
        # unroll operation again, it will incorrectly choose the original ast WITH THE IDLE QUBITS
        qasm_module._statements = qasm_module._unrolled_ast.statements

        return qasm_module

    def reverse_qubit_order(self, in_place=True):
        """Reverse the order of qubits in the module.

        Will unroll the module if not already done.

        Args:
            in_place (bool): Flag to indicate if the reversal should be done in place.

        Returns:
            QasmModule: The module the qubit order reversed. If in_place is False, a new module
                        with the reversed qubit order is returned.
        """

        qasm_module = self if in_place else self.copy()
        qasm_module.unroll()

        new_qubit_mappings = {}
        for register, size in self._qubit_registers.items():
            new_qubit_mappings[register] = {0: 0}
            if size > 1:
                new_qubit_mappings[register] = {old_id: size - old_id - 1 for old_id in range(size)}

        # Example -
        # q[0], q[1], q[2], q[3] -> q[3], q[2], q[1], q[0]
        # new_qubit_mappings = {"q": {0: 3, 1: 2, 2: 1, 3: 0}}

        # 1. Qubit depths will be recalculated whenever we calculate the depth so we do not update
        #    the depth maps here

        # 2. replace each qubit index in the Quantum Operations with the new index
        for operation in qasm_module._unrolled_ast.statements:
            if isinstance(operation, QUANTUM_STATEMENTS):
                bit_list = Qasm3Analyzer.get_op_bit_list(operation)
                for bit in bit_list:
                    curr_reg_name = bit.name.name
                    curr_reg_idx = bit.indices[0][0].value
                    new_reg_idx = new_qubit_mappings[curr_reg_name][curr_reg_idx]

                    # make the idx -ve so that this is not touched
                    # while updating the same index later

                    # idx -> -1 * idx - 1 as we also have to look at index 0
                    # which will remain 0 if we just multiply by -1
                    bit.indices[0][0].value = -1 * new_reg_idx - 1

        # remove the -ve marker
        for operation in qasm_module._unrolled_ast.statements:
            if isinstance(operation, QUANTUM_STATEMENTS):
                bit_list = Qasm3Analyzer.get_op_bit_list(operation)
                for bit in bit_list:
                    if bit.indices[0][0].value < 0:
                        bit.indices[0][0].value += 1
                        bit.indices[0][0].value *= -1

        # 3. update the original AST with the unrolled AST
        qasm_module._statements = qasm_module._unrolled_ast.statements

        # 4. return the module
        return qasm_module

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
            self._unrolled_ast = Program(statements=[], version=self.original_program.version)
            raise err

    def __str__(self) -> str:
        """Return the string representation of the QASM program

        Returns:
            str: The string representation of the module
        """

        if len(self._unrolled_ast.statements) > 1:
            return self._qasm_ast_to_str(self.unrolled_ast)
        return self._qasm_ast_to_str(self.original_program)

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
