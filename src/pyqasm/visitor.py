# Copyright (C) 2024 qBraid
#
# This file is part of pyqasm
#
# Pyqasm is free software released under the GNU General Public License v3
# or later. You can redistribute and/or modify it under the terms of the GPL v3.
# See the LICENSE file in the project root or <https://www.gnu.org/licenses/gpl-3.0.html>.
#
# THERE IS NO WARRANTY for pyqasm, as per Section 15 of the GPL v3.

# pylint: disable=too-many-lines

"""
Module defining Qasm Visitor.

"""
import copy
import logging
from collections import deque
from functools import partial
from typing import Any, Callable, Optional, Union

import numpy as np
import openqasm3.ast as qasm3_ast

from pyqasm.analyzer import Qasm3Analyzer
from pyqasm.elements import ClbitDepthNode, Context, InversionOp, QubitDepthNode, Variable
from pyqasm.exceptions import ValidationError, raise_qasm3_error
from pyqasm.expressions import Qasm3ExprEvaluator
from pyqasm.maps import (
    ARRAY_TYPE_MAP,
    CONSTANTS_MAP,
    MAX_ARRAY_DIMENSIONS,
    SWITCH_BLACKLIST_STMTS,
    map_qasm_inv_op_to_callable,
    map_qasm_op_to_callable,
)
from pyqasm.subroutines import Qasm3SubroutineProcessor
from pyqasm.transformer import Qasm3Transformer
from pyqasm.validator import Qasm3Validator

logger = logging.getLogger(__name__)


