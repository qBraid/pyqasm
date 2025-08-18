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

# pylint: disable=too-many-lines

"""
Module defining Qasm Visitor.

"""
import copy
import logging
import re
import sys
from collections import OrderedDict, deque
from functools import partial
from io import StringIO
from typing import Any, Callable, Optional, Sequence, cast

import numpy as np
import openqasm3.ast as qasm3_ast
from openqasm3.printer import dumps

from pyqasm.analyzer import Qasm3Analyzer
from pyqasm.elements import (
    Capture,
    ClbitDepthNode,
    Context,
    Frame,
    InversionOp,
    QubitDepthNode,
    Variable,
    Waveform,
)
from pyqasm.exceptions import (
    BreakSignal,
    ContinueSignal,
    LoopControlSignal,
    LoopLimitExceededError,
    ValidationError,
    raise_qasm3_error,
)
from pyqasm.expressions import Qasm3ExprEvaluator
from pyqasm.maps import SWITCH_BLACKLIST_STMTS
from pyqasm.maps.expressions import (
    ARRAY_TYPE_MAP,
    CONSTANTS_MAP,
    FUNCTION_MAP,
    MAX_ARRAY_DIMENSIONS,
)
from pyqasm.maps.gates import (
    map_qasm_ctrl_op_to_callable,
    map_qasm_inv_op_to_callable,
    map_qasm_op_num_params,
    map_qasm_op_to_callable,
)
from pyqasm.pulse.expressions import (
    OPENPULSE_CAPTURE_FUNCTION_MAP,
    OPENPULSE_FRAME_FUNCTION_MAP,
    OPENPULSE_WAVEFORM_FUNCTION_MAP,
)
from pyqasm.pulse.utils import PulseUtils
from pyqasm.pulse.validator import PulseValidator
from pyqasm.pulse.visitor import OpenPulseVisitor
from pyqasm.scope import ScopeManager
from pyqasm.subroutines import Qasm3SubroutineProcessor
from pyqasm.transformer import Qasm3Transformer
from pyqasm.validator import Qasm3Validator

logger = logging.getLogger(__name__)
logger.propagate = False