# pylint: disable-next=too-many-instance-attributes
class QasmVisitor:
    """A visitor for basic OpenQASM program elements.

    This class is designed to traverse and interact with elements in an OpenQASM program.

    Args:
        initialize_runtime (bool): If True, quantum runtime will be initialized. Defaults to True.
        record_output (bool): If True, output of the circuit will be recorded. Defaults to True.
        external_gates (list[str]): List of gates that should not be unrolled.
    """

    def __init__(self, module, check_only: bool = False, external_gates: list[str] | None = None):
        self._module = module
        self._scope: deque = deque([{}])
        self._context: deque = deque([Context.GLOBAL])
        self._included_files: set[str] = set()
        self._qubit_labels: dict[str, int] = {}
        self._clbit_labels: dict[str, int] = {}
        self._alias_qubit_labels: dict[tuple[str, int], tuple[str, int]] = {}
        self._global_qreg_size_map: dict[str, int] = {}
        self._global_alias_size_map: dict[str, int] = {}
        self._function_qreg_size_map: deque = deque([])  # for nested functions
        self._function_qreg_transform_map: deque = deque([])  # for nested functions
        self._global_creg_size_map: dict[str, int] = {}
        self._custom_gates: dict[str, qasm3_ast.QuantumGateDefinition] = {}
        self._external_gates: list[str] = [] if external_gates is None else external_gates
        self._subroutine_defns: dict[str, qasm3_ast.SubroutineDefinition] = {}
        self._check_only: bool = check_only
        self._curr_scope: int = 0
        self._label_scope_level: dict[int, set] = {self._curr_scope: set()}

        self._init_utilities()

    def _init_utilities(self):
        """Initialize the utilities for the visitor."""
        for class_obj in [Qasm3Transformer, Qasm3ExprEvaluator, Qasm3SubroutineProcessor]:
            class_obj.set_visitor_obj(self)

    def _push_scope(self, scope: dict) -> None:
        if not isinstance(scope, dict):
            raise TypeError("Scope must be a dictionary")
        self._scope.append(scope)

    def _push_context(self, context: Context) -> None:
        if not isinstance(context, Context):
            raise TypeError("Context must be an instance of Context")
        self._context.append(context)

    def _pop_scope(self) -> None:
        if len(self._scope) == 0:
            raise IndexError("Scope list is empty, can not pop")
        self._scope.pop()

    def _restore_context(self) -> None:
        if len(self._context) == 0:
            raise IndexError("Context list is empty, can not pop")
        self._context.pop()

    def _get_parent_scope(self) -> dict:
        if len(self._scope) < 2:
            raise IndexError("Parent scope not available")
        return self._scope[-2]

    def _get_curr_scope(self) -> dict:
        if len(self._scope) == 0:
            raise IndexError("No scopes available to get")
        return self._scope[-1]

    def _get_curr_context(self) -> Context:
        if len(self._context) == 0:
            raise IndexError("No context available to get")
        return self._context[-1]

    def _get_global_scope(self) -> dict:
        if len(self._scope) == 0:
            raise IndexError("No scopes available to get")
        return self._scope[0]

    def _check_in_scope(self, var_name: str) -> bool:
        """
        Checks if a variable is in scope.

        Args:
            var_name (str): The name of the variable to check.

        Returns:
            bool: True if the variable is in scope, False otherwise.

        NOTE:

        - According to our definition of scope, we have a NEW DICT
          for each block scope also
        - Since all visible variables of the immediate parent are visible
          inside block scope, we have to check till we reach the boundary
          contexts
        - The "boundary" for a scope is either a FUNCTION / GATE context
          OR the GLOBAL context
        - Why then do we need a new scope for a block?
        - Well, if the block redeclares a variable in its scope, then the
          variable in the parent scope is shadowed. We need to remember the
          original value of the shadowed variable when we exit the block scope

        """
        global_scope = self._get_global_scope()
        curr_scope = self._get_curr_scope()
        if self._in_global_scope():
            return var_name in global_scope
        if self._in_function_scope() or self._in_gate_scope():
            if var_name in curr_scope:
                return True
            if var_name in global_scope:
                return global_scope[var_name].is_constant
        if self._in_block_scope():
            for scope, context in zip(reversed(self._scope), reversed(self._context)):
                if context != Context.BLOCK:
                    return var_name in scope
                if var_name in scope:
                    return True
        return False

    def _get_from_visible_scope(self, var_name: str) -> Union[Variable, None]:
        """
        Retrieves a variable from the visible scope.

        Args:
            var_name (str): The name of the variable to retrieve.

        Returns:
            Union[Variable, None]: The variable if found, None otherwise.
        """
        global_scope = self._get_global_scope()
        curr_scope = self._get_curr_scope()

        if self._in_global_scope():
            return global_scope.get(var_name, None)
        if self._in_function_scope() or self._in_gate_scope():
            if var_name in curr_scope:
                return curr_scope[var_name]
            if var_name in global_scope and global_scope[var_name].is_constant:
                return global_scope[var_name]
        if self._in_block_scope():
            for scope, context in zip(reversed(self._scope), reversed(self._context)):
                if context != Context.BLOCK:
                    return scope.get(var_name, None)
                if var_name in scope:
                    return scope[var_name]
                    # keep on checking otherwise
        return None

    def _add_var_in_scope(self, variable: Variable) -> None:
        """Add a variable to the current scope.

        Args:
            variable (Variable): The variable to add.

        Raises:
            ValueError: If the variable already exists in the current scope.
        """
        curr_scope = self._get_curr_scope()
        if variable.name in curr_scope:
            raise ValueError(f"Variable '{variable.name}' already exists in current scope")
        curr_scope[variable.name] = variable

    def _update_var_in_scope(self, variable: Variable) -> None:
        """
        Updates the variable in the current scope.

        Args:
            variable (Variable): The variable to be updated.

        Raises:
            ValueError: If no scope is available to update.
        """
        if len(self._scope) == 0:
            raise ValueError("No scope available to update")

        global_scope = self._get_global_scope()
        curr_scope = self._get_curr_scope()

        if self._in_global_scope():
            global_scope[variable.name] = variable
        if self._in_function_scope() or self._in_gate_scope():
            curr_scope[variable.name] = variable
        if self._in_block_scope():
            for scope, context in zip(reversed(self._scope), reversed(self._context)):
                if context != Context.BLOCK:
                    scope[variable.name] = variable
                    break
                if variable.name in scope:
                    scope[variable.name] = variable
                    break
                continue

    def _in_global_scope(self) -> bool:
        return len(self._scope) == 1 and self._get_curr_context() == Context.GLOBAL

    def _in_function_scope(self) -> bool:
        return len(self._scope) > 1 and self._get_curr_context() == Context.FUNCTION

    def _in_gate_scope(self) -> bool:
        return len(self._scope) > 1 and self._get_curr_context() == Context.GATE

    def _in_block_scope(self) -> bool:  # block scope is for if/else/for/while constructs
        return len(self._scope) > 1 and self._get_curr_context() == Context.BLOCK

    def _visit_quantum_register(
        self, register: qasm3_ast.QubitDeclaration
    ) -> list[qasm3_ast.QubitDeclaration]:
        """Visit a Qubit declaration statement.

        Args:
            register (QubitDeclaration): The register name and size.

        Returns:
            None
        """
        logger.debug("Visiting register '%s'", str(register))

        current_size = len(self._qubit_labels)
        register_size = (
            1
            if register.size is None
            else Qasm3ExprEvaluator.evaluate_expression(register.size, const_expr=True)[
                0
            ]  # type: ignore[attr-defined]
        )
        register.size = qasm3_ast.IntegerLiteral(register_size)
        register_name = register.qubit.name  # type: ignore[union-attr]

        size_map = self._global_qreg_size_map
        label_map = self._qubit_labels

        if self._check_in_scope(register_name):
            raise_qasm3_error(
                f"Re-declaration of quantum register with name '{register_name}'",
                span=register.span,
            )

        if register_name in CONSTANTS_MAP:
            raise_qasm3_error(
                f"Can not declare quantum register with keyword name '{register_name}'",
                span=register.span,
            )

        self._add_var_in_scope(
            Variable(
                register_name, qasm3_ast.QubitDeclaration, register_size, None, None, False, True
            )
        )
        size_map[f"{register_name}"] = register_size

        for i in range(register_size):
            # required if indices are not used while applying a gate or measurement
            label_map[f"{register_name}_{i}"] = current_size + i
            self._module._qubit_depths[(register_name, i)] = QubitDepthNode(register_name, i)

        self._label_scope_level[self._curr_scope].add(register_name)

        self._module._add_qubit_register(register_name, register_size)

        logger.debug("Added labels for register '%s'", str(register))

        if self._check_only:
            return []
        return [register]

    def _check_if_name_in_scope(self, name: str, operation: Any) -> None:
        """Check if a name is in scope to avoid duplicate declarations.
        Args:
            name (str): The name to check.
            operation (Any): The operation to check the name in scope for.

        Returns:
            bool: Whether the name is in scope.
        """
        for scope_level in range(0, self._curr_scope + 1):
            if name in self._label_scope_level[scope_level]:
                return
        raise_qasm3_error(
            f"Variable {name} not in scope for operation {operation}", span=operation.span
        )

    # pylint: disable-next=too-many-locals,too-many-branches
    def _get_op_bits(
        self, operation: Any, reg_size_map: dict, qubits: bool = True
    ) -> list[qasm3_ast.IndexedIdentifier]:
        """Get the quantum / classical bits for the operation.

        Args:
            operation (Any): The operation to get qubits for.
            reg_size_map (dict): The size map of the registers in scope.
            qubits (bool): Whether the bits are quantum bits or classical bits. Defaults to True.
        Returns:
            list[qasm3_ast.IndexedIdentifier] : The bits for the operation.
        """
        openqasm_bits = []
        visited_bits = set()
        bit_list = []
        original_size_map = reg_size_map

        if isinstance(operation, qasm3_ast.QuantumMeasurementStatement):
            assert operation.target is not None
            bit_list = [operation.measure.qubit] if qubits else [operation.target]
        elif isinstance(operation, qasm3_ast.QuantumPhase) and operation.qubits is None:
            for reg_name, reg_size in reg_size_map.items():
                bit_list.append(
                    qasm3_ast.IndexedIdentifier(
                        qasm3_ast.Identifier(reg_name), [[qasm3_ast.IntegerLiteral(i)]]
                    )
                    for i in range(reg_size)
                )
            return bit_list
        else:
            bit_list = (
                operation.qubits if isinstance(operation.qubits, list) else [operation.qubits]
            )

        for bit in bit_list:
            # required for each bit
            replace_alias = False
            reg_size_map = original_size_map
            if isinstance(bit, qasm3_ast.IndexedIdentifier):
                reg_name = bit.name.name
            else:
                reg_name = bit.name

            if reg_name not in reg_size_map:
                # check for aliasing
                if qubits and reg_name in self._global_alias_size_map:
                    replace_alias = True
                    reg_size_map = self._global_alias_size_map
                else:
                    raise_qasm3_error(
                        f"Missing register declaration for {reg_name} in operation {operation}",
                        span=operation.span,
                    )
            self._check_if_name_in_scope(reg_name, operation)

            if isinstance(bit, qasm3_ast.IndexedIdentifier):
                if isinstance(bit.indices[0], qasm3_ast.DiscreteSet):
                    bit_ids = Qasm3Transformer.extract_values_from_discrete_set(bit.indices[0])
                elif isinstance(bit.indices[0][0], qasm3_ast.RangeDefinition):
                    bit_ids = Qasm3Transformer.get_qubits_from_range_definition(
                        bit.indices[0][0], reg_size_map[reg_name], is_qubit_reg=qubits
                    )
                else:
                    bit_id = Qasm3ExprEvaluator.evaluate_expression(bit.indices[0][0])[0]
                    Qasm3Validator.validate_register_index(
                        bit_id, reg_size_map[reg_name], qubit=qubits
                    )
                    bit_ids = [bit_id]
            else:
                bit_ids = list(range(reg_size_map[reg_name]))

            if replace_alias:
                original_reg_name, _ = self._alias_qubit_labels[(reg_name, bit_ids[0])]
                bit_ids = [
                    self._alias_qubit_labels[(reg_name, bit_id)][1]  # gives (original_reg, index)
                    for bit_id in bit_ids
                ]
                reg_name = original_reg_name

            new_bits = [
                qasm3_ast.IndexedIdentifier(
                    qasm3_ast.Identifier(reg_name), [[qasm3_ast.IntegerLiteral(bit_id)]]
                )
                for bit_id in bit_ids
            ]
            # check for duplicate bits
            for bit_id in new_bits:
                bit_name, bit_value = bit_id.name.name, bit_id.indices[0][0].value
                if tuple((bit_name, bit_value)) in visited_bits:
                    raise_qasm3_error(
                        f"Duplicate {'qubit' if qubits else 'clbit'} "
                        f"{bit_name}[{bit_value}] argument",
                        span=operation.span,
                    )
                visited_bits.add((bit_name, bit_value))

            openqasm_bits.extend(new_bits)

        return openqasm_bits

    def _visit_measurement(  # pylint: disable=too-many-locals
        self, statement: qasm3_ast.QuantumMeasurementStatement
    ) -> list[qasm3_ast.QuantumMeasurementStatement]:
        """Visit a measurement statement element.

        Args:
            statement (qasm3_ast.QuantumMeasurementStatement): The measurement statement to visit.

        Returns:
            None
        """
        logger.debug("Visiting measurement statement '%s'", str(statement))

        source = statement.measure.qubit
        target = statement.target
        assert source and target

        # # TODO: handle in-function measurements
        source_name: str = (
            source.name if isinstance(source, qasm3_ast.Identifier) else source.name.name
        )
        if source_name not in self._global_qreg_size_map:
            raise_qasm3_error(
                f"Missing register declaration for {source_name} in measurement "
                f"operation {statement}",
                span=statement.span,
            )

        target_name: str = (
            target.name if isinstance(target, qasm3_ast.Identifier) else target.name.name
        )
        if target_name not in self._global_creg_size_map:
            raise_qasm3_error(
                f"Missing register declaration for {target_name} in measurement "
                f"operation {statement}",
                span=statement.span,
            )

        source_ids = self._get_op_bits(
            statement, reg_size_map=self._global_qreg_size_map, qubits=True
        )
        target_ids = self._get_op_bits(
            statement, reg_size_map=self._global_creg_size_map, qubits=False
        )

        if len(source_ids) != len(target_ids):
            raise_qasm3_error(
                f"Register sizes of {source_name} and {target_name} do not match "
                "for measurement operation",
                span=statement.span,
            )
        unrolled_measurements = []
        for src_id, tgt_id in zip(source_ids, target_ids):
            unrolled_measure = qasm3_ast.QuantumMeasurementStatement(
                measure=qasm3_ast.QuantumMeasurement(qubit=src_id), target=tgt_id
            )
            src_name, src_id = src_id.name.name, src_id.indices[0][0].value  # type: ignore
            tgt_name, tgt_id = tgt_id.name.name, tgt_id.indices[0][0].value  # type: ignore

            qubit_node, clbit_node = (
                self._module._qubit_depths[(src_name, src_id)],
                self._module._clbit_depths[(tgt_name, tgt_id)],
            )
            qubit_node.depth += 1
            qubit_node.num_measurements += 1

            clbit_node.depth += 1
            clbit_node.num_measurements += 1

            qubit_node.depth = max(qubit_node.depth, clbit_node.depth)
            clbit_node.depth = max(qubit_node.depth, clbit_node.depth)

            unrolled_measurements.append(unrolled_measure)

        if self._check_only:
            return []

        return unrolled_measurements

    def _visit_reset(self, statement: qasm3_ast.QuantumReset) -> list[qasm3_ast.QuantumReset]:
        """Visit a reset statement element.

        Args:
            statement (qasm3_ast.QuantumReset): The reset statement to visit.

        Returns:
            None
        """
        logger.debug("Visiting reset statement '%s'", str(statement))
        if len(self._function_qreg_size_map) > 0:  # atleast in SOME function scope
            # transform qubits to use the global qreg identifiers
            statement.qubits = (
                Qasm3Transformer.transform_function_qubits(  # type: ignore[assignment]
                    statement,
                    self._function_qreg_size_map[-1],
                    self._function_qreg_transform_map[-1],
                )
            )
        qubit_ids = self._get_op_bits(statement, self._global_qreg_size_map, True)

        unrolled_resets = []
        for qid in qubit_ids:
            unrolled_reset = qasm3_ast.QuantumReset(qubits=qid)

            qubit_name, qubit_id = qid.name.name, qid.indices[0][0].value  # type: ignore
            qubit_node = self._module._qubit_depths[(qubit_name, qubit_id)]

            qubit_node.depth += 1
            qubit_node.num_resets += 1

            unrolled_resets.append(unrolled_reset)

        if self._check_only:
            return []

        return unrolled_resets

    def _visit_barrier(self, barrier: qasm3_ast.QuantumBarrier) -> list[qasm3_ast.QuantumBarrier]:
        """Visit a barrier statement element.

        Args:
            statement (qasm3_ast.QuantumBarrier): The barrier statement to visit.

        Returns:
            None
        """
        # if barrier is applied to ALL qubits at once, we are fine
        if len(self._function_qreg_size_map) > 0:  # atleast in SOME function scope
            # transform qubits to use the global qreg identifiers

            # since we are changing the qubits to IndexedIdentifiers, we need to supress the
            # error for the type checker
            barrier.qubits = (
                Qasm3Transformer.transform_function_qubits(  # type: ignore [assignment]
                    barrier,
                    self._function_qreg_size_map[-1],
                    self._function_qreg_transform_map[-1],
                )
            )
        barrier_qubits = self._get_op_bits(barrier, self._global_qreg_size_map)
        unrolled_barriers = []
        max_involved_depth = 0
        for qubit in barrier_qubits:
            unrolled_barrier = qasm3_ast.QuantumBarrier(qubits=[qubit])  # type: ignore[list-item]
            qubit_name, qubit_id = qubit.name.name, qubit.indices[0][0].value  # type: ignore
            qubit_node = self._module._qubit_depths[(qubit_name, qubit_id)]

            qubit_node.depth += 1
            qubit_node.num_barriers += 1

            max_involved_depth = max(max_involved_depth, qubit_node.depth)
            unrolled_barriers.append(unrolled_barrier)

        for qubit in barrier_qubits:
            qubit_name, qubit_id = qubit.name.name, qubit.indices[0][0].value  # type: ignore
            qubit_node = self._module._qubit_depths[(qubit_name, qubit_id)]
            qubit_node.depth = max_involved_depth

        if self._check_only:
            return []

        return unrolled_barriers

    def _get_op_parameters(self, operation: qasm3_ast.QuantumGate) -> list[float]:
        """Get the parameters for the operation.

        Args:
            operation (qasm3_ast.QuantumGate): The operation to get parameters for.

        Returns:
            list[float]: The parameters for the operation.
        """
        param_list = []
        for param in operation.arguments:
            param_value = Qasm3ExprEvaluator.evaluate_expression(param)[0]
            param_list.append(param_value)

        return param_list

    def _visit_gate_definition(self, definition: qasm3_ast.QuantumGateDefinition) -> list[None]:
        """Visit a gate definition element.

        Args:
            definition (qasm3_ast.QuantumGateDefinition): The gate definition to visit.

        Returns:
            None
        """
        gate_name = definition.name.name
        if gate_name in self._custom_gates:
            raise_qasm3_error(f"Duplicate gate definition for {gate_name}", span=definition.span)
        self._custom_gates[gate_name] = definition

        return []

    def _unroll_multiple_target_qubits(
        self, operation: qasm3_ast.QuantumGate, gate_qubit_count: int
    ) -> list[list[qasm3_ast.IndexedIdentifier]]:
        """Unroll the complete list of all qubits that the given operation is applied to.
           E.g. this maps 'cx q[0], q[1], q[2], q[3]' to [[q[0], q[1]], [q[2], q[3]]]

        Args:
            operation (qasm3_ast.QuantumGate): The gate to be applied.
            gate_qubit_count (list[int]): The number of qubits that a single gate acts on.

        Returns:
            The list of all targets that the unrolled gate should act on.
        """
        op_qubits = self._get_op_bits(operation, self._global_qreg_size_map)
        if len(op_qubits) % gate_qubit_count != 0:
            raise_qasm3_error(
                f"Invalid number of qubits {len(op_qubits)} for operation {operation.name.name}",
                span=operation.span,
            )
        qubit_subsets = []
        for i in range(0, len(op_qubits), gate_qubit_count):
            # we apply the gate on the qubit subset linearly
            qubit_subsets.append(op_qubits[i : i + gate_qubit_count])
        return qubit_subsets

    def _broadcast_gate_operation(
        self, gate_function: Callable, all_targets: list[list[qasm3_ast.IndexedIdentifier]]
    ) -> list[qasm3_ast.QuantumGate]:
        """Broadcasts the application of a gate onto multiple sets of target qubits.

        Args:
            gate_function (callable): The gate that should be applied to multiple target qubits.
            (All arguments of the callable should be qubits, i.e. all non-qubit arguments of the
            gate should already be evaluated, e.g. using functools.partial).
            all_targets (list[list[qasm3_ast.IndexedIdentifier]]):
                The list of target qubits.
                The length of this list indicates the number of time the gate is invoked.
        Returns:
            List of all executed gates.
        """
        result = []
        for targets in all_targets:
            result.extend(gate_function(*targets))
        return result

    def _update_qubit_depth_for_gate(self, all_targets: list[list[qasm3_ast.IndexedIdentifier]]):
        """Updates the depth of the circuit after applying a broadcasted gate.

        Args:
            all_targes: The list of qubits on which a gate was just added.

        Returns:
            None
        """
        for qubit_subset in all_targets:
            max_involved_depth = 0
            for qubit in qubit_subset:
                qubit_name, qubit_id = qubit.name.name, qubit.indices[0][0].value  # type: ignore
                qubit_node = self._module._qubit_depths[(qubit_name, qubit_id)]
                qubit_node.num_gates += 1
                max_involved_depth = max(max_involved_depth, qubit_node.depth + 1)

            for qubit in qubit_subset:
                qubit_name, qubit_id = qubit.name.name, qubit.indices[0][0].value  # type: ignore
                qubit_node = self._module._qubit_depths[(qubit_name, qubit_id)]
                qubit_node.depth = max_involved_depth

    def _visit_basic_gate_operation(  # pylint: disable=too-many-locals
        self, operation: qasm3_ast.QuantumGate, inverse: bool = False
    ) -> list[qasm3_ast.QuantumGate]:
        """Visit a gate operation element.

        Args:
            operation (qasm3_ast.QuantumGate): The gate operation to visit.
            inverse (bool): Whether the operation is an inverse operation. Defaults to False.

                          - if inverse is True, we apply check for different cases in the
                            map_qasm_inv_op_to_callable method.

                          - Only rotation and S / T gates are affected by this inversion. For S/T
                            gates we map them to Sdg / Tdg and vice versa.

                          - For rotation gates, we map to the same gates but invert the rotation
                            angles.

        Returns:
            None

        Raises:
            ValidationError: If the number of qubits is invalid.

        """
        logger.debug("Visiting basic gate operation '%s'", str(operation))
        inverse_action = None
        if not inverse:
            qasm_func, op_qubit_count = map_qasm_op_to_callable(operation.name.name)
        else:
            # in basic gates, inverse action only affects the rotation gates
            qasm_func, op_qubit_count, inverse_action = map_qasm_inv_op_to_callable(
                operation.name.name
            )

        op_parameters = []

        if len(operation.arguments) > 0:  # parametric gate
            op_parameters = self._get_op_parameters(operation)
            if inverse_action == InversionOp.INVERT_ROTATION:
                op_parameters = [-1 * param for param in op_parameters]

        result = []

        unrolled_targets = self._unroll_multiple_target_qubits(operation, op_qubit_count)
        unrolled_gate_function = partial(qasm_func, *op_parameters)
        result.extend(self._broadcast_gate_operation(unrolled_gate_function, unrolled_targets))

        self._update_qubit_depth_for_gate(unrolled_targets)

        if self._check_only:
            return []

        return result

    def _visit_custom_gate_operation(
        self, operation: qasm3_ast.QuantumGate, inverse: bool = False
    ) -> list[Union[qasm3_ast.QuantumGate, qasm3_ast.QuantumPhase]]:
        """Visit a custom gate operation element recursively.

        Args:
            operation (qasm3_ast.QuantumGate): The gate operation to visit.
            inverse (bool): Whether the operation is an inverse operation. Defaults to False.

                            If True, the gate operation is applied in reverse order and the
                            inverse modifier is appended to each gate call.
                            See https://openqasm.com/language/gates.html#inverse-modifier
                            for more clarity.

        Returns:
            None
        """
        logger.debug("Visiting custom gate operation '%s'", str(operation))
        gate_name: str = operation.name.name
        gate_definition: qasm3_ast.QuantumGateDefinition = self._custom_gates[gate_name]
        op_qubits: list[qasm3_ast.IndexedIdentifier] = (
            self._get_op_bits(  # type: ignore [assignment]
                operation,
                self._global_qreg_size_map,
            )
        )

        Qasm3Validator.validate_gate_call(operation, gate_definition, len(op_qubits))
        # we need this because the gates applied inside a gate definition use the
        # VARIABLE names and not the qubits

        # so we need to update the arguments of these gate applications with the actual
        # qubit identifiers and then RECURSIVELY call the visit_generic_gate_operation
        qubit_map = {
            formal_arg.name: actual_arg
            for formal_arg, actual_arg in zip(gate_definition.qubits, op_qubits)
        }
        param_map = {
            formal_arg.name: Qasm3ExprEvaluator.evaluate_expression(actual_arg)[0]
            for formal_arg, actual_arg in zip(gate_definition.arguments, operation.arguments)
        }

        gate_definition_ops = copy.deepcopy(gate_definition.body)
        if inverse:
            gate_definition_ops.reverse()

        self._push_context(Context.GATE)
        result = []
        for gate_op in gate_definition_ops:
            if isinstance(gate_op, (qasm3_ast.QuantumGate, qasm3_ast.QuantumPhase)):
                gate_op_copy = copy.deepcopy(gate_op)
                # necessary to avoid modifying the original gate definition
                # in case the gate is reapplied
                if isinstance(gate_op, qasm3_ast.QuantumGate) and gate_op.name.name == gate_name:
                    raise_qasm3_error(
                        f"Recursive definitions not allowed for gate {gate_name}", span=gate_op.span
                    )
                Qasm3Transformer.transform_gate_params(gate_op_copy, param_map)
                Qasm3Transformer.transform_gate_qubits(gate_op_copy, qubit_map)
                # need to trickle the inverse down to the child gates
                if inverse:
                    # span doesn't matter as we don't analyze it
                    gate_op_copy.modifiers.append(
                        qasm3_ast.QuantumGateModifier(qasm3_ast.GateModifierName.inv, None)
                    )
                result.extend(self._visit_generic_gate_operation(gate_op_copy))
            else:
                # TODO: add control flow support
                raise_qasm3_error(
                    f"Unsupported gate definition statement {gate_op}", span=gate_op.span
                )

        self._restore_context()

        if self._check_only:
            return []

        return result

    def _visit_external_gate_operation(
        self, operation: qasm3_ast.QuantumGate, inverse: bool = False
    ) -> list[qasm3_ast.QuantumGate]:
        """Visit an external gate operation element.

        Args:
            operation (qasm3_ast.QuantumGate): The external gate operation to visit.
            inverse (bool): Whether the operation is an inverse operation. Defaults to False.

                            If True, the gate operation is applied in reverse order and the
                            inverse modifier is appended to each gate call.
                            See https://openqasm.com/language/gates.html#inverse-modifier
                            for more clarity.

        Returns:
            list[qasm3_ast.QuantumGate]: The quantum gate that was collected.
        """

        logger.debug("Visiting external gate operation '%s'", str(operation))
        gate_name: str = operation.name.name

        if gate_name in self._custom_gates:
            # Ignore result, this is just for validation
            self._visit_custom_gate_operation(operation, inverse=inverse)
            # Don't need to check if custom gate exists, since we just validated the call
            gate_qubit_count = len(self._custom_gates[gate_name].qubits)
        else:
            # Ignore result, this is just for validation
            self._visit_basic_gate_operation(operation, inverse=inverse)
            # Don't need to check if basic gate exists, since we just validated the call
            _, gate_qubit_count = map_qasm_op_to_callable(operation.name.name)

        op_parameters = [
            qasm3_ast.FloatLiteral(param) for param in self._get_op_parameters(operation)
        ]

        self._push_context(Context.GATE)

        modifiers = []
        if inverse:
            modifiers = [qasm3_ast.QuantumGateModifier(qasm3_ast.GateModifierName.inv, None)]

        def gate_function(*qubits):
            return [
                qasm3_ast.QuantumGate(
                    modifiers=modifiers,
                    name=qasm3_ast.Identifier(gate_name),
                    qubits=list(qubits),
                    arguments=list(op_parameters),
                )
            ]

        all_targets = self._unroll_multiple_target_qubits(operation, gate_qubit_count)
        result = self._broadcast_gate_operation(gate_function, all_targets)

        self._restore_context()
        if self._check_only:
            return []

        return result

    def _visit_phase_operation(
        self, operation: qasm3_ast.QuantumPhase, inverse: bool = False
    ) -> list[qasm3_ast.QuantumPhase]:
        """Visit a phase operation element.

        Args:
            operation (qasm3_ast.QuantumPhase): The phase operation to visit.
            inverse (bool): Whether the operation is an inverse operation. Defaults to False.

        Returns:
            list[qasm3_ast.Statement]: The unrolled quantum phase operation.
        """
        logger.debug("Visiting phase operation '%s'", str(operation))

        evaluated_arg = Qasm3ExprEvaluator.evaluate_expression(operation.argument)[0]
        if inverse:
            evaluated_arg = -1 * evaluated_arg
        # remove the modifiers, as we have already applied the inverse
        operation.modifiers = []

        operation.argument = qasm3_ast.FloatLiteral(value=evaluated_arg)
        # no qubit evaluation to be done here
        # if args are provided in global scope, then we should raise error
        if self._in_global_scope() and len(operation.qubits) != 0:
            raise_qasm3_error(
                f"Qubit arguments not allowed for phase operation {str(operation)} in global scope",
                span=operation.span,
            )

        # if it were in function scope, then the args would have been evaluated and added to the
        # qubit list
        if self._check_only:
            return []

        return [operation]

    def _collapse_gate_modifiers(
        self, operation: Union[qasm3_ast.QuantumGate, qasm3_ast.QuantumPhase]
    ) -> tuple:
        """Collapse the gate modifiers of a gate operation.
           Some analysis is required to get this result.
           The basic idea is that any power operation is multiplied and inversions are toggled.
           The placement of the inverse operation does not matter.

        Args:
            operation (qasm3_ast.QuantumGate): The gate operation to collapse modifiers for.

        Returns:
            tuple[Any, Any]: The power and inverse values of the gate operation.
        """
        power_value, inverse_value = 1, False

        for modifier in operation.modifiers:
            modifier_name = modifier.modifier
            if modifier_name == qasm3_ast.GateModifierName.pow and modifier.argument is not None:
                current_power = Qasm3ExprEvaluator.evaluate_expression(modifier.argument)[0]
                if current_power < 0:
                    inverse_value = not inverse_value
                power_value = power_value * abs(current_power)
            elif modifier_name == qasm3_ast.GateModifierName.inv:
                inverse_value = not inverse_value
            elif modifier_name in [
                qasm3_ast.GateModifierName.ctrl,
                qasm3_ast.GateModifierName.negctrl,
            ]:
                raise_qasm3_error(
                    f"Controlled modifier gates not yet supported in gate operation {operation}",
                    err_type=NotImplementedError,
                    span=operation.span,
                )
        return (power_value, inverse_value)

    def _visit_generic_gate_operation(
        self, operation: Union[qasm3_ast.QuantumGate, qasm3_ast.QuantumPhase]
    ) -> list[Union[qasm3_ast.QuantumGate, qasm3_ast.QuantumPhase]]:
        """Visit a gate operation element.

        Args:
            operation (qasm3_ast.QuantumGate): The gate operation to visit.

        Returns:
            None
        """
        power_value, inverse_value = self._collapse_gate_modifiers(operation)
        operation = copy.deepcopy(operation)

        # only needs to be done once for a gate operation
        if (
            len(operation.qubits) > 0
            and not self._in_gate_scope()
            and len(self._function_qreg_size_map) > 0
        ):
            # we are in SOME function scope
            # transform qubits to use the global qreg identifiers
            operation.qubits = (
                Qasm3Transformer.transform_function_qubits(  # type: ignore [assignment]
                    operation,
                    self._function_qreg_size_map[-1],
                    self._function_qreg_transform_map[-1],
                )
            )
        # Applying the inverse first and then the power is same as
        # apply the power first and then inverting the result
        result: list[Union[qasm3_ast.QuantumGate, qasm3_ast.QuantumPhase]] = []
        for _ in range(power_value):
            if isinstance(operation, qasm3_ast.QuantumPhase):
                result.extend(self._visit_phase_operation(operation, inverse_value))
            elif operation.name.name in self._external_gates:
                result.extend(self._visit_external_gate_operation(operation, inverse_value))
            elif operation.name.name in self._custom_gates:
                result.extend(self._visit_custom_gate_operation(operation, inverse_value))
            else:
                result.extend(self._visit_basic_gate_operation(operation, inverse_value))

        if self._check_only:
            return []

        return result

    def _visit_constant_declaration(
        self, statement: qasm3_ast.ConstantDeclaration
    ) -> list[qasm3_ast.Statement]:
        """
        Visit a constant declaration element. Const can only be declared for scalar
        type variables and not arrays. Assignment is mandatory in constant declaration.

        Args:
            statement (qasm3_ast.ConstantDeclaration): The constant declaration to visit.

        Returns:
            None
        """
        statements = []
        var_name = statement.identifier.name

        if var_name in CONSTANTS_MAP:
            raise_qasm3_error(
                f"Can not declare variable with keyword name {var_name}", span=statement.span
            )
        if self._check_in_scope(var_name):
            raise_qasm3_error(f"Re-declaration of variable {var_name}", span=statement.span)
        init_value, stmts = Qasm3ExprEvaluator.evaluate_expression(
            statement.init_expression, const_expr=True
        )
        statements.extend(stmts)

        base_type = statement.type
        if isinstance(base_type, qasm3_ast.BoolType):
            base_size = 1
        elif hasattr(base_type, "size"):
            if base_type.size is None:
                base_size = 32  # default for now
            else:
                base_size = Qasm3ExprEvaluator.evaluate_expression(base_type.size, const_expr=True)[
                    0
                ]
                if not isinstance(base_size, int) or base_size <= 0:
                    raise_qasm3_error(
                        f"Invalid base size {base_size} for variable {var_name}",
                        span=statement.span,
                    )

        variable = Variable(var_name, base_type, base_size, [], init_value, is_constant=True)

        # cast + validation
        variable.value = Qasm3Validator.validate_variable_assignment_value(variable, init_value)

        self._add_var_in_scope(variable)

        if self._check_only:
            return []

        return statements

    # pylint: disable=too-many-branches, too-many-statements, too-many-locals
    def _visit_classical_declaration(
        self, statement: qasm3_ast.ClassicalDeclaration
    ) -> list[qasm3_ast.Statement]:
        """Visit a classical operation element.

        Args:
            statement (ClassicalType): The classical operation to visit.

        Returns:
            None
        """
        statements = []
        var_name = statement.identifier.name
        if var_name in CONSTANTS_MAP:
            raise_qasm3_error(
                f"Can not declare variable with keyword name {var_name}", span=statement.span
            )
        if self._check_in_scope(var_name):
            if self._in_block_scope() and var_name not in self._get_curr_scope():
                # we can re-declare variables once in block scope even if they are
                # present in the parent scope
                # Eg. int a = 10;
                #     { int a = 20;} // is valid
                pass
            else:
                raise_qasm3_error(f"Re-declaration of variable {var_name}", span=statement.span)

        init_value = None
        base_type = statement.type
        dimensions = []
        final_dimensions = []

        if isinstance(base_type, qasm3_ast.ArrayType):
            dimensions = base_type.dimensions
            base_type = base_type.base_type

        base_size = 1
        if not isinstance(base_type, qasm3_ast.BoolType):
            initial_size = 1 if isinstance(base_type, qasm3_ast.BitType) else 32
            base_size = (
                initial_size
                if not hasattr(base_type, "size") or base_type.size is None
                else Qasm3ExprEvaluator.evaluate_expression(base_type.size, const_expr=True)[0]
            )
        Qasm3Validator.validate_classical_type(base_type, base_size, var_name, statement.span)

        # initialize the bit register
        if isinstance(base_type, qasm3_ast.BitType):
            final_dimensions = [base_size]
            init_value = np.full(final_dimensions, 0)

        if len(dimensions) > 0:
            # bit type arrays are not allowed
            if isinstance(base_type, qasm3_ast.BitType):
                raise_qasm3_error(
                    f"Can not declare array {var_name} with type 'bit'", span=statement.span
                )
            if len(dimensions) > MAX_ARRAY_DIMENSIONS:
                raise_qasm3_error(
                    f"Invalid dimensions {len(dimensions)} for array declaration for {var_name}. "
                    f"Max allowed dimensions is {MAX_ARRAY_DIMENSIONS}",
                    span=statement.span,
                )

            for dim in dimensions:
                dim_value = Qasm3ExprEvaluator.evaluate_expression(dim, const_expr=True)[0]
                if not isinstance(dim_value, int) or dim_value <= 0:
                    raise_qasm3_error(
                        f"Invalid dimension size {dim_value} in array declaration for {var_name}",
                        span=statement.span,
                    )
                final_dimensions.append(dim_value)

            init_value = np.full(final_dimensions, None)

        # populate the variable
        if statement.init_expression:
            if isinstance(statement.init_expression, qasm3_ast.ArrayLiteral):
                init_value = self._evaluate_array_initialization(
                    statement.init_expression, final_dimensions, base_type
                )
            else:
                init_value, stmts = Qasm3ExprEvaluator.evaluate_expression(
                    statement.init_expression
                )
                statements.extend(stmts)

        variable = Variable(
            var_name,
            base_type,
            base_size,
            final_dimensions,
            init_value,
            is_register=isinstance(base_type, qasm3_ast.BitType),
        )

        # validate the assignment
        if statement.init_expression:
            if isinstance(init_value, np.ndarray):
                assert variable.dims is not None
                Qasm3Validator.validate_array_assignment_values(variable, variable.dims, init_value)
            else:
                variable.value = Qasm3Validator.validate_variable_assignment_value(
                    variable, init_value
                )
        self._add_var_in_scope(variable)

        if isinstance(base_type, qasm3_ast.BitType):
            self._global_creg_size_map[var_name] = base_size
            current_classical_size = len(self._clbit_labels)
            for i in range(base_size):
                self._clbit_labels[f"{var_name}_{i}"] = current_classical_size + i
                self._module._clbit_depths[(var_name, i)] = ClbitDepthNode(var_name, i)

            self._label_scope_level[self._curr_scope].add(var_name)

            if hasattr(statement.type, "size"):
                statement.type.size = (
                    qasm3_ast.IntegerLiteral(1)
                    if statement.type.size is None
                    else qasm3_ast.IntegerLiteral(base_size)
                )
            statements.append(statement)
            self._module._add_classical_register(var_name, base_size)

        if self._check_only:
            return []

        return statements

    def _visit_classical_assignment(
        self, statement: qasm3_ast.ClassicalAssignment
    ) -> list[qasm3_ast.Statement]:
        """Visit a classical assignment element.

        Args:
            statement (qasm3_ast.ClassicalAssignment): The classical assignment to visit.

        Returns:
            list[qasm3_ast.Statement]: The list of statements generated by the assignment.
        """
        statements = []
        lvalue = statement.lvalue
        lvar_name = lvalue.name
        if isinstance(lvar_name, qasm3_ast.Identifier):
            lvar_name = lvar_name.name

        lvar = self._get_from_visible_scope(lvar_name)
        if lvar is None:  # we check for none here, so type errors are irrelevant afterwards
            raise_qasm3_error(f"Undefined variable {lvar_name} in assignment", span=statement.span)
        if lvar.is_constant:  # type: ignore[union-attr]
            raise_qasm3_error(
                f"Assignment to constant variable {lvar_name} not allowed", span=statement.span
            )
        binary_op: Union[str, None, qasm3_ast.BinaryOperator] = None
        if statement.op != qasm3_ast.AssignmentOperator["="]:
            # eg. j += 1 -> broken down to j = j + 1
            binary_op = statement.op.name.removesuffix("=")
            binary_op = qasm3_ast.BinaryOperator[binary_op]

        # rvalue will be an evaluated value (scalar, list)
        # if rvalue is a list, we want a copy of it
        rvalue = statement.rvalue
        if binary_op is not None:
            rvalue = qasm3_ast.BinaryExpression(
                lhs=lvalue, op=binary_op, rhs=rvalue  # type: ignore[arg-type]
            )
        rvalue_raw, rhs_stmts = Qasm3ExprEvaluator.evaluate_expression(
            rvalue
        )  # consists of scope check and index validation
        statements.extend(rhs_stmts)

        # cast + validation
        rvalue_eval = None
        if not isinstance(rvalue_raw, np.ndarray):
            # rhs is a scalar
            rvalue_eval = Qasm3Validator.validate_variable_assignment_value(
                lvar, rvalue_raw  # type: ignore[arg-type]
            )
        else:  # rhs is a list
            rvalue_dimensions = list(rvalue_raw.shape)

            # validate that the values inside rvar are valid for lvar
            Qasm3Validator.validate_array_assignment_values(
                variable=lvar,  # type: ignore[arg-type]
                dimensions=rvalue_dimensions,
                values=rvalue_raw,  # type: ignore[arg-type]
            )
            rvalue_eval = rvalue_raw

        if lvar.readonly:  # type: ignore[union-attr]
            raise_qasm3_error(
                f"Assignment to readonly variable '{lvar_name}' not allowed in function call",
                span=statement.span,
            )

        # lvalue will be the variable which will HOLD this value
        if isinstance(lvalue, qasm3_ast.IndexedIdentifier):
            # stupid indices structure in openqasm :/
            if len(lvalue.indices[0]) > 1:  # type: ignore[arg-type]
                l_indices = lvalue.indices[0]
            else:
                l_indices = [idx[0] for idx in lvalue.indices]  # type: ignore[assignment, index]

            validated_l_indices = Qasm3Analyzer.analyze_classical_indices(
                l_indices, lvar, Qasm3ExprEvaluator  # type: ignore[arg-type]
            )
            Qasm3Transformer.update_array_element(
                multi_dim_arr=lvar.value,  # type: ignore[union-attr, arg-type]
                indices=validated_l_indices,
                value=rvalue_eval,
            )
        else:
            lvar.value = rvalue_eval  # type: ignore[union-attr]
        self._update_var_in_scope(lvar)  # type: ignore[arg-type]

        if self._check_only:
            return []

        return statements

    def _evaluate_array_initialization(
        self, array_literal: qasm3_ast.ArrayLiteral, dimensions: list[int], base_type: Any
    ) -> np.ndarray:
        """Evaluate an array initialization.

        Args:
            array_literal (qasm3_ast.ArrayLiteral): The array literal to evaluate.
            dimensions (list[int]): The dimensions of the array.
            base_type (Any): The base type of the array.

        Returns:
            np.ndarray: The evaluated array initialization.
        """
        init_values = []
        for value in array_literal.values:
            if isinstance(value, qasm3_ast.ArrayLiteral):
                nested_array = self._evaluate_array_initialization(value, dimensions[1:], base_type)
                init_values.append(nested_array)
            else:
                eval_value = Qasm3ExprEvaluator.evaluate_expression(value)[0]
                init_values.append(eval_value)

        return np.array(init_values, dtype=ARRAY_TYPE_MAP[base_type.__class__])

    def _visit_branching_statement(
        self, statement: qasm3_ast.BranchingStatement
    ) -> list[qasm3_ast.Statement]:
        """Visit a branching statement element.

        Args:
            statement (qasm3_ast.BranchingStatement): The branching statement to visit.

        Returns:
            None
        """
        self._push_context(Context.BLOCK)
        self._push_scope({})
        self._curr_scope += 1
        self._label_scope_level[self._curr_scope] = set()

        result = []
        condition = statement.condition

        if not statement.if_block:
            raise_qasm3_error("Missing if block", span=statement.span)

        if Qasm3ExprEvaluator.classical_register_in_expr(condition):
            # leave this condition as is, and start unrolling the block

            # here, the lhs CAN only be a classical register as QCs won't have
            # ability to evaluate expressions in the condition

            reg_id, reg_name, rhs_value = Qasm3Transformer.get_branch_params(condition)

            if reg_name not in self._global_creg_size_map:
                raise_qasm3_error(
                    f"Missing register declaration for {reg_name} in {condition}",
                    span=statement.span,
                )
            if reg_id is not None:
                Qasm3Validator.validate_register_index(
                    reg_id, self._global_creg_size_map[reg_name], qubit=False
                )

            new_lhs = (
                qasm3_ast.IndexExpression(
                    collection=qasm3_ast.Identifier(name=reg_name),
                    index=[qasm3_ast.IntegerLiteral(reg_id)],
                )
                if reg_id is not None
                else qasm3_ast.Identifier(name=reg_name)
            )
            assert isinstance(rhs_value, (bool, int))
            new_rhs = (
                qasm3_ast.BooleanLiteral(rhs_value)
                if isinstance(rhs_value, bool)
                else qasm3_ast.IntegerLiteral(rhs_value)
            )

            new_if_block = qasm3_ast.BranchingStatement(
                condition=qasm3_ast.BinaryExpression(
                    op=qasm3_ast.BinaryOperator["=="],
                    lhs=new_lhs,
                    rhs=new_rhs,
                ),
                if_block=self.visit_basic_block(statement.if_block),
                else_block=self.visit_basic_block(statement.else_block),
            )
            result.append(new_if_block)

        else:
            # here we can unroll the block depending on the condition
            positive_branching = Qasm3ExprEvaluator.evaluate_expression(condition)[0] != 0
            block_to_visit = statement.if_block if positive_branching else statement.else_block

            result.extend(self.visit_basic_block(block_to_visit))  # type: ignore[arg-type]

        del self._label_scope_level[self._curr_scope]
        self._curr_scope -= 1
        self._pop_scope()
        self._restore_context()

        if self._check_only:
            return []

        return result  # type: ignore[return-value]

    def _visit_forin_loop(self, statement: qasm3_ast.ForInLoop) -> list[qasm3_ast.Statement]:
        # Compute loop variable values
        if isinstance(statement.set_declaration, qasm3_ast.RangeDefinition):
            init_exp = statement.set_declaration.start
            startval = Qasm3ExprEvaluator.evaluate_expression(init_exp)[0]
            range_def = statement.set_declaration
            stepval = (
                1
                if range_def.step is None
                else Qasm3ExprEvaluator.evaluate_expression(range_def.step)[0]
            )
            endval = Qasm3ExprEvaluator.evaluate_expression(range_def.end)[0]
            irange = list(range(startval, endval + stepval, stepval))
        elif isinstance(statement.set_declaration, qasm3_ast.DiscreteSet):
            init_exp = statement.set_declaration.values[0]
            irange = [
                Qasm3ExprEvaluator.evaluate_expression(exp)[0]
                for exp in statement.set_declaration.values
            ]
        else:
            raise ValidationError(
                f"Unexpected type {type(statement.set_declaration)} of set_declaration in loop."
            )

        i: Optional[Variable]  # will store iteration Variable to update to loop scope

        result = []
        for ival in irange:
            self._push_context(Context.BLOCK)
            self._push_scope({})

            # Initialize loop variable in loop scope
            # need to re-declare as we discard the block scope in subsequent
            # iterations of the loop
            result.extend(
                self._visit_classical_declaration(
                    qasm3_ast.ClassicalDeclaration(statement.type, statement.identifier, init_exp)
                )
            )
            i = self._get_from_visible_scope(statement.identifier.name)

            # Update scope with current value of loop Variable
            if i is not None:
                i.value = ival
                self._update_var_in_scope(i)

            result.extend(self.visit_basic_block(statement.block))

            # scope not persistent between loop iterations
            self._pop_scope()
            self._restore_context()

            # as we are only checking compile time errors
            # not runtime errors, we can break here
            if self._check_only:
                return []
        return result

    def _visit_subroutine_definition(self, statement: qasm3_ast.SubroutineDefinition) -> list[None]:
        """Visit a subroutine definition element.
           Reference: https://openqasm.com/language/subroutines.html#subroutines

        Args:
            statement (qasm3_ast.SubroutineDefinition): The subroutine definition to visit.

        Returns:
            None
        """
        fn_name = statement.name.name

        if fn_name in CONSTANTS_MAP:
            raise_qasm3_error(
                f"Subroutine name '{fn_name}' is a reserved keyword", span=statement.span
            )

        if fn_name in self._subroutine_defns:
            raise_qasm3_error(f"Redefinition of subroutine '{fn_name}'", span=statement.span)

        if self._check_in_scope(fn_name):
            raise_qasm3_error(
                f"Can not declare subroutine with name '{fn_name}' as "
                "it is already declared as a variable",
                span=statement.span,
            )

        self._subroutine_defns[fn_name] = statement

        return []

    # pylint: disable=too-many-locals, too-many-statements
    def _visit_function_call(
        self, statement: qasm3_ast.FunctionCall
    ) -> tuple[Any, list[qasm3_ast.Statement]]:
        """Visit a function call element.

        Args:
            statement (qasm3_ast.FunctionCall): The function call to visit.
        Returns:
            None

        """
        fn_name = statement.name.name
        if fn_name not in self._subroutine_defns:
            raise_qasm3_error(f"Undefined subroutine '{fn_name}' was called", span=statement.span)

        subroutine_def = self._subroutine_defns[fn_name]

        if len(statement.arguments) != len(subroutine_def.arguments):
            raise_qasm3_error(
                f"Parameter count mismatch for subroutine '{fn_name}'. Expected "
                f"{len(subroutine_def.arguments)} but got {len(statement.arguments)} in call",
                span=statement.span,
            )

        duplicate_qubit_detect_map: dict = {}
        qubit_transform_map: dict = {}  # {(formal arg, idx) : (actual arg, idx)}
        formal_qreg_size_map: dict = {}

        quantum_vars, classical_vars = [], []
        for actual_arg, formal_arg in zip(statement.arguments, subroutine_def.arguments):
            if isinstance(formal_arg, qasm3_ast.ClassicalArgument):
                classical_vars.append(
                    Qasm3SubroutineProcessor.process_classical_arg(
                        formal_arg, actual_arg, fn_name, statement.span
                    )
                )
            else:
                quantum_vars.append(
                    Qasm3SubroutineProcessor.process_quantum_arg(
                        formal_arg,
                        actual_arg,
                        formal_qreg_size_map,
                        duplicate_qubit_detect_map,
                        qubit_transform_map,
                        fn_name,
                        statement.span,
                    )
                )

        self._push_scope({})
        self._curr_scope += 1
        self._label_scope_level[self._curr_scope] = set()
        self._push_context(Context.FUNCTION)

        for var in quantum_vars:
            self._add_var_in_scope(var)

        for var in classical_vars:
            self._add_var_in_scope(var)

        # push qubit transform maps
        self._function_qreg_size_map.append(formal_qreg_size_map)
        self._function_qreg_transform_map.append(qubit_transform_map)

        return_statement = None
        result = []
        for function_op in subroutine_def.body:
            if isinstance(function_op, qasm3_ast.ReturnStatement):
                return_statement = copy.deepcopy(function_op)
                break
            result.extend(self.visit_statement(copy.deepcopy(function_op)))

        return_value = None
        if return_statement:
            return_value, stmts = Qasm3ExprEvaluator.evaluate_expression(
                return_statement.expression
            )
            return_value = Qasm3Validator.validate_return_statement(
                subroutine_def, return_statement, return_value
            )
            result.extend(stmts)

        # remove qubit transformation map
        self._function_qreg_transform_map.pop()
        self._function_qreg_size_map.pop()

        self._restore_context()
        del self._label_scope_level[self._curr_scope]
        self._curr_scope -= 1
        self._pop_scope()

        if self._check_only:
            return return_value, []

        return return_value, result

    def _visit_while_loop(self, statement: qasm3_ast.WhileLoop) -> None:
        pass

    def _visit_alias_statement(self, statement: qasm3_ast.AliasStatement) -> list[None]:
        """Visit an alias statement element.

        Args:
            statement (qasm3_ast.AliasStatement): The alias statement to visit.

        Returns:
            None
        """
        # pylint: disable=too-many-branches
        target = statement.target
        value = statement.value

        alias_reg_name: str = target.name
        alias_reg_size: int = 0
        aliased_reg_name: str = ""
        aliased_reg_size: int = 0

        # this will only build a global alias map

        # whenever we are referring to qubits , we will first check in the global map of registers

        # if the register is present, we will use the global map to get the qubit labels
        # if not, we will check the alias map for the labels

        # see self._get_op_bits for details

        # Alias should not be redeclared earlier as a variable or a constant
        if self._check_in_scope(alias_reg_name):
            raise_qasm3_error(f"Re-declaration of variable '{alias_reg_name}'", span=statement.span)
        self._label_scope_level[self._curr_scope].add(alias_reg_name)

        if isinstance(value, qasm3_ast.Identifier):
            aliased_reg_name = value.name
        elif isinstance(value, qasm3_ast.IndexExpression) and isinstance(
            value.collection, qasm3_ast.Identifier
        ):
            aliased_reg_name = value.collection.name
        else:
            raise_qasm3_error(f"Unsupported aliasing {statement}", span=statement.span)

        if aliased_reg_name not in self._global_qreg_size_map:
            raise_qasm3_error(
                f"Qubit register {aliased_reg_name} not found for aliasing", span=statement.span
            )
        aliased_reg_size = self._global_qreg_size_map[aliased_reg_name]
        if isinstance(value, qasm3_ast.Identifier):  # "let alias = q;"
            for i in range(aliased_reg_size):
                self._alias_qubit_labels[(alias_reg_name, i)] = (aliased_reg_name, i)
            alias_reg_size = aliased_reg_size
        elif isinstance(value, qasm3_ast.IndexExpression):
            if isinstance(value.index, qasm3_ast.DiscreteSet):  # "let alias = q[{0,1}];"
                qids = Qasm3Transformer.extract_values_from_discrete_set(value.index)
                for i, qid in enumerate(qids):
                    Qasm3Validator.validate_register_index(
                        qid, self._global_qreg_size_map[aliased_reg_name], qubit=True
                    )
                    self._alias_qubit_labels[(alias_reg_name, i)] = (aliased_reg_name, qid)
                alias_reg_size = len(qids)
            elif len(value.index) != 1:  # like "let alias = q[0,1];"?
                raise_qasm3_error(
                    "An index set can be specified by a single integer (signed or unsigned), "
                    "a comma-separated list of integers contained in braces {a,b,c,…}, "
                    "or a range",
                    span=statement.span,
                )
            elif isinstance(value.index[0], qasm3_ast.IntegerLiteral):  # "let alias = q[0];"
                qid = value.index[0].value
                Qasm3Validator.validate_register_index(
                    qid, self._global_qreg_size_map[aliased_reg_name], qubit=True
                )
                self._alias_qubit_labels[(alias_reg_name, 0)] = (
                    aliased_reg_name,
                    value.index[0].value,
                )
                alias_reg_size = 1
            elif isinstance(value.index[0], qasm3_ast.RangeDefinition):  # "let alias = q[0:1:2];"
                qids = Qasm3Transformer.get_qubits_from_range_definition(
                    value.index[0],
                    aliased_reg_size,
                    is_qubit_reg=True,
                )
                for i, qid in enumerate(qids):
                    self._alias_qubit_labels[(alias_reg_name, i)] = (aliased_reg_name, qid)
                alias_reg_size = len(qids)

        self._global_alias_size_map[alias_reg_name] = alias_reg_size

        logger.debug("Added labels for aliasing '%s'", target)

        return []

    def _visit_switch_statement(  # type: ignore[return]
        self, statement: qasm3_ast.SwitchStatement
    ) -> list[qasm3_ast.Statement]:
        """Visit a switch statement element.

        Args:
            statement (qasm3_ast.SwitchStatement): The switch statement to visit.

        Returns:
            list[qasm3_ast.Statement]: The list of statements generated by the switch statement.
        """
        # 1. analyze the target - it should ONLY be int, not casted
        switch_target = statement.target
        switch_target_name = ""
        # either identifier or indexed expression
        if isinstance(switch_target, qasm3_ast.Identifier):
            switch_target_name = switch_target.name
        elif isinstance(switch_target, qasm3_ast.IndexExpression):
            switch_target_name, _ = Qasm3Analyzer.analyze_index_expression(switch_target)

        if not Qasm3Validator.validate_variable_type(
            self._get_from_visible_scope(switch_target_name), qasm3_ast.IntType
        ):
            raise_qasm3_error(
                f"Switch target {switch_target_name} must be of type int", span=statement.span
            )

        switch_target_val = Qasm3ExprEvaluator.evaluate_expression(switch_target)[0]

        if len(statement.cases) == 0:
            raise_qasm3_error("Switch statement must have at least one case", span=statement.span)

        # 2. handle the cases of the switch stmt
        #    each element in the list of the values
        #    should be of const int type and no duplicates should be present

        def _evaluate_case(statements):
            # can not put 'context' outside
            # BECAUSE the case expression CAN CONTAIN VARS from global scope
            self._push_context(Context.BLOCK)
            self._push_scope({})
            result = []
            for stmt in statements:
                Qasm3Validator.validate_statement_type(SWITCH_BLACKLIST_STMTS, stmt, "switch")
                result.extend(self.visit_statement(stmt))

            self._pop_scope()
            self._restore_context()
            if self._check_only:
                return []
            return result

        case_fulfilled = False
        for case in statement.cases:
            case_list = case[0]
            seen_values = set()
            for case_expr in case_list:
                # 3. evaluate and verify that it is a const_expression
                # using vars only within the scope AND each component is either a
                # literal OR type int
                case_val = Qasm3ExprEvaluator.evaluate_expression(
                    case_expr, const_expr=True, reqd_type=qasm3_ast.IntType
                )[0]

                if case_val in seen_values:
                    raise_qasm3_error(
                        f"Duplicate case value {case_val} in switch statement", span=case_expr.span
                    )

                seen_values.add(case_val)

                if case_val == switch_target_val:
                    case_fulfilled = True

            if case_fulfilled:
                case_stmts = case[1].statements
                return _evaluate_case(case_stmts)

        if not case_fulfilled and statement.default:
            default_stmts = statement.default.statements
            return _evaluate_case(default_stmts)

    def _visit_include(self, include: qasm3_ast.Include) -> list[qasm3_ast.Statement]:
        """Visit an include statement element.

        Args:
            include (qasm3_ast.Include): The include statement to visit.

        Returns:
            None
        """
        filename = include.filename
        if filename in self._included_files:
            raise_qasm3_error(f"File '{filename}' already included", span=include.span)
        self._included_files.add(filename)
        if self._check_only:
            return []

        return [include]

    def visit_statement(self, statement: qasm3_ast.Statement) -> list[qasm3_ast.Statement]:
        """Visit a statement element.

        Args:
            statement (qasm3_ast.Statement): The statement to visit.

        Returns:
            None
        """
        logger.debug("Visiting statement '%s'", str(statement))
        result = []
        visit_map = {
            qasm3_ast.Include: self._visit_include,  # No operation
            qasm3_ast.QuantumMeasurementStatement: self._visit_measurement,
            qasm3_ast.QuantumReset: self._visit_reset,
            qasm3_ast.QuantumBarrier: self._visit_barrier,
            qasm3_ast.QubitDeclaration: self._visit_quantum_register,
            qasm3_ast.QuantumGateDefinition: self._visit_gate_definition,
            qasm3_ast.QuantumGate: self._visit_generic_gate_operation,
            qasm3_ast.QuantumPhase: self._visit_generic_gate_operation,
            qasm3_ast.ClassicalDeclaration: self._visit_classical_declaration,
            qasm3_ast.ClassicalAssignment: self._visit_classical_assignment,
            qasm3_ast.ConstantDeclaration: self._visit_constant_declaration,
            qasm3_ast.BranchingStatement: self._visit_branching_statement,
            qasm3_ast.ForInLoop: self._visit_forin_loop,
            qasm3_ast.AliasStatement: self._visit_alias_statement,
            qasm3_ast.SwitchStatement: self._visit_switch_statement,
            qasm3_ast.SubroutineDefinition: self._visit_subroutine_definition,
            qasm3_ast.ExpressionStatement: lambda x: self._visit_function_call(x.expression),
            qasm3_ast.IODeclaration: lambda x: [],
        }

        visitor_function = visit_map.get(type(statement))

        if visitor_function:
            if isinstance(statement, qasm3_ast.ExpressionStatement):
                # these return a tuple of return value and list of statements
                _, ret_stmts = visitor_function(statement)  # type: ignore[operator]
                result.extend(ret_stmts)
            else:
                result.extend(visitor_function(statement))  # type: ignore[operator]
        else:
            raise_qasm3_error(
                f"Unsupported statement of type {type(statement)}", span=statement.span
            )
        return result

    def visit_basic_block(self, stmt_list: list[qasm3_ast.Statement]) -> list[qasm3_ast.Statement]:
        """Visit a basic block of statements.

        Args:
            stmt_list (list[qasm3_ast.Statement]): The list of statements to visit.

        Returns:
            list[qasm3_ast.Statement]: The list of unrolled statements.
        """
        result = []
        for stmt in stmt_list:
            result.extend(self.visit_statement(stmt))
        return result

    def finalize(self, unrolled_stmts):
        """Finalize the unrolled statements.
        Rules:
        - Remove qubit args from phase operations if ALL qubits are used
        To add more rules if needed

        Args:
            unrolled_stmts (list[qasm3_ast.Statement]): The list of unrolled statements.

        Returns:
            list[qasm3_ast.Statement]: The list of finalized statements.

        """
        # remove the gphase qubits if they use ALL qubits
        for stmt in unrolled_stmts:
            # Rule 1
            if isinstance(stmt, qasm3_ast.QuantumPhase):
                if len(stmt.qubits) == len(self._qubit_labels):
                    stmt.qubits = []
        return unrolled_stmts