# pylint: disable-next=too-many-instance-attributes
class QasmVisitor:
    """A visitor for basic OpenQASM program elements.

    This class is designed to traverse and interact with elements in an OpenQASM program.

    Args:
        module: The OpenQASM module to visit.
        scope_manager (ScopeManager): The scope manager to handle variable scopes.
        check_only (bool): If True, only check the program without executing it. Defaults to False.
        external_gates (list[str]): List of gates that should not be unrolled.
        unroll_barriers (bool): If True, barriers will be unrolled. Defaults to True.
        max_loop_iters (int): Max iterations for loops to prevent infinite loops. Defaults to 1e9.
        consolidate_qubits (bool): If True, consolidate all quantum registers into single register.
    """

    def __init__(  # pylint: disable=too-many-arguments
        self,
        module,
        scope_manager: ScopeManager,
        check_only: bool = False,
        external_gates: list[str] | None = None,
        unroll_barriers: bool = True,
        max_loop_iters: int = int(1e9),
        consolidate_qubits: bool = False,
    ):
        self._module = module
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
        self._subroutine_defns: dict[
            str, qasm3_ast.SubroutineDefinition | qasm3_ast.ExternDeclaration
        ] = {}
        self._check_only: bool = check_only
        self._unroll_barriers: bool = unroll_barriers
        self._recording_ext_gate_depth = False
        self._in_branching_statement: int = 0
        self._is_branch_qubits: set[tuple[str, int]] = set()
        self._is_branch_clbits: set[tuple[str, int]] = set()
        self._measurement_set: set[str] = set()
        self._init_utilities()
        self._loop_limit = max_loop_iters
        self._consolidate_qubits: bool = consolidate_qubits
        self._in_generic_gate_op_scope: int = 0
        self._qubit_register_offsets: OrderedDict = OrderedDict()
        self._qubit_register_max_offset = 0
        self._total_delay_duration_in_box = 0
        self._in_extern_function: bool = False
        self._openpulse_qubit_map: dict[str, set[str]] = {}
        self._total_pulse_qubits: int = 0

        self._scope_manager: ScopeManager = scope_manager
        self._openpulse_scope_manager: ScopeManager = ScopeManager()
        self._pulse_visitor = OpenPulseVisitor(
            qasm_visitor=self,
            check_only=check_only,
        )

    def _init_utilities(self):
        """Initialize the utilities for the visitor."""
        for class_obj in [Qasm3Transformer, Qasm3ExprEvaluator, Qasm3SubroutineProcessor]:
            class_obj.set_visitor_obj(self)

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
        try:
            register_size = (
                1
                if register.size is None
                else Qasm3ExprEvaluator.evaluate_expression(register.size, const_expr=True)[
                    0
                ]  # type: ignore[attr-defined]
            )
        except ValidationError as err:
            raise_qasm3_error(
                f"Invalid size '{dumps(register.size)}' for quantum "  # type: ignore[arg-type]
                f"register '{register.qubit.name}'",
                error_node=register,
                span=register.span,
                raised_from=err,
            )
        register.size = qasm3_ast.IntegerLiteral(register_size)
        register_name = register.qubit.name  # type: ignore[union-attr]

        size_map = self._global_qreg_size_map
        label_map = self._qubit_labels

        if self._scope_manager.check_in_scope(register_name):
            raise_qasm3_error(
                f"Re-declaration of quantum register with name '{register_name}'",
                error_node=register,
                span=register.span,
            )

        if register_name in CONSTANTS_MAP:
            raise_qasm3_error(
                f"Can not declare quantum register with keyword name '{register_name}'",
                error_node=register,
                span=register.span,
            )

        self._scope_manager.add_var_in_scope(
            Variable(
                name=register_name,
                base_type=qasm3_ast.QubitDeclaration,
                base_size=register_size,
                dims=None,
                value=None,
                span=register.span,
                is_qubit=True,
                is_constant=False,
            )
        )
        size_map[f"{register_name}"] = register_size

        for i in range(register_size):
            # required if indices are not used while applying a gate or measurement
            label_map[f"{register_name}_{i}"] = current_size + i
            self._module._qubit_depths[(register_name, i)] = QubitDepthNode(register_name, i)

        self._module._add_qubit_register(register_name, register_size)

        # _qubit_register_offsets maps each original quantum register to its
        # starting index in the consolidated register, enabling correct
        # translation of qubit indices after consolidation.
        if self._consolidate_qubits:
            self._qubit_register_offsets[register_name] = self._qubit_register_max_offset
            self._qubit_register_max_offset += register_size

        logger.debug("Added labels for register '%s'", str(register))

        if self._check_only:
            return []
        return [register]

    # pylint: disable-next=too-many-locals,too-many-branches
    def _get_op_bits(
        self,
        operation: Any,
        qubits: bool = True,
        function_qubit_sizes: Optional[dict[str, int]] = None,
    ) -> list[qasm3_ast.IndexedIdentifier]:
        """Get the quantum / classical bits for the operation.

        Args:
            operation (Any): The operation to get qubits for.
            qubits (bool): Whether the bits are quantum bits or classical bits. Defaults to True.
        Returns:
            list[qasm3_ast.IndexedIdentifier] : The bits for the operation.
        """
        openqasm_bits = []
        bit_list = []

        if isinstance(operation, qasm3_ast.QuantumMeasurementStatement):
            if qubits:
                bit_list = [operation.measure.qubit]
            else:
                assert operation.target is not None
                bit_list = [operation.target]
        elif isinstance(operation, qasm3_ast.QuantumPhase) and operation.qubits is None:
            for reg_name, reg_size in self._global_qreg_size_map.items():
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
            if isinstance(bit, qasm3_ast.IndexedIdentifier):
                reg_name = bit.name.name
            else:
                reg_name = bit.name

            max_register_size = 0
            reg_var = self._scope_manager.get_from_visible_scope(reg_name)
            if reg_var is None:
                if function_qubit_sizes is None:
                    err_msg = (
                        f"Missing {'qubit' if qubits else 'clbit'} register declaration "
                        f"for '{reg_name}' in {type(operation).__name__}"
                    )
                    raise_qasm3_error(
                        err_msg,
                        error_node=operation,
                        span=operation.span,
                    )
                # we are trying to replace the qubits inside a nested function
                assert function_qubit_sizes is not None
                reg_size = function_qubit_sizes.get(reg_name, None)
                if reg_size is not None:
                    max_register_size = reg_size

            if reg_var:
                assert isinstance(reg_var, Variable)
                max_register_size = reg_var.base_size

            if isinstance(bit, qasm3_ast.IndexedIdentifier):
                if isinstance(bit.indices[0], qasm3_ast.DiscreteSet):
                    bit_ids = Qasm3Transformer.extract_values_from_discrete_set(
                        bit.indices[0], operation
                    )
                elif isinstance(bit.indices[0][0], qasm3_ast.RangeDefinition):
                    bit_ids = Qasm3Transformer.get_qubits_from_range_definition(
                        bit.indices[0][0],
                        max_register_size,
                        is_qubit_reg=qubits,
                        op_node=operation,
                    )
                else:
                    bit_id = Qasm3ExprEvaluator.evaluate_expression(bit.indices[0][0])[0]
                    Qasm3Validator.validate_register_index(
                        bit_id, max_register_size, qubit=qubits, op_node=operation
                    )
                    bit_ids = [bit_id]
            else:
                bit_ids = list(range(max_register_size))

            if reg_var and reg_var.is_alias:
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

            openqasm_bits.extend(new_bits)

        return openqasm_bits

    def _check_variable_type_size(
        self, statement: qasm3_ast.Statement, var_name: str, var_format: str, base_type: Any
    ) -> int:
        """Get the size of the given variable type.

        Args:
            statement: current statement to get span.
            var_name(str): variable name of the current operation.
            base_type (Any): Base type of the variable.
            is_const (bool): whether the statement is constant declaration or not.
        Returns:
            Int: size of the variable base type.
        """
        base_size = 1
        if not isinstance(base_type, qasm3_ast.BoolType):
            initial_size = 1 if isinstance(base_type, qasm3_ast.BitType) else 32
            try:
                base_size = (
                    initial_size
                    if not hasattr(base_type, "size") or base_type.size is None
                    else Qasm3ExprEvaluator.evaluate_expression(base_type.size, const_expr=True)[0]
                )
                if (
                    isinstance(base_type, qasm3_ast.AngleType)
                    and self._module._compiler_angle_type_size
                ):
                    base_size = self._module._compiler_angle_type_size
            except ValidationError as err:
                raise_qasm3_error(
                    f"Invalid base size for {var_format} '{var_name}'",
                    error_node=statement,
                    span=statement.span,
                    raised_from=err,
                )
        if not isinstance(base_size, int) or base_size <= 0:
            raise_qasm3_error(
                f"Invalid base size '{base_size}' for {var_format} '{var_name}'",
                error_node=statement,
                span=statement.span,
            )
        return base_size

    # pylint: disable-next=too-many-arguments
    def _check_variable_cast_type(
        self,
        statement: qasm3_ast.Statement,
        val_type: Any,
        var_name: str,
        base_type: Any,
        base_size: Any,
        is_const: bool,
    ) -> None:
        """Checks the declaration type and cast type of current variable.

        Args:
            statement: current statement to get span.
            val_type(Any): type of cast to apply on variable.
            var_name(str): declaration variable name.
            base_type (Any): Base type of the declaration variable.
            base_size(Any): literal to get the base size of the declaration variable.
            is_const (bool): whether the statement is constant declaration or not.
        Returns:
            None
        """
        if not val_type:
            val_type = base_type

        var_format = "variable"
        if is_const:
            var_format = "constant"

        val_type_size = self._check_variable_type_size(statement, var_name, var_format, val_type)
        if not isinstance(val_type, type(base_type)) or val_type_size != base_size:
            raise_qasm3_error(
                f"Declaration type: "
                f"'{(type(base_type).__name__).replace('Type', '')}[{base_size}]' and "
                f"Cast type: '{(type(val_type).__name__).replace('Type', '')}[{val_type_size}]',"
                f" should be same for '{var_name}'",
                error_node=statement,
                span=statement.span,
            )

    def _qubit_register_consolidation(
        self, unrolled_stmts: list, total_qubits: int
    ) -> list[qasm3_ast.Statement]:
        """
        Consolidate all quantum registers into a single register '__PYQASM_QUBITS__'.

        Args:
            unrolled_stmts (list): The list of statements to process and modify in-place.

        Raises:
            ValidationError: If the total number of qubits exceeds the available device qubits,
                             or if the reserved register '__PYQASM_QUBITS__' is already declared
                             in the original QASM program.
        """
        if total_qubits > self._module._device_qubits:  # type: ignore
            raise_qasm3_error(
                # pylint: disable-next=line-too-long
                f"Total qubits '({total_qubits})' exceed device qubits '({self._module._device_qubits})'.",
            )

        global_scope = self._scope_manager.get_global_scope()
        for var, val in global_scope.items():
            if var == "__PYQASM_QUBITS__":
                raise_qasm3_error(
                    "Variable '__PYQASM_QUBITS__' is already defined",
                    span=val.span,
                )

        pyqasm_reg_id = qasm3_ast.Identifier("__PYQASM_QUBITS__")
        pyqasm_reg_size = qasm3_ast.IntegerLiteral(self._module._device_qubits)  # type: ignore
        pyqasm_reg_stmt = qasm3_ast.QubitDeclaration(pyqasm_reg_id, pyqasm_reg_size)

        _valid_statements: list[qasm3_ast.Statement] = []
        _valid_statements.append(pyqasm_reg_stmt)
        for stmt in unrolled_stmts:
            if not isinstance(stmt, qasm3_ast.QubitDeclaration):
                _valid_statements.append(stmt)

        return _valid_statements

    def _handle_function_init_expression(
        self, expression: Any, init_value: Any
    ) -> None | qasm3_ast.Expression:
        """Handle function initialization expression.

        Args:
            statement (Any): The statement to handle function initialization expression.
            init_value (Any): The value to handle function initialization expression.
        """
        if isinstance(expression, qasm3_ast.FunctionCall):
            func_name = expression.name.name
            if func_name in FUNCTION_MAP:
                if isinstance(init_value, (float, int)):
                    return qasm3_ast.FloatLiteral(init_value)
        return None

    def _handle_extern_function_cleanup(
        self, statements: list, statement: qasm3_ast.Statement
    ) -> None:
        """Clean up extern function state and modify statements if needed.

        Args:
            statements: List of statements to potentially modify
            statement: The statement to append if in extern function
        """
        if self._in_extern_function:
            self._in_extern_function = False
            statements.clear()
            statements.append(statement)

    def _validate_bitstring_literal_width(self, init_value, base_size, var_name, statement):
        if len(init_value) != base_size:
            raise_qasm3_error(
                f"Invalid bitstring literal '{init_value}' width [{len(init_value)}] "
                f"for variable '{var_name}' of size [{base_size}]",
                error_node=statement,
                span=statement.span,
            )

    def _visit_measurement(  # pylint: disable=too-many-locals,too-many-branches,too-many-statements
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
        if isinstance(source, qasm3_ast.Identifier):
            is_pulse_gate = False
            if source.name.startswith("$") and source.name[1:].isdigit():
                is_pulse_gate = True
                statement.measure.qubit.name = f"__PYQASM_QUBITS__[{source.name[1:]}]"
            elif source.name.startswith("__PYQASM_QUBITS__"):
                is_pulse_gate = True
                statement.measure.qubit.name = source.name
            if self._total_pulse_qubits <= 0 and sum(self._global_qreg_size_map.values()) == 0:
                raise_qasm3_error(
                    "Invalid no of qubits in pulse level measurement",
                    error_node=statement,
                    span=statement.span,
                )
            if is_pulse_gate:
                return [statement]
        # # TODO: handle in-function measurements
        source_name: str = (
            source.name if isinstance(source, qasm3_ast.Identifier) else source.name.name
        )
        if source_name not in self._global_qreg_size_map:
            raise_qasm3_error(
                f"Missing register declaration for '{source_name}' in measurement " f"operation",
                error_node=statement,
                span=statement.span,
            )

        source_ids = self._get_op_bits(statement, qubits=True)

        unrolled_measurements = []

        if not target:
            for src_id in source_ids:
                unrolled_measurements.append(
                    qasm3_ast.QuantumMeasurementStatement(
                        measure=qasm3_ast.QuantumMeasurement(qubit=src_id), target=None
                    )
                )
                # if measurement gate is not in branching statement
                if not self._in_branching_statement:
                    src_name, src_id = src_id.name.name, src_id.indices[0][0].value  # type: ignore
                    qubit_node = self._module._qubit_depths[(src_name, src_id)]
                    qubit_node.depth += 1
                    qubit_node.num_measurements += 1
        else:
            target_name: str = (
                target.name if isinstance(target, qasm3_ast.Identifier) else target.name.name
            )
            if target_name not in self._global_creg_size_map:
                raise_qasm3_error(
                    f"Missing register declaration for '{target_name}' in measurement "
                    f"operation",
                    error_node=statement,
                    span=statement.span,
                )

            target_ids = self._get_op_bits(statement, qubits=False)

            if len(source_ids) != len(target_ids):
                raise_qasm3_error(
                    f"Register sizes of {source_name} and {target_name} do not match "
                    "for measurement operation",
                    error_node=statement,
                    span=statement.span,
                )

            for src_id, tgt_id in zip(source_ids, target_ids):
                unrolled_measure = qasm3_ast.QuantumMeasurementStatement(
                    measure=qasm3_ast.QuantumMeasurement(qubit=src_id),
                    target=tgt_id if target else None,
                )
                # if measurement gate is not in branching statement
                if not self._in_branching_statement:
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

                    if isinstance(target, qasm3_ast.Identifier):
                        self._measurement_set.add(target.name)
                    elif isinstance(target, qasm3_ast.IndexedIdentifier):
                        self._measurement_set.add(target.name.name)

                unrolled_measurements.append(unrolled_measure)

        if self._consolidate_qubits:
            unrolled_measurements = cast(
                list[qasm3_ast.QuantumMeasurementStatement],
                Qasm3Transformer.consolidate_qubit_registers(
                    unrolled_measurements,
                    self._qubit_register_offsets,
                    self._global_qreg_size_map,
                    self._module._device_qubits,
                ),
            )

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
        if isinstance(statement.qubits, qasm3_ast.Identifier):
            is_pulse_gate = False
            if statement.qubits.name.startswith("$") and statement.qubits.name[1:].isdigit():
                is_pulse_gate = True
                statement.qubits.name = f"__PYQASM_QUBITS__[{statement.qubits.name[1:]}]"
            elif statement.qubits.name.startswith("__PYQASM_QUBITS__"):
                is_pulse_gate = True
                statement.qubits.name = statement.qubits.name
            if is_pulse_gate:
                return [statement]

        if len(self._function_qreg_size_map) > 0:  # atleast in SOME function scope
            # since we may have multiple function scopes, we need to transform the qubits
            # to use the global qreg identifiers
            for transform_map, size_map in zip(
                reversed(self._function_qreg_transform_map), reversed(self._function_qreg_size_map)
            ):
                statement.qubits = (
                    Qasm3Transformer.transform_function_qubits(  # type: ignore[assignment]
                        statement,
                        transform_map,
                        size_map,
                    )
                )
        qubit_ids = self._get_op_bits(statement, qubits=True)

        unrolled_resets = []
        for qid in qubit_ids:
            unrolled_reset = qasm3_ast.QuantumReset(qubits=qid)

            qubit_name, qubit_id = qid.name.name, qid.indices[0][0].value  # type: ignore
            if not self._in_branching_statement:
                qubit_node = self._module._qubit_depths[(qubit_name, qubit_id)]
                qubit_node.depth += 1
                qubit_node.num_resets += 1
            else:
                self._is_branch_qubits.add((qubit_name, qubit_id))

            unrolled_resets.append(unrolled_reset)

        if self._consolidate_qubits:
            unrolled_resets = cast(
                list[qasm3_ast.QuantumReset],
                Qasm3Transformer.consolidate_qubit_registers(
                    unrolled_resets,
                    self._qubit_register_offsets,
                    self._global_qreg_size_map,
                    self._module._device_qubits,
                ),
            )

        if self._check_only:
            return []

        return unrolled_resets

    def _visit_barrier(  # pylint: disable=too-many-locals, too-many-branches
        self, barrier: qasm3_ast.QuantumBarrier
    ) -> list[qasm3_ast.QuantumBarrier]:
        """Visit a barrier statement element.

        Args:
            statement (qasm3_ast.QuantumBarrier): The barrier statement to visit.

        Returns:
            None
        """
        valid_open_pulse_qubits = False
        for op_qubit in barrier.qubits:
            if isinstance(op_qubit, qasm3_ast.Identifier):
                if op_qubit.name.startswith("$") and op_qubit.name[1:].isdigit():
                    if int(op_qubit.name[1:]) >= self._total_pulse_qubits:
                        raise_qasm3_error(
                            f"Invalid pulse qubit index `{op_qubit.name}` on barrier",
                            error_node=barrier,
                            span=barrier.span,
                        )
                    valid_open_pulse_qubits = True
        if valid_open_pulse_qubits:
            return [barrier]
        # if barrier is applied to ALL qubits at once, we are fine
        if len(self._function_qreg_size_map) > 0:  # atleast in SOME function scope
            # we have multiple function scopes, so we need to transform the qubits
            # to use the global qreg identifiers

            # since we are changing the qubits to IndexedIdentifiers, we need to supress the
            # error for the type checker
            for transform_map, size_map in zip(
                reversed(self._function_qreg_transform_map), reversed(self._function_qreg_size_map)
            ):
                barrier.qubits = (
                    Qasm3Transformer.transform_function_qubits(  # type: ignore [assignment]
                        barrier,
                        transform_map,
                        size_map,
                    )
                )
        barrier_qubits = self._get_op_bits(barrier, qubits=True)
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

        if not self._unroll_barriers:
            if self._consolidate_qubits:
                barrier = cast(
                    qasm3_ast.QuantumBarrier,
                    Qasm3Transformer.consolidate_qubit_registers(
                        barrier,
                        self._qubit_register_offsets,
                        self._global_qreg_size_map,
                        self._module._device_qubits,
                    ),
                )
            return [barrier]

        if self._consolidate_qubits:
            unrolled_barriers = cast(
                list[qasm3_ast.QuantumBarrier],
                Qasm3Transformer.consolidate_qubit_registers(
                    unrolled_barriers,
                    self._qubit_register_offsets,
                    self._global_qreg_size_map,
                    self._module._device_qubits,
                ),
            )

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
            try:
                param_value = Qasm3ExprEvaluator.evaluate_expression(param)[0]
                param_list.append(param_value)
            except ValidationError as err:
                raise_qasm3_error(
                    f"Invalid parameter '{dumps(param)}' for gate '{operation.name.name}'",
                    error_node=operation,
                    span=operation.span,
                    raised_from=err,
                )

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
            raise_qasm3_error(
                f"Duplicate quantum gate definition for '{gate_name}'",
                error_node=definition,
                span=definition.span,
            )
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
        op_qubits = self._get_op_bits(operation, qubits=True)
        if len(op_qubits) <= 0 or len(op_qubits) % gate_qubit_count != 0:
            raise_qasm3_error(
                f"Invalid number of qubits {len(op_qubits)} for operation {operation.name.name}",
                error_node=operation,
                span=operation.span,
            )
        qubit_subsets = []
        for i in range(0, len(op_qubits), gate_qubit_count):
            # we apply the gate on the qubit subset linearly
            qubit_subsets.append(op_qubits[i : i + gate_qubit_count])
        return qubit_subsets

    def _broadcast_gate_operation(
        self,
        gate_function: Callable,
        all_targets: list[list[qasm3_ast.IndexedIdentifier]],
        ctrls: Optional[list[qasm3_ast.IndexedIdentifier]] = None,
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
        if ctrls is None:
            ctrls = []
        for targets in all_targets:
            result.extend(gate_function(*ctrls, *targets))
        return result

    def _update_qubit_depth_for_gate(
        self,
        all_targets: list[list[qasm3_ast.IndexedIdentifier]],
        ctrls: list[qasm3_ast.IndexedIdentifier],
    ):
        """Updates the depth of the circuit after applying a broadcasted gate.

        Args:
            all_targes: The list of qubits on which a gate was just added.

        Returns:
            None
        """
        if not self._recording_ext_gate_depth:
            for qubit_subset in all_targets:
                max_involved_depth = 0
                for qubit in qubit_subset + ctrls:
                    assert isinstance(qubit.indices[0], list)
                    _qid_ = qubit.indices[0][0]
                    qubit_id = Qasm3ExprEvaluator.evaluate_expression(_qid_)[0]  # type: ignore
                    qubit_node = self._module._qubit_depths[(qubit.name.name, qubit_id)]
                    qubit_node.num_gates += 1
                    max_involved_depth = max(max_involved_depth, qubit_node.depth + 1)

                for qubit in qubit_subset + ctrls:
                    assert isinstance(qubit.indices[0], list)
                    _qid_ = qubit.indices[0][0]
                    qubit_id = Qasm3ExprEvaluator.evaluate_expression(_qid_)[0]  # type: ignore
                    qubit_node = self._module._qubit_depths[(qubit.name.name, qubit_id)]
                    qubit_node.depth = max_involved_depth

    # pylint: disable=too-many-branches, too-many-locals
    def _visit_basic_gate_operation(
        self,
        operation: qasm3_ast.QuantumGate,
        inverse: bool = False,
        ctrls: Optional[list[qasm3_ast.IndexedIdentifier]] = None,
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
        if ctrls is None:
            ctrls = []

        if not inverse:
            if len(ctrls) > 0:
                qasm_func, op_qubit_total_count = map_qasm_ctrl_op_to_callable(
                    operation.name.name, len(ctrls)
                )
                op_qubit_count = op_qubit_total_count - len(ctrls)
            else:
                qasm_func, op_qubit_count = map_qasm_op_to_callable(operation)
        else:
            # in basic gates, inverse action only affects the rotation gates
            qasm_func, op_qubit_count, inverse_action = map_qasm_inv_op_to_callable(
                operation.name.name
            )
        op_parameters = []
        actual_num_params = map_qasm_op_num_params(operation.name.name)

        if len(operation.arguments) > 0:  # parametric gate
            op_parameters = self._get_op_parameters(operation)
            if inverse_action == InversionOp.INVERT_ROTATION:
                op_parameters = [-1 * param for param in op_parameters]

        if len(op_parameters) != actual_num_params:
            raise_qasm3_error(
                f"Expected {actual_num_params} parameter{'s' if actual_num_params != 1 else ''}"
                f" for gate '{operation.name.name}', but got {len(op_parameters)}",
                error_node=operation,
                span=operation.span,
            )

        result = []
        unrolled_targets = self._unroll_multiple_target_qubits(operation, op_qubit_count)
        unrolled_gate_function = partial(qasm_func, *op_parameters)

        if inverse:
            # for convenience, we recur and handle the ctrl @'s to the unrolled no inverse case
            # instead of trying to map the inverted callable to a ctrl'd version
            result.extend(
                [
                    g2
                    for g in self._broadcast_gate_operation(
                        unrolled_gate_function, unrolled_targets, None
                    )
                    for g2 in self._visit_basic_gate_operation(g, False, ctrls)
                ]
            )
        else:
            result.extend(
                self._broadcast_gate_operation(unrolled_gate_function, unrolled_targets, ctrls)
            )
            if self._module._decompose_native_gates and len(result) > 1:
                for gate in result:
                    if isinstance(gate, qasm3_ast.QuantumGate):
                        self._visit_basic_gate_operation(gate)
            else:
                # if gate is not in branching statement
                if not self._in_branching_statement:
                    self._update_qubit_depth_for_gate(unrolled_targets, ctrls)
                else:
                    # get qreg in branching operations
                    for qubit_subset in unrolled_targets + [ctrls]:
                        for qubit in qubit_subset:
                            assert isinstance(qubit.indices, list) and len(qubit.indices) > 0
                            assert isinstance(qubit.indices[0], list) and len(qubit.indices[0]) > 0
                            qubit_idx = Qasm3ExprEvaluator.evaluate_expression(qubit.indices[0][0])[
                                0
                            ]
                            self._is_branch_qubits.add((qubit.name.name, qubit_idx))

        # check for duplicate bits
        for final_gate in result:
            Qasm3Analyzer.verify_gate_qubits(final_gate, operation.span)

        if self._check_only:
            return []

        return result

    def _visit_break(self, statement: qasm3_ast.BreakStatement) -> None:
        raise_qasm3_error(
            err_type=BreakSignal,
            error_node=statement,
        )

    def _visit_continue(self, statement: qasm3_ast.ContinueStatement) -> None:
        raise_qasm3_error(
            err_type=ContinueSignal,
            error_node=statement,
        )

    def _visit_custom_gate_operation(
        self,
        operation: qasm3_ast.QuantumGate,
        inverse: bool = False,
        ctrls: Optional[list[qasm3_ast.IndexedIdentifier]] = None,
    ) -> list[qasm3_ast.QuantumGate | qasm3_ast.QuantumPhase]:
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
        if ctrls is None:
            ctrls = []
        gate_name: str = operation.name.name
        gate_definition: qasm3_ast.QuantumGateDefinition = self._custom_gates[gate_name]
        op_qubits: list[qasm3_ast.IndexedIdentifier] = self._get_op_bits(
            operation, qubits=True
        )  # type: ignore [assignment]

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

        self._scope_manager.push_scope({})
        self._scope_manager.push_context(Context.GATE)

        # Pause recording the depth of new gates because we are processing the
        # definition of a custom gate here - handle the depth separately afterwards
        self._recording_ext_gate_depth = gate_name in self._external_gates

        result = []
        for gate_op in gate_definition_ops:
            if isinstance(gate_op, (qasm3_ast.QuantumGate, qasm3_ast.QuantumPhase)):
                gate_op_copy = copy.deepcopy(gate_op)
                # necessary to avoid modifying the original gate definition
                # in case the gate is reapplied
                if isinstance(gate_op, qasm3_ast.QuantumGate) and gate_op.name.name == gate_name:
                    raise_qasm3_error(
                        f"Recursive definitions not allowed for gate '{gate_name}'",
                        error_node=gate_op,
                        span=gate_op.span,
                    )
                Qasm3Transformer.transform_gate_params(gate_op_copy, param_map)
                Qasm3Transformer.transform_gate_qubits(gate_op_copy, qubit_map)
                # need to trickle the inverse down to the child gates
                if inverse:
                    # span doesn't matter as we don't analyze it
                    gate_op_copy.modifiers.append(
                        qasm3_ast.QuantumGateModifier(qasm3_ast.GateModifierName.inv, None)
                    )
                result.extend(self._visit_generic_gate_operation(gate_op_copy, ctrls))
            else:
                # TODO: add control flow support
                raise_qasm3_error(
                    f"Unsupported statement in gate definition '{type(gate_op).__name__}'",
                    error_node=gate_op,
                    span=gate_op.span,
                )

        # Update the depth only once for the entire custom gate
        if self._recording_ext_gate_depth:
            self._recording_ext_gate_depth = False
            if not self._in_branching_statement:  # if custom gate is not in branching statement
                self._update_qubit_depth_for_gate([op_qubits], ctrls)
            else:
                # get qubit registers in branching operations
                for qubit_subset in [op_qubits] + [ctrls]:
                    for qubit in qubit_subset:
                        assert isinstance(qubit.indices, list) and len(qubit.indices) > 0
                        assert isinstance(qubit.indices[0], list) and len(qubit.indices[0]) > 0
                        qubit_idx = Qasm3ExprEvaluator.evaluate_expression(qubit.indices[0][0])[0]
                        self._is_branch_qubits.add((qubit.name.name, qubit_idx))

        self._scope_manager.pop_scope()
        self._scope_manager.restore_context()

        if self._check_only:
            return []

        return result

    def _visit_external_gate_operation(
        self,
        operation: qasm3_ast.QuantumGate,
        inverse: bool = False,
        ctrls: Optional[list[qasm3_ast.IndexedIdentifier]] = None,
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
        if ctrls is None:
            ctrls = []

        if gate_name in self._custom_gates:
            # Ignore result, this is just for validation
            self._visit_custom_gate_operation(operation, inverse, ctrls)
            # Don't need to check if custom gate exists, since we just validated the call
            gate_qubit_count = len(self._custom_gates[gate_name].qubits)
        else:
            # Ignore result, this is just for validation
            self._visit_basic_gate_operation(operation)
            # Don't need to check if basic gate exists, since we just validated the call
            _, gate_qubit_count = map_qasm_op_to_callable(operation)

        op_parameters = [
            qasm3_ast.FloatLiteral(param) for param in self._get_op_parameters(operation)
        ]

        self._scope_manager.push_context(Context.GATE)

        # TODO: add ctrl @ support + testing
        modifiers = []
        if inverse:
            modifiers.append(qasm3_ast.QuantumGateModifier(qasm3_ast.GateModifierName.inv, None))
        if len(ctrls) > 0:
            modifiers.append(
                qasm3_ast.QuantumGateModifier(
                    qasm3_ast.GateModifierName.ctrl, qasm3_ast.IntegerLiteral(len(ctrls))
                )
            )

        def gate_function(*qubits):
            return [
                qasm3_ast.QuantumGate(
                    modifiers=modifiers,
                    name=qasm3_ast.Identifier(gate_name),
                    qubits=ctrls + list(qubits),
                    arguments=list(op_parameters),
                )
            ]

        all_targets = self._unroll_multiple_target_qubits(operation, gate_qubit_count)
        result = self._broadcast_gate_operation(gate_function, all_targets)

        # check for any duplicates
        for final_gate in result:
            Qasm3Analyzer.verify_gate_qubits(final_gate, operation.span)

        self._scope_manager.restore_context()
        if self._check_only:
            return []

        return result

    def _visit_phase_operation(
        self,
        operation: qasm3_ast.QuantumPhase,
        inverse: bool = False,
        ctrls: Optional[list[qasm3_ast.IndexedIdentifier]] = None,
    ) -> list[qasm3_ast.QuantumPhase]:
        """Visit a phase operation element.

        Args:
            operation (qasm3_ast.QuantumPhase): The phase operation to visit.
            inverse (bool): Whether the operation is an inverse operation. Defaults to False.

        Returns:
            list[qasm3_ast.Statement]: The unrolled quantum phase operation.
        """
        logger.debug("Visiting phase operation '%s'", str(operation))
        if ctrls is None:
            ctrls = []

        if len(ctrls) > 0:
            return self._visit_basic_gate_operation(
                qasm3_ast.QuantumGate(
                    modifiers=[
                        qasm3_ast.QuantumGateModifier(
                            qasm3_ast.GateModifierName.ctrl,
                            qasm3_ast.IntegerLiteral(len(ctrls) - 1),
                        )
                    ],
                    name=qasm3_ast.Identifier("p"),
                    qubits=ctrls[0:1],  # type: ignore
                    arguments=[operation.argument],
                ),  # type: ignore
                inverse,
                ctrls[:-1],
            )

        evaluated_arg = Qasm3ExprEvaluator.evaluate_expression(operation.argument)[0]
        if inverse:
            evaluated_arg = -1 * evaluated_arg
        # remove the modifiers, as we have already applied the inverse
        operation.modifiers = []

        operation.argument = qasm3_ast.FloatLiteral(value=evaluated_arg)
        # no qubit evaluation to be done here
        # if args are provided in global scope, then we should raise error
        if self._scope_manager.in_global_scope() and len(operation.qubits) != 0:
            raise_qasm3_error(
                "Qubit arguments not allowed for 'gphase' operation in global scope",
                error_node=operation,
                span=operation.span,
            )

        # if it were in function scope, then the args would have been evaluated and added to the
        # qubit list
        if self._check_only:
            return []

        return [operation]

    def _visit_generic_gate_operation(  # pylint: disable=too-many-branches, too-many-statements
        self,
        operation: qasm3_ast.QuantumGate | qasm3_ast.QuantumPhase,
        ctrls: Optional[list[qasm3_ast.IndexedIdentifier]] = None,
    ) -> list[qasm3_ast.QuantumGate | qasm3_ast.QuantumPhase]:
        """Visit a gate operation element.

        Args:
            operation (qasm3_ast.QuantumGate): The gate operation to visit.

        Returns:
            None
        """
        operation, ctrls = copy.copy(operation), copy.copy(ctrls)
        negctrls = []
        if ctrls is None:
            ctrls = []
        # This is a special register name, e.g., $0, $1, etc.
        # In OpenQASM 3, these are often used for implicit qubit registers.
        if isinstance(operation, qasm3_ast.QuantumGate) and (
            operation.name.name in self._openpulse_qubit_map
        ):
            gate_op = operation.name.name
            gate_def = self._subroutine_defns[gate_op]
            operation = PulseValidator.validate_openpulse_gate_parameters(
                operation,
                gate_op,
                gate_def,
                self._pulse_visitor,
                self._scope_manager,
                self._module,
            )
            stmts = PulseUtils.process_qubits_for_openpulse_gate(
                operation, gate_op, self._openpulse_qubit_map, self._global_qreg_size_map
            )
            return stmts  # type: ignore

        self._in_generic_gate_op_scope += 1

        # only needs to be done once for a gate operation
        if (
            len(operation.qubits) > 0
            and not self._scope_manager.in_gate_scope()
            and len(self._function_qreg_size_map) > 0
        ):
            # we are in SOME function scope
            # transform qubits to use the global qreg identifiers
            for transform_map, size_map in zip(
                reversed(self._function_qreg_transform_map), reversed(self._function_qreg_size_map)
            ):
                operation.qubits = (
                    Qasm3Transformer.transform_function_qubits(  # type: ignore [assignment]
                        operation, transform_map, size_map
                    )
                )

        operation.qubits = self._get_op_bits(operation, qubits=True)  # type: ignore

        # ctrl / pow / inv modifiers commute. so group them.
        exponent = 1
        ctrl_arg_ind = 0
        for modifier in operation.modifiers:
            modifier_name = modifier.modifier
            if modifier_name == qasm3_ast.GateModifierName.pow and modifier.argument is not None:
                try:
                    current_power = Qasm3ExprEvaluator.evaluate_expression(
                        modifier.argument, reqd_type=qasm3_ast.IntType
                    )[0]
                except ValidationError:
                    raise_qasm3_error(
                        f"Power modifier argument must be an integer in gate operation {operation}",
                        error_node=operation,
                        span=operation.span,
                    )
                exponent *= current_power
            elif modifier_name == qasm3_ast.GateModifierName.inv:
                exponent *= -1
            elif modifier_name in [
                qasm3_ast.GateModifierName.ctrl,
                qasm3_ast.GateModifierName.negctrl,
            ]:
                try:
                    count = Qasm3ExprEvaluator.evaluate_expression(
                        modifier.argument, const_expr=True
                    )[0]
                except ValidationError:
                    raise_qasm3_error(
                        "Controlled modifier arguments must be compile-time constants "
                        f"in gate operation {operation}",
                        error_node=operation,
                        span=operation.span,
                    )
                if count is None:
                    count = 1
                if not isinstance(count, int) or count <= 0:
                    raise_qasm3_error(
                        "Controlled modifier argument must be a positive integer "
                        f"in gate operation {operation}",
                        error_node=operation,
                        span=operation.span,
                    )
                ctrl_qubits = operation.qubits[ctrl_arg_ind : ctrl_arg_ind + count]

                # TODO: assert ctrl_qubits are single qubits
                ctrl_arg_ind += count
                ctrls.extend(ctrl_qubits)  # type: ignore
                if modifier_name == qasm3_ast.GateModifierName.negctrl:
                    negctrls.extend(ctrl_qubits)

        power_value, inverse_value = abs(exponent), exponent < 0

        operation.qubits = operation.qubits[ctrl_arg_ind:]
        operation.modifiers = []

        # apply pow(int) via duplication
        if not isinstance(power_value, int):
            raise_qasm3_error(
                "Power modifiers with non-integer arguments are unsupported in gate "
                f"operation {operation}",
                error_node=operation,
                span=operation.span,
            )

        # get controlled? inverted? operation x power times
        result: list[qasm3_ast.QuantumGate | qasm3_ast.QuantumPhase] = []
        for _ in range(power_value):
            if isinstance(operation, qasm3_ast.QuantumPhase):
                result.extend(self._visit_phase_operation(operation, inverse_value, ctrls))
            elif operation.name.name in self._external_gates:
                result.extend(self._visit_external_gate_operation(operation, inverse_value, ctrls))
            elif operation.name.name in self._custom_gates:
                result.extend(self._visit_custom_gate_operation(operation, inverse_value, ctrls))
            else:
                result.extend(self._visit_basic_gate_operation(operation, inverse_value, ctrls))

        # negctrl -> ctrl conversion
        negs = [
            qasm3_ast.QuantumGate([], qasm3_ast.Identifier("x"), [], [ctrl]) for ctrl in negctrls
        ]
        result = negs + result + negs  # type: ignore
        self._in_generic_gate_op_scope -= 1
        if self._consolidate_qubits and not self._in_generic_gate_op_scope:
            result = cast(
                list[qasm3_ast.QuantumGate | qasm3_ast.QuantumPhase],
                Qasm3Transformer.consolidate_qubit_registers(
                    result,
                    self._qubit_register_offsets,
                    self._global_qreg_size_map,
                    self._module._device_qubits,
                ),
            )

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
                f"Can not declare variable with keyword name {var_name}",
                error_node=statement,
                span=statement.span,
            )
        if self._scope_manager.check_in_scope(var_name) or (
            self._scope_manager.in_pulse_scope()
            and self._scope_manager.check_in_global_scope(var_name)
        ):
            raise_qasm3_error(
                f"Re-declaration of variable '{var_name}'",
                error_node=statement,
                span=statement.span,
            )

        if statement.init_expression:
            global_scope = self._scope_manager.get_global_scope()
            PulseValidator.validate_duration_or_stretch_statements(
                statement=statement,
                base_type=statement.type,
                rvalue=statement.init_expression,
                global_scope=global_scope,
            )

        try:
            init_value, stmts = Qasm3ExprEvaluator.evaluate_expression(
                statement.init_expression,
                const_expr=True,
                dt=self._module._device_cycle_time,
            )
        except ValidationError as err:
            raise_qasm3_error(
                f"Invalid initialization value for constant '{var_name}'",
                error_node=statement,
                span=statement.span,
                raised_from=err,
            )

        statements.extend(stmts)

        base_type = statement.type
        base_size = self._check_variable_type_size(statement, var_name, "constant", base_type)
        angle_val_bit_string = None
        if (
            isinstance(base_type, qasm3_ast.AngleType)
            and not self._in_extern_function
            and init_value is not None
        ):
            init_value, angle_val_bit_string = PulseValidator.validate_angle_type_value(
                statement,
                init_value=init_value,
                base_size=base_size,
                compiler_angle_width=self._module._compiler_angle_type_size,
            )
        val_type, _ = Qasm3ExprEvaluator.evaluate_expression(
            statement.init_expression,
            validate_only=True,
        )
        self._check_variable_cast_type(statement, val_type, var_name, base_type, base_size, True)
        variable = Variable(
            var_name,
            base_type,
            len(angle_val_bit_string) if angle_val_bit_string else base_size,
            [],
            init_value,
            is_constant=True,
            span=statement.span,
            angle_bit_string=angle_val_bit_string,
        )

        if isinstance(base_type, qasm3_ast.BitType) and isinstance(init_value, str):
            self._validate_bitstring_literal_width(init_value, base_size, var_name, statement)

        if isinstance(base_type, (qasm3_ast.DurationType, qasm3_ast.StretchType)):
            PulseValidator.validate_duration_literal_value(init_value, statement, base_type)
            if self._module._device_cycle_time:
                variable.time_unit = "dt"
            else:
                variable.time_unit = "ns"

        # cast + validation
        if init_value is not None and not self._in_extern_function:
            variable.value = Qasm3Validator.validate_variable_assignment_value(
                variable, init_value, op_node=statement
            )

        self._scope_manager.add_var_in_scope(variable)

        if isinstance(base_type, qasm3_ast.ComplexType) and isinstance(variable.value, complex):
            statement.init_expression = PulseValidator.make_complex_binary_expression(init_value)

        if isinstance(statement.init_expression, qasm3_ast.FunctionCall):
            statement.init_expression = (
                self._handle_function_init_expression(statement.init_expression, init_value)
                or statement.init_expression
            )
        self._handle_extern_function_cleanup(statements, statement)

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
                f"Can not declare variable with keyword name {var_name}",
                error_node=statement,
                span=statement.span,
            )
        if self._scope_manager.check_in_scope(var_name):
            if (
                self._scope_manager.in_block_scope(),
                self._scope_manager.in_box_scope(),
            ) and (
                var_name not in self._scope_manager.get_curr_scope()
                and not self._scope_manager.in_pulse_scope()
            ):
                # we can re-declare variables once in block scope even if they are
                # present in the parent scope
                # Eg. int a = 10;
                #     { int a = 20;} // is valid
                pass
            else:
                raise_qasm3_error(
                    f"Re-declaration of variable '{var_name}'",
                    error_node=statement,
                    span=statement.span,
                )

        init_value = None
        base_type = statement.type
        dimensions = []
        final_dimensions = []
        angle_val_bit_string = None

        if isinstance(base_type, qasm3_ast.StretchType):
            if statement.init_expression:
                raise_qasm3_error(
                    f"Assignment to 'stretch' type variable '{var_name}' is not allowed,"
                    " must be initialized with a constant at declaration.",
                    error_node=statement,
                    span=statement.span,
                )
            else:
                statements.append(cast(qasm3_ast.Statement, statement))

        if isinstance(base_type, qasm3_ast.ArrayType):
            dimensions = base_type.dimensions
            base_type = base_type.base_type

        base_size = self._check_variable_type_size(statement, var_name, "variable", base_type)
        Qasm3Validator.validate_classical_type(base_type, base_size, var_name, statement)

        # initialize the bit register
        if isinstance(base_type, qasm3_ast.BitType):
            final_dimensions = [base_size]
            init_value = np.full(final_dimensions, 0)

        if len(dimensions) > 0:
            # bit type arrays are not allowed
            if isinstance(base_type, qasm3_ast.BitType):
                raise_qasm3_error(
                    f"Can not declare array {var_name} with type 'bit'",
                    error_node=statement,
                    span=statement.span,
                )
            if len(dimensions) > MAX_ARRAY_DIMENSIONS:
                raise_qasm3_error(
                    f"Invalid dimensions {len(dimensions)} for array declaration for '{var_name}'. "
                    f"Max allowed dimensions is {MAX_ARRAY_DIMENSIONS}",
                    error_node=statement,
                    span=statement.span,
                )

            for dim in dimensions:
                dim_value = Qasm3ExprEvaluator.evaluate_expression(dim, const_expr=True)[0]
                if not isinstance(dim_value, int) or dim_value <= 0:
                    raise_qasm3_error(
                        f"Invalid dimension size {dim_value} in array declaration for '{var_name}'",
                        error_node=statement,
                        span=statement.span,
                    )
                final_dimensions.append(dim_value)

            init_value = np.full(final_dimensions, None)

        # populate the variable
        if statement.init_expression:

            global_scope = self._scope_manager.get_global_scope()
            PulseValidator.validate_duration_or_stretch_statements(
                statement=statement,
                base_type=base_type,
                rvalue=statement.init_expression,
                global_scope=global_scope,
            )

            if isinstance(statement.init_expression, qasm3_ast.ArrayLiteral):
                init_value = self._evaluate_array_initialization(
                    statement.init_expression, final_dimensions, base_type
                )
            elif isinstance(statement.init_expression, qasm3_ast.QuantumMeasurement):
                measurement, statement.init_expression = statement.init_expression, None
                return self._visit_classical_declaration(statement) + self._visit_measurement(
                    qasm3_ast.QuantumMeasurementStatement(measurement, statement.identifier)
                )  # type: ignore
            else:
                try:
                    init_value, stmts = Qasm3ExprEvaluator.evaluate_expression(
                        statement.init_expression,
                        dt=self._module._device_cycle_time,
                    )
                    statements.extend(stmts)
                    _req_type = (
                        type(qasm3_ast.AngleType())
                        if isinstance(base_type, qasm3_ast.AngleType)
                        else None
                    )
                    val_type, _ = Qasm3ExprEvaluator.evaluate_expression(
                        statement.init_expression,
                        validate_only=True,
                        reqd_type=_req_type,
                    )
                    if (
                        isinstance(base_type, qasm3_ast.AngleType)
                        and not self._in_extern_function
                        and init_value is not None
                    ):
                        init_value, angle_val_bit_string = PulseValidator.validate_angle_type_value(
                            statement,
                            init_value=init_value,
                            base_size=base_size,
                            compiler_angle_width=self._module._compiler_angle_type_size,
                        )
                    self._check_variable_cast_type(
                        statement, val_type, var_name, base_type, base_size, False
                    )
                except ValidationError as err:
                    raise_qasm3_error(
                        f"Invalid initialization value for variable '{var_name}'",
                        error_node=statement,
                        span=statement.span,
                        raised_from=err,
                    )
        if isinstance(base_type, qasm3_ast.BitType) and isinstance(init_value, str):
            self._validate_bitstring_literal_width(init_value, base_size, var_name, statement)

        variable = Variable(
            var_name,
            base_type,
            len(angle_val_bit_string) if angle_val_bit_string else base_size,
            final_dimensions,
            init_value,
            is_qubit=False,
            span=statement.span,
            angle_bit_string=angle_val_bit_string,
        )

        if isinstance(base_type, qasm3_ast.DurationType):
            PulseValidator.validate_duration_literal_value(init_value, statement, base_type)
            if self._module._device_cycle_time:
                variable.time_unit = "dt"
            else:
                variable.time_unit = "ns"

        # validate the assignment
        if statement.init_expression:
            if isinstance(init_value, np.ndarray):
                assert variable.dims is not None
                try:
                    Qasm3Validator.validate_array_assignment_values(
                        variable, variable.dims, init_value
                    )
                except ValidationError as err:
                    raise_qasm3_error(
                        f"Invalid initialization value for array '{var_name}'",
                        error_node=statement,
                        span=statement.span,
                        raised_from=err,
                    )
            else:
                try:
                    if init_value is not None and not self._in_extern_function:
                        variable.value = Qasm3Validator.validate_variable_assignment_value(
                            variable, init_value, op_node=statement
                        )
                except ValidationError as err:
                    raise_qasm3_error(
                        f"Invalid initialization value for variable '{var_name}'",
                        error_node=statement,
                        span=statement.span,
                        raised_from=err,
                    )
        self._scope_manager.add_var_in_scope(variable)

        # special handling for bit[...]
        if isinstance(base_type, qasm3_ast.BitType):
            self._global_creg_size_map[var_name] = base_size
            current_classical_size = len(self._clbit_labels)
            for i in range(base_size):
                self._clbit_labels[f"{var_name}_{i}"] = current_classical_size + i
                self._module._clbit_depths[(var_name, i)] = ClbitDepthNode(var_name, i)

            if hasattr(statement.type, "size"):
                statement.type.size = (
                    qasm3_ast.IntegerLiteral(1)
                    if statement.type.size is None
                    else qasm3_ast.IntegerLiteral(base_size)
                )
            statements.append(statement)
            self._module._add_classical_register(var_name, base_size)

        self._handle_extern_function_cleanup(statements, statement)

        if isinstance(base_type, qasm3_ast.ComplexType) and isinstance(variable.value, complex):
            statement.init_expression = PulseValidator.make_complex_binary_expression(init_value)

        if isinstance(statement.init_expression, qasm3_ast.FunctionCall):
            statement.init_expression = (
                self._handle_function_init_expression(statement.init_expression, init_value)
                or statement.init_expression
            )

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

        lvar = self._scope_manager.get_from_visible_scope(lvar_name)
        if lvar is None and self._scope_manager.in_pulse_scope():
            lvar = self._pulse_visitor._get_identifier(statement, lvar_name)
        if lvar is None:  # we check for none here, so type errors are irrelevant afterwards
            raise_qasm3_error(
                f"Undefined variable {lvar_name} in assignment",
                error_node=statement,
                span=statement.span,
            )
        if isinstance(lvar, (Waveform, Frame, Capture)):
            return []
        if lvar.is_constant:  # type: ignore[union-attr]
            raise_qasm3_error(
                f"Assignment to constant variable {lvar_name} not allowed",
                error_node=statement,
                span=statement.span,
            )
        if lvar and isinstance(lvar.base_type, qasm3_ast.StretchType):
            raise_qasm3_error(
                f"Assignment to 'stretch' type variable '{lvar_name}' is not allowed,"
                " must be initialized with a constant at declaration.",
                error_node=statement,
                span=statement.span,
            )
        binary_op: str | None | qasm3_ast.BinaryOperator = None
        if statement.op != qasm3_ast.AssignmentOperator["="]:
            # eg. j += 1 -> broken down to j = j + 1
            binary_op = statement.op.name.removesuffix("=")
            binary_op = qasm3_ast.BinaryOperator[binary_op]

        # rvalue will be an evaluated value (scalar, list)
        # if rvalue is a list, we want a copy of it
        rvalue = statement.rvalue
        lvar_base_type = lvar.base_type  # type: ignore[union-attr]
        if rvalue:
            global_scope = self._scope_manager.get_global_scope()
            PulseValidator.validate_duration_or_stretch_statements(
                statement=statement,
                base_type=lvar_base_type,
                rvalue=rvalue,
                global_scope=global_scope,
            )
        if binary_op is not None:
            rvalue = qasm3_ast.BinaryExpression(
                lhs=lvalue, op=binary_op, rhs=rvalue  # type: ignore[arg-type]
            )
        rvalue_raw, rhs_stmts = Qasm3ExprEvaluator.evaluate_expression(
            rvalue,
            dt=self._module._device_cycle_time,
        )  # consists of scope check and index validation
        statements.extend(rhs_stmts)
        val_type, _ = Qasm3ExprEvaluator.evaluate_expression(
            rvalue,
            validate_only=True,
        )
        self._check_variable_cast_type(
            statement,
            val_type,
            lvar_name,
            lvar.base_type,  # type: ignore[union-attr]
            lvar.base_size,  # type: ignore[union-attr]
            False,
        )
        if isinstance(lvar_base_type, qasm3_ast.BitType) and isinstance(rvalue_raw, str):
            self._validate_bitstring_literal_width(
                rvalue_raw, lvar.base_size, lvar_name, statement  # type: ignore[union-attr]
            )
        angle_val_bit_string = None
        if (
            isinstance(lvar_base_type, qasm3_ast.AngleType)
            and not self._in_extern_function
            and rvalue_raw is not None
        ):
            rvalue_raw, angle_val_bit_string = PulseValidator.validate_angle_type_value(
                statement,
                init_value=rvalue_raw,
                base_size=lvar.base_size,  # type: ignore[union-attr]
                compiler_angle_width=self._module._compiler_angle_type_size,
            )
            lvar.angle_bit_string = angle_val_bit_string  # type: ignore[union-attr]
            if angle_val_bit_string:
                lvar.base_size = len(angle_val_bit_string)  # type: ignore[union-attr]
        # cast + validation
        rvalue_eval = None
        if not isinstance(rvalue_raw, np.ndarray):
            # rhs is a scalar
            if rvalue_raw is not None and not self._in_extern_function:
                rvalue_eval = Qasm3Validator.validate_variable_assignment_value(
                    lvar, rvalue_raw, op_node=statement  # type: ignore[arg-type]
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

        if isinstance(lvar_base_type, qasm3_ast.DurationType):
            PulseValidator.validate_duration_literal_value(rvalue_eval, statement, lvar_base_type)

        if lvar.readonly:  # type: ignore[union-attr]
            raise_qasm3_error(
                f"Assignment to readonly variable '{lvar_name}' not allowed in function call",
                error_node=statement,
                span=statement.span,
            )

        # lvalue will be the variable which will HOLD this value
        if isinstance(lvalue, qasm3_ast.IndexedIdentifier):
            # stupid indices structure in openqasm :/
            if len(lvalue.indices[0]) > 1:  # type: ignore[arg-type]
                l_indices = lvalue.indices[0]
            else:
                l_indices = [idx[0] for idx in lvalue.indices]  # type: ignore[assignment, index]
            try:
                validated_l_indices = Qasm3Analyzer.analyze_classical_indices(
                    l_indices, lvar, Qasm3ExprEvaluator  # type: ignore[arg-type]
                )
            except ValidationError as err:
                raise_qasm3_error(
                    f"Invalid index for variable '{lvar_name}'",
                    error_node=statement,
                    span=statement.span,
                    raised_from=err,
                )
            Qasm3Transformer.update_array_element(
                multi_dim_arr=lvar.value,  # type: ignore[union-attr, arg-type]
                indices=validated_l_indices,
                value=rvalue_eval,
            )
        else:
            lvar.value = rvalue_eval  # type: ignore[union-attr]
        self._scope_manager.update_var_in_scope(lvar)  # type: ignore[arg-type]

        if isinstance(lvar_base_type, qasm3_ast.ComplexType) and isinstance(
            lvar.value, complex  # type: ignore[union-attr]
        ):
            statement.rvalue = PulseValidator.make_complex_binary_expression(
                lvar.value  # type: ignore[union-attr]
            )

        if isinstance(statement.rvalue, qasm3_ast.FunctionCall):
            statement.rvalue = (
                self._handle_function_init_expression(statement.rvalue, rvalue_eval)
                or statement.rvalue
            )

        self._handle_extern_function_cleanup(statements, statement)

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

    # update branching operators depth
    def _update_branching_gate_depths(self) -> None:
        """Updates the depth of the circuit after applying branching statements."""
        all_nodes = [
            self._module._qubit_depths[(name, idx)] for name, idx in self._is_branch_qubits
        ] + [self._module._clbit_depths[(name, idx)] for name, idx in self._is_branch_clbits]

        try:
            max_depth = max(node.depth + 1 for node in all_nodes)
        except ValueError:
            max_depth = 0

        for node in all_nodes:
            node.depth = max_depth

        self._is_branch_clbits.clear()
        self._is_branch_qubits.clear()

    def _visit_branching_statement(
        self, statement: qasm3_ast.BranchingStatement
    ) -> list[qasm3_ast.Statement]:
        """Visit a branching statement element.

        Args:
            statement (qasm3_ast.BranchingStatement): The branching statement to visit.

        Returns:
            None
        """
        self._scope_manager.push_context(Context.BLOCK)
        self._scope_manager.push_scope({})
        self._scope_manager.increment_scope_level()
        self._in_branching_statement += 1

        result = []
        condition = statement.condition

        if not statement.if_block:
            raise_qasm3_error("Missing if block", error_node=statement, span=statement.span)

        if Qasm3ExprEvaluator.classical_register_in_expr(condition):
            # leave this condition as is, and start unrolling the block

            # here, the lhs CAN only be a classical register as QCs won't have
            # ability to evaluate expressions in the condition

            reg_idx, reg_name, op, rhs_value = Qasm3Transformer.get_branch_params(condition)

            if reg_name not in self._global_creg_size_map:
                raise_qasm3_error(
                    f"Missing register declaration for '{reg_name}' in branching statement",
                    error_node=condition,
                    span=statement.span,
                )

            assert isinstance(rhs_value, (bool, int))

            if_block = self.visit_basic_block(statement.if_block)
            else_block = self.visit_basic_block(statement.else_block)

            if reg_idx is not None:
                # single bit branch
                Qasm3Validator.validate_register_index(
                    reg_idx, self._global_creg_size_map[reg_name], qubit=False, op_node=condition
                )

                # getting creg for depth counting
                self._is_branch_clbits.add((reg_name, reg_idx))

                new_if_block = qasm3_ast.BranchingStatement(
                    condition=qasm3_ast.BinaryExpression(
                        op=qasm3_ast.BinaryOperator["=="],
                        lhs=qasm3_ast.IndexExpression(
                            collection=qasm3_ast.Identifier(name=reg_name),
                            index=[qasm3_ast.IntegerLiteral(reg_idx)],
                        ),
                        rhs=(
                            qasm3_ast.BooleanLiteral(rhs_value)
                            if isinstance(rhs_value, bool)
                            else qasm3_ast.IntegerLiteral(rhs_value)
                        ),
                    ),
                    if_block=if_block,
                    else_block=else_block,
                )
                result.append(new_if_block)
            else:
                # unroll multi-bit branch
                assert isinstance(rhs_value, int) and op in [
                    qasm3_ast.BinaryOperator[o] for o in ["==", ">=", "<=", ">", "<"]
                ]

                if op == qasm3_ast.BinaryOperator[">"]:
                    op = qasm3_ast.BinaryOperator[">="]
                    rhs_value += 1
                elif op == qasm3_ast.BinaryOperator["<"]:
                    op = qasm3_ast.BinaryOperator["<="]
                    rhs_value -= 1

                size = self._global_creg_size_map[reg_name]
                # getting cregs for depth counting
                self._is_branch_clbits.update((reg_name, i) for i in range(size))
                rhs_value_str = bin(int(rhs_value))[2:].zfill(size)
                else_block = self.visit_basic_block(statement.else_block)

                def ravel(bit_ind):
                    """Unravel if statement from MSB to LSB"""
                    r = rhs_value_str[bit_ind] == "1"
                    if (op == qasm3_ast.BinaryOperator[">="] and not r) or (
                        op == qasm3_ast.BinaryOperator["<="] and r
                    ):
                        # skip if bit condition is irrelevant.
                        # ex. if op is >= and r = 0, both values reg[i]={0,1} satisfy the condition
                        return if_block if bit_ind == len(rhs_value_str) - 1 else ravel(bit_ind + 1)

                    return [
                        qasm3_ast.BranchingStatement(
                            condition=qasm3_ast.BinaryExpression(
                                op=qasm3_ast.BinaryOperator["=="],
                                lhs=qasm3_ast.IndexExpression(
                                    collection=qasm3_ast.Identifier(name=reg_name),
                                    index=[qasm3_ast.IntegerLiteral(bit_ind)],
                                ),
                                rhs=qasm3_ast.BooleanLiteral(r),
                            ),
                            if_block=(
                                if_block
                                if bit_ind == len(rhs_value_str) - 1
                                else ravel(bit_ind + 1)
                            ),
                            else_block=else_block,
                        )
                    ]

                result.extend(self.visit_basic_block(ravel(0)))  # type: ignore[arg-type]
        else:
            # here we can unroll the block depending on the condition
            positive_branching = Qasm3ExprEvaluator.evaluate_expression(condition)[0] != 0
            block_to_visit = statement.if_block if positive_branching else statement.else_block

            result.extend(self.visit_basic_block(block_to_visit))  # type: ignore[arg-type]

        self._scope_manager.decrement_scope_level()
        self._scope_manager.pop_scope()
        self._scope_manager.restore_context()
        self._in_branching_statement -= 1
        if not self._in_branching_statement:
            self._update_branching_gate_depths()

        if self._check_only:
            return []

        return result  # type: ignore[return-value]

    def _visit_forin_loop(self, statement: qasm3_ast.ForInLoop) -> list[qasm3_ast.Statement]:
        # Compute loop variable values
        irange = []
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
            irange = list(range(int(startval), int(endval) + int(stepval), int(stepval)))
        elif isinstance(statement.set_declaration, qasm3_ast.DiscreteSet):
            init_exp = statement.set_declaration.values[0]
            irange = [
                Qasm3ExprEvaluator.evaluate_expression(exp)[0]
                for exp in statement.set_declaration.values
            ]
        else:
            raise_qasm3_error(
                f"Unexpected type {type(statement.set_declaration)} of set_declaration in loop.",
                error_node=statement,
                span=statement.span,
            )

        # Check if the loop range exceeds the maximum allowed iterations
        if len(irange) > self._loop_limit:
            raise_qasm3_error(
                # pylint: disable-next=line-too-long
                f"Loop range '{len(irange)-1}' exceeded max allowed '{self._loop_limit}' iterations",
                err_type=LoopLimitExceededError,
                error_node=statement,
                span=statement.span,
            )

        i: Optional[Variable]  # will store iteration Variable to update to loop scope

        result = []
        statement_block = None
        for ival in irange:
            self._scope_manager.push_context(Context.BLOCK)
            self._scope_manager.push_scope({})

            # Initialize loop variable in loop scope
            # need to re-declare as we discard the block scope in subsequent
            # iterations of the loop
            result.extend(
                self._visit_classical_declaration(
                    qasm3_ast.ClassicalDeclaration(statement.type, statement.identifier, init_exp)
                )
            )
            i = self._scope_manager.get_from_visible_scope(statement.identifier.name)

            # Update scope with current value of loop Variable
            if i is not None:
                i.value = ival
                self._scope_manager.update_var_in_scope(i)

            if statement_block != statement.block:
                statement_block = copy.deepcopy(statement.block)
                result.extend(self.visit_basic_block(statement_block))
            else:
                result.extend(self.visit_basic_block(statement.block))

            # scope not persistent between loop iterations
            self._scope_manager.pop_scope()
            self._scope_manager.restore_context()

            # as we are only checking compile time errors
            # not runtime errors, we can break here
            if self._check_only:
                return []
        return result

    def _visit_subroutine_definition(
        self, statement: qasm3_ast.SubroutineDefinition | qasm3_ast.ExternDeclaration
    ) -> Sequence[None | qasm3_ast.ExternDeclaration]:
        """Visit a subroutine definition element.
           Reference: https://openqasm.com/language/subroutines.html#subroutines

        Args:
            statement (qasm3_ast.SubroutineDefinition): The subroutine definition to visit.

        Returns:
            None
        """
        fn_name = statement.name.name
        statements = []

        if fn_name in CONSTANTS_MAP:
            raise_qasm3_error(
                f"Subroutine name '{fn_name}' is a reserved keyword",
                error_node=statement,
                span=statement.span,
            )

        if fn_name in self._subroutine_defns:
            raise_qasm3_error(
                f"Redefinition of subroutine '{fn_name}'", error_node=statement, span=statement.span
            )

        if self._scope_manager.check_in_scope(fn_name):
            raise_qasm3_error(
                f"Can not declare subroutine with name '{fn_name}' as "
                "it is already declared as a variable",
                error_node=statement,
                span=statement.span,
            )

        if isinstance(statement, qasm3_ast.ExternDeclaration):
            if statement.name.name in self._module._extern_functions:
                PulseValidator.validate_extern_declaration(self._module, statement)
            self._module._extern_functions[statement.name.name] = (
                statement.arguments,
                statement.return_type,
            )

            statements.append(statement)

        self._subroutine_defns[fn_name] = statement
        if self._check_only:
            return []

        return statements

    # pylint: disable=too-many-locals, too-many-statements
    def _visit_function_call(
        self, statement: qasm3_ast.FunctionCall
    ) -> tuple[Any | None, list[qasm3_ast.Statement | qasm3_ast.FunctionCall]]:
        """Visit a function call element.

        Args:
            statement (qasm3_ast.FunctionCall): The function call to visit.
        Returns:
            None

        """
        fn_name = statement.name.name
        if fn_name not in self._subroutine_defns and fn_name not in FUNCTION_MAP:
            if (
                fn_name in OPENPULSE_WAVEFORM_FUNCTION_MAP
                or fn_name in OPENPULSE_FRAME_FUNCTION_MAP
                or fn_name in OPENPULSE_CAPTURE_FUNCTION_MAP
                or fn_name in ["get_phase", "get_frequency"]
            ):
                return None, []
            raise_qasm3_error(
                f"Undefined subroutine '{fn_name}' was called",
                error_node=statement,
                span=statement.span,
            )

        subroutine_def = self._subroutine_defns[fn_name]

        if len(statement.arguments) != len(subroutine_def.arguments):
            raise_qasm3_error(
                f"Parameter count mismatch for subroutine '{fn_name}'. Expected "
                f"{len(subroutine_def.arguments)} but got {len(statement.arguments)} in call",
                error_node=statement,
                span=statement.span,
            )

        duplicate_qubit_detect_map: dict = {}
        qubit_transform_map: dict = {}  # {(formal arg, idx) : (actual arg, idx)}
        formal_qreg_size_map: dict = {}
        actual_qreg_size_map: dict = (
            self._function_qreg_size_map[-1]
            if self._function_qreg_size_map
            else self._global_qreg_size_map
        )

        quantum_vars, classical_vars = [], []
        for actual_arg, formal_arg in zip(statement.arguments, subroutine_def.arguments):
            if isinstance(formal_arg, (qasm3_ast.ClassicalArgument, qasm3_ast.ExternArgument)):
                classical_vars.append(
                    Qasm3SubroutineProcessor.process_classical_arg(
                        formal_arg, actual_arg, fn_name, statement
                    )
                )
            else:
                quantum_vars.append(
                    Qasm3SubroutineProcessor.process_quantum_arg(
                        formal_arg,
                        actual_arg,
                        actual_qreg_size_map,
                        formal_qreg_size_map,
                        duplicate_qubit_detect_map,
                        qubit_transform_map,
                        fn_name,
                        statement,
                    )
                )

        self._scope_manager.push_scope({})
        self._scope_manager.increment_scope_level()
        self._scope_manager.push_context(Context.FUNCTION)

        for var in quantum_vars:
            self._scope_manager.add_var_in_scope(var)

        for var in classical_vars:
            self._scope_manager.add_var_in_scope(var)

        # push qubit transform maps
        self._function_qreg_size_map.append(formal_qreg_size_map)
        self._function_qreg_transform_map.append(qubit_transform_map)

        return_statement = None
        return_value = None
        result: list[qasm3_ast.Statement | qasm3_ast.FunctionCall] = []
        if isinstance(subroutine_def, qasm3_ast.ExternDeclaration):
            self._in_extern_function = True
            global_scope = self._scope_manager.get_global_scope()
            result.append(
                PulseValidator.validate_and_process_extern_function_call(
                    statement, global_scope, self._module._device_cycle_time
                )
            )
        else:
            for function_op in subroutine_def.body:
                if isinstance(function_op, qasm3_ast.ReturnStatement):
                    return_statement = copy.copy(function_op)
                    break
                try:
                    result.extend(self.visit_statement(copy.copy(function_op)))
                except (TypeError, copy.Error):
                    result.extend(self.visit_statement(copy.deepcopy(function_op)))

            if return_statement:
                return_value, stmts = Qasm3ExprEvaluator.evaluate_expression(
                    return_statement.expression,
                )
                return_value = Qasm3Validator.validate_return_statement(
                    subroutine_def, return_statement, return_value
                )
                result.extend(stmts)

        # remove qubit transformation map
        self._function_qreg_transform_map.pop()
        self._function_qreg_size_map.pop()

        self._scope_manager.restore_context()
        self._scope_manager.decrement_scope_level()
        self._scope_manager.pop_scope()

        if self._check_only and not self._in_extern_function:
            return return_value, []

        return return_value, result

    def _visit_while_loop(self, statement: qasm3_ast.WhileLoop) -> list[qasm3_ast.Statement]:
        """Visit a while-loop element.

        Args:
            statement (qasm3_ast.WhileLoop) - the while-loop AST node
        Returns:
            list[qasm3_ast.Statement] - flattened/unrolled statements
        Raises:
            ValidationError - if loop condition is non-classical or dynamic
            LoopLimitExceededError - if the loop exceeds the maximum limit"""

        result = []

        loop_counter = 0
        max_iterations = self._loop_limit

        if Qasm3Analyzer.condition_depends_on_measurement(
            statement.while_condition, self._measurement_set
        ):
            raise_qasm3_error(
                "Cannot unroll while-loop with condition depending on quantum measurement result.",
                error_node=statement,
                span=statement.span,
            )

        while True:
            cond_value = Qasm3ExprEvaluator.evaluate_expression(statement.while_condition)[0]
            if not cond_value:
                break

            self._scope_manager.push_context(Context.BLOCK)
            self._scope_manager.push_scope({})

            try:
                result.extend(self.visit_basic_block(statement.block))
            except LoopControlSignal as lcs:
                self._scope_manager.pop_scope()
                self._scope_manager.restore_context()
                if lcs.signal_type == "break":
                    break
                if lcs.signal_type == "continue":
                    continue

            self._scope_manager.pop_scope()
            self._scope_manager.restore_context()

            loop_counter += 1
            if loop_counter >= max_iterations:
                raise_qasm3_error(
                    "Loop exceeded max allowed iterations",
                    err_type=LoopLimitExceededError,
                    error_node=statement,
                    span=statement.span,
                )

        return result

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
        if self._scope_manager.check_in_scope(alias_reg_name):
            # Earlier Aliases can be updated
            if not alias_reg_name in self._global_alias_size_map:
                raise_qasm3_error(
                    f"Re-declaration of variable '{alias_reg_name}'",
                    error_node=statement,
                    span=statement.span,
                )

        if isinstance(value, qasm3_ast.Identifier):
            aliased_reg_name = value.name
        elif isinstance(value, qasm3_ast.IndexExpression) and isinstance(
            value.collection, qasm3_ast.Identifier
        ):
            aliased_reg_name = value.collection.name
        else:
            raise_qasm3_error(
                f"Unsupported aliasing {statement}", error_node=statement, span=statement.span
            )

        if aliased_reg_name not in self._global_qreg_size_map:
            raise_qasm3_error(
                f"Qubit register {aliased_reg_name} not found for aliasing",
                error_node=statement,
                span=statement.span,
            )
        aliased_reg_size = self._global_qreg_size_map[aliased_reg_name]
        if isinstance(value, qasm3_ast.Identifier):  # "let alias = q;"
            for i in range(aliased_reg_size):
                self._alias_qubit_labels[(alias_reg_name, i)] = (aliased_reg_name, i)
            alias_reg_size = aliased_reg_size
        elif isinstance(value, qasm3_ast.IndexExpression):
            if isinstance(value.index, qasm3_ast.DiscreteSet):  # "let alias = q[{0,1}];"
                qids = Qasm3Transformer.extract_values_from_discrete_set(value.index, statement)
                for i, qid in enumerate(qids):
                    Qasm3Validator.validate_register_index(
                        qid,
                        self._global_qreg_size_map[aliased_reg_name],
                        qubit=True,
                        op_node=statement,
                    )
                    self._alias_qubit_labels[(alias_reg_name, i)] = (aliased_reg_name, qid)
                alias_reg_size = len(qids)
            elif len(value.index) != 1:  # like "let alias = q[0,1];"?
                raise_qasm3_error(
                    "An index set can be specified by a single integer (signed or unsigned), "
                    "a comma-separated list of integers contained in braces {a,b,c,…}, "
                    "or a range",
                    error_node=statement,
                    span=statement.span,
                )
            elif isinstance(value.index[0], qasm3_ast.IntegerLiteral):  # "let alias = q[0];"
                qid = value.index[0].value
                Qasm3Validator.validate_register_index(
                    qid, self._global_qreg_size_map[aliased_reg_name], qubit=True, op_node=statement
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

        # we are updating as the alias can be redefined as well
        alias_var = Variable(
            alias_reg_name,
            qasm3_ast.QubitDeclaration,
            alias_reg_size,
            [],
            None,
            is_alias=True,
            span=statement.span,
        )

        if self._scope_manager.check_in_scope(alias_reg_name):
            # means, the alias is present in current scope
            alias_var.shadow = True
            self._scope_manager.update_var_in_scope(alias_var)
        else:
            # if the alias is not present already, we add it to the scope
            self._scope_manager.add_var_in_scope(alias_var)

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
            self._scope_manager.get_from_visible_scope(switch_target_name), qasm3_ast.IntType
        ):
            raise_qasm3_error(
                f"Switch target {switch_target_name} must be of type int",
                error_node=statement,
                span=statement.span,
            )

        switch_target_val = Qasm3ExprEvaluator.evaluate_expression(switch_target)[0]

        if len(statement.cases) == 0:
            raise_qasm3_error(
                "Switch statement must have at least one case",
                error_node=statement,
                span=statement.span,
            )

        # 2. handle the cases of the switch stmt
        #    each element in the list of the values
        #    should be of const int type and no duplicates should be present

        def _evaluate_case(statements):
            # can not put 'context' outside
            # BECAUSE the case expression CAN CONTAIN VARS from global scope
            self._scope_manager.push_context(Context.BLOCK)
            self._scope_manager.push_scope({})
            result = []
            for stmt in statements:
                Qasm3Validator.validate_statement_type(SWITCH_BLACKLIST_STMTS, stmt, "switch")
                result.extend(self.visit_statement(stmt))

            self._scope_manager.pop_scope()
            self._scope_manager.restore_context()
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
                        f"Duplicate case value {case_val} in switch statement",
                        error_node=case_expr,
                        span=case_expr.span,
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

    def _visit_delay_statement(
        self, statement: qasm3_ast.DelayInstruction
    ) -> list[qasm3_ast.Statement]:
        """
        Visit a DelayInstruction statement.
        Args:
            statement (qasm3_ast.DelayInstruction): The DelayInstruction statement to visit.
        Returns:
            list[qasm3_ast.Statement]: The list of statements generated by the DelayInstruction.
        """
        _delay_time_var = statement.duration
        global_scope = self._scope_manager.get_global_scope()
        curr_scope = self._scope_manager.get_curr_scope()
        # If curr_scope is pulse scope, mix the pulse scope and scope before pulse into curr_scope
        if self._scope_manager.in_pulse_scope():
            if len(self._scope_manager._context) > 2:
                if self._scope_manager._context[-2] != Context.GLOBAL:
                    curr_scope.update(self._scope_manager._scope[-2])

        PulseValidator.validate_duration_variable(
            _delay_time_var, statement, global_scope, curr_scope
        )
        duration_val, _ = Qasm3ExprEvaluator.evaluate_expression(
            _delay_time_var, dt=self._module._device_cycle_time
        )
        if duration_val:
            PulseValidator.validate_duration_literal_value(duration_val, statement)
            statement.duration = qasm3_ast.DurationLiteral(
                duration_val,
                unit=(
                    qasm3_ast.TimeUnit.dt
                    if self._module._device_cycle_time
                    else qasm3_ast.TimeUnit.ns
                ),
            )

        if self._scope_manager.in_box_scope():
            self._total_delay_duration_in_box += duration_val

        if statement.qubits is not None:
            _is_delay_frame = False
            for qubit in statement.qubits:
                if isinstance(qubit, qasm3_ast.Identifier):
                    frame = self._openpulse_scope_manager.get_from_global_scope(qubit.name)
                    if isinstance(frame, Frame):
                        frame.time = qasm3_ast.DurationLiteral(
                            frame.time.value + duration_val,
                            unit=frame.time.unit,
                        )
                        _is_delay_frame = True
            if _is_delay_frame:
                self._pulse_visitor._update_current_block_time(duration_val)
                return [statement]

        delay_qubit_bits = self._get_op_bits(statement, qubits=True)

        duplicate_delay_qubit = Qasm3Analyzer.extract_duplicate_qubit(delay_qubit_bits)
        if duplicate_delay_qubit:
            delay_qubit_name, delay_qubit_id = duplicate_delay_qubit
            raise_qasm3_error(
                f"Duplicate qubit '{delay_qubit_name}[{delay_qubit_id}]' arg in DelayInstruction",
                error_node=statement,
                span=statement.span,
            )

        if self._check_only:
            return []

        if not delay_qubit_bits:
            statement.qubits = [
                qasm3_ast.IndexedIdentifier(
                    name=qasm3_ast.Identifier(reg_name),
                    indices=[[qasm3_ast.IntegerLiteral(reg)]],
                )
                for reg_name, reg_size in self._global_qreg_size_map.items()
                for reg in range(reg_size)
            ]
        else:
            statement.qubits = delay_qubit_bits  # type: ignore[assignment]

        return [statement]

    def _visit_box_statement(self, statement: qasm3_ast.Box) -> list[qasm3_ast.Statement]:
        """
        Visit a Box statement.
        Args:
            statement (qasm3_ast.Box): The Box statement node to visit.
        Returns:
            list[qasm3_ast.Statement]: The list of statements generated by the Box statement.
        """
        statements = []
        _box_time_var = statement.duration
        box_duration_val = 0
        if _box_time_var is not None:
            global_scope = self._scope_manager.get_global_scope()
            PulseValidator.validate_duration_variable(_box_time_var, statement, global_scope, {})
            box_duration_val, _ = Qasm3ExprEvaluator.evaluate_expression(
                _box_time_var, dt=self._module._device_cycle_time
            )
            if box_duration_val:
                PulseValidator.validate_duration_literal_value(box_duration_val, statement)
                statement.duration = qasm3_ast.DurationLiteral(
                    box_duration_val,
                    unit=(
                        qasm3_ast.TimeUnit.dt
                        if self._module._device_cycle_time
                        else qasm3_ast.TimeUnit.ns
                    ),
                )
        self._scope_manager.push_scope({})
        self._scope_manager.increment_scope_level()
        self._scope_manager.push_context(Context.BOX)

        if statement.body:
            statements.extend(
                self.visit_basic_block(stmt_list=statement.body)  # type: ignore[arg-type]
            )
        else:
            raise_qasm3_error(
                "Box statement must have atleast one Quantum Statement.",
                error_node=statement,
                span=statement.span,
            )

        self._scope_manager.restore_context()
        self._scope_manager.decrement_scope_level()
        self._scope_manager.pop_scope()

        if (
            _box_time_var
            and box_duration_val
            and self._total_delay_duration_in_box > box_duration_val
        ):
            time_unit = "dt" if self._module._device_cycle_time else "ns"
            raise_qasm3_error(
                f"Total delay duration value '{self._total_delay_duration_in_box}{time_unit}' "
                f"should be less than 'box[{box_duration_val}{time_unit}]' duration.",
                error_node=statement,
                span=statement.span,
            )
        self._total_delay_duration_in_box = 0

        if self._check_only:
            return []
        statement.body = statements  # type: ignore[assignment]
        return [statement]

    def _visit_calibration_definition(
        self, statement: qasm3_ast.CalibrationDefinition
    ) -> list[Any]:
        """Visit a calibration definition element.

        Args:
            statement (qasm3_ast.CalibrationDefinition): The calibration definition to visit.

        Returns:
            None
        """
        from openpulse.parser import (  # pylint: disable=import-outside-toplevel
            OpenPulseParsingError,
            parse_openpulse,
        )

        if not self._consolidate_qubits:
            self._consolidate_qubits = True

        self._scope_manager.push_context(Context.PULSE)
        self._scope_manager.push_scope({})

        try:
            block_body = parse_openpulse(statement.body, in_defcal=True, permissive=False)
        except OpenPulseParsingError as err:
            _error_line = re.sub(
                r"line (\d+)",
                lambda m: f"line {statement.span.start_line + int(m.group(1)) - 1}",  # type: ignore
                str(err),
            )
            raise ValidationError(f"Failed to parse OpenPulse string: {_error_line}") from err

        result = []
        if len(self._global_qreg_size_map) > 1:
            raise_qasm3_error(
                "Openpulse program supports only one global qubit register. "
                f"Found: {list(self._global_qreg_size_map.keys())}",
                error_node=statement,
                span=statement.span,
            )
        if statement.name.name not in self._openpulse_qubit_map:
            self._openpulse_qubit_map[statement.name.name] = set()
        self._subroutine_defns[statement.name.name] = statement  # type: ignore[assignment]
        arg_vars = []
        for i, arg in enumerate(getattr(statement, "arguments", []) or []):
            if isinstance(arg, qasm3_ast.ClassicalArgument) and isinstance(
                arg.name, qasm3_ast.Identifier
            ):
                base_size = self._check_variable_type_size(
                    statement,
                    arg.name.name,
                    var_format="variable",
                    base_type=arg.type,
                )
                var = Variable(
                    name=arg.name.name,
                    value=0.0,
                    base_type=arg.type,
                    base_size=base_size,
                )
                self._scope_manager.add_var_in_scope(var)
                arg_vars.append(var)
            else:
                statement.arguments[i] = qasm3_ast.FloatLiteral(
                    Qasm3ExprEvaluator.evaluate_expression(arg)[0]
                )

        for qubit in statement.qubits:
            if not isinstance(qubit, qasm3_ast.Identifier):
                continue
            name = qubit.name
            if name.startswith("$") and name[1:].isdigit():
                self._openpulse_qubit_map[statement.name.name].add(name)
                self._total_pulse_qubits = max(self._total_pulse_qubits, int(name[1:]) + 1)
            elif name in self._global_qreg_size_map:
                reg_size = self._global_qreg_size_map[name]
                self._openpulse_qubit_map[statement.name.name].update(
                    f"${i}" for i in range(reg_size)
                )
            else:
                raise_qasm3_error(
                    f"Qubit register '{name}' is not declared",
                    error_node=statement,
                    span=statement.span,
                )

        calibration_stmts: list[qasm3_ast.Statement] = copy.deepcopy(block_body.body)
        for stmt in calibration_stmts:
            stmt.span.start_line = statement.span.start_line  # type: ignore
        result.extend(self._pulse_visitor.visit_basic_block(calibration_stmts, is_def_cal=True))

        for var in arg_vars:
            self._openpulse_scope_manager.remove_var_from_curr_scope(var)

        if len(result) == 0:
            return []

        if statement.return_type and isinstance(result[-1], qasm3_ast.ReturnStatement):
            return_stmt = result[-1]
            assert isinstance(return_stmt.expression, qasm3_ast.Identifier)
            _retrun_obj = self._openpulse_scope_manager.get_from_visible_scope(
                return_stmt.expression.name
            )
            if _retrun_obj and not isinstance(_retrun_obj.base_type, type(statement.return_type)):
                raise_qasm3_error(
                    f"Return type '{type(_retrun_obj.base_type).__name__}' does not match "
                    f"declaration type '{type(statement.return_type).__name__}'",
                    error_node=return_stmt,
                    span=return_stmt.span,
                )

        self._scope_manager.pop_scope()
        self._scope_manager.restore_context()

        if self._check_only:
            return [statement]

        old_stdout = sys.stdout
        captured_output = StringIO()
        sys.stdout = captured_output

        try:
            body_str = PulseUtils.format_calibration_body(block_body.body)
            _ = captured_output.getvalue()
        finally:
            # Restore stdout
            sys.stdout = old_stdout

        statement.body = "\n" + body_str

        return [statement]

    def _visit_calibration_statement(self, statement: qasm3_ast.CalibrationStatement) -> list[Any]:
        """Visit a calibration statement element.

        Args:
            statement (qasm3_ast.CalibrationStatement): The calibration statement to visit.

        Returns:
            None
        """
        from openpulse.parser import (  # pylint: disable=import-outside-toplevel
            OpenPulseParsingError,
            parse_openpulse,
        )

        if not self._consolidate_qubits:
            self._consolidate_qubits = True

        self._scope_manager.push_context(Context.PULSE)
        self._scope_manager.push_scope({})

        try:
            block_body = parse_openpulse(statement.body, in_defcal=False, permissive=False)
        except OpenPulseParsingError as err:
            _error_line = re.sub(
                r"line (\d+)",
                lambda m: f"line {statement.span.start_line + int(m.group(1)) - 1}",  # type: ignore
                str(err),
            )
            raise ValidationError(f"Failed to parse OpenPulse string: {_error_line}") from err

        result = []
        calibration_stmts: list[qasm3_ast.Statement] = block_body.body
        for stmt in calibration_stmts:
            stmt.span.start_line += statement.span.start_line  # type: ignore

        result.extend(self._pulse_visitor.visit_basic_block(calibration_stmts, is_def_cal=False))
        if len(result) == 0:
            return []

        self._scope_manager.pop_scope()
        self._scope_manager.restore_context()

        if self._check_only:
            return [statement]

        old_stdout = sys.stdout
        captured_output = StringIO()
        sys.stdout = captured_output

        try:
            body_str = PulseUtils.format_calibration_body(result)
            _ = captured_output.getvalue()
        finally:
            # Restore stdout
            sys.stdout = old_stdout

        statement.body = "\n" + body_str

        return [statement]

    def _visit_calibration_grammar_declaration(
        self, statement: qasm3_ast.CalibrationGrammarDeclaration
    ) -> list[qasm3_ast.Statement]:
        """Visit a calibration grammar declaration element.

        Args:
            statement (qasm3_ast.CalibrationGrammarDeclaration): The calibration grammar declaration

        Returns:
            None
        """
        if statement.name != "openpulse":
            raise_qasm3_error(
                f"Unsupported calibration grammar declaration: {statement.name}",
                error_node=statement,
                span=statement.span,
            )
        self._consolidate_qubits = True

        return [statement]

    def _visit_include(self, include: qasm3_ast.Include) -> list[qasm3_ast.Statement]:
        """Visit an include statement element.

        Args:
            include (qasm3_ast.Include): The include statement to visit.

        Returns:
            None
        """
        filename = include.filename
        if filename in self._included_files:
            raise_qasm3_error(
                f"File '{filename}' already included", error_node=include, span=include.span
            )
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
            qasm3_ast.WhileLoop: self._visit_while_loop,
            qasm3_ast.AliasStatement: self._visit_alias_statement,
            qasm3_ast.SwitchStatement: self._visit_switch_statement,
            qasm3_ast.SubroutineDefinition: self._visit_subroutine_definition,
            qasm3_ast.ExternDeclaration: self._visit_subroutine_definition,
            qasm3_ast.ExpressionStatement: lambda x: self._visit_function_call(x.expression),
            qasm3_ast.IODeclaration: lambda x: [],
            qasm3_ast.BreakStatement: self._visit_break,
            qasm3_ast.ContinueStatement: self._visit_continue,
            qasm3_ast.DelayInstruction: self._visit_delay_statement,
            qasm3_ast.Box: self._visit_box_statement,
            qasm3_ast.CalibrationDefinition: self._visit_calibration_definition,
            qasm3_ast.CalibrationStatement: self._visit_calibration_statement,
            qasm3_ast.CalibrationGrammarDeclaration: self._visit_calibration_grammar_declaration,
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
                f"Unsupported statement of type {type(statement)}",
                error_node=statement,
                span=statement.span,
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
        if self._consolidate_qubits:
            total_qubits = sum(self._global_qreg_size_map.values())
            total_qubits = max(total_qubits, self._total_pulse_qubits)
            if self._module._device_qubits is None:
                self._module._device_qubits = total_qubits
            unrolled_stmts = self._qubit_register_consolidation(unrolled_stmts, total_qubits)
        for stmt in unrolled_stmts:
            # Rule 1
            if isinstance(stmt, qasm3_ast.QuantumPhase):
                if len(stmt.qubits) == len(self._qubit_labels):
                    stmt.qubits = []
        Qasm3ExprEvaluator.angle_var_in_expr = None
        return unrolled_stmts
