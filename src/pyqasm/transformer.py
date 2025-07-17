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
Module with transformation functions for QASM3 visitor

"""
from copy import deepcopy
from typing import Any, NamedTuple, Optional, Sequence, cast

import numpy as np
from openqasm3.ast import (
    BinaryExpression,
    BinaryOperator,
    BooleanLiteral,
    DiscreteSet,
    Expression,
    FloatLiteral,
    Identifier,
    IndexedIdentifier,
    IndexExpression,
    IntegerLiteral,
)
from openqasm3.ast import IntType as Qasm3IntType
from openqasm3.ast import (
    QASMNode,
    QuantumBarrier,
    QuantumGate,
    QuantumMeasurementStatement,
    QuantumPhase,
    QuantumReset,
    RangeDefinition,
    Statement,
    UintType,
    UnaryExpression,
    UnaryOperator,
)

from pyqasm.elements import Variable
from pyqasm.exceptions import raise_qasm3_error
from pyqasm.expressions import Qasm3ExprEvaluator
from pyqasm.maps.expressions import VARIABLE_TYPE_MAP
from pyqasm.validator import Qasm3Validator

# mypy: disable-error-code="attr-defined, union-attr"

BranchParams = NamedTuple(
    "BranchParams",
    [
        ("reg_idx", Optional[int]),
        ("reg_name", str),
        ("op", Optional[BinaryOperator | UnaryOperator]),
        ("rhs_val", Optional[bool | int]),
    ],
)


class Qasm3Transformer:
    """Class with utility functions for transforming QASM elements"""

    visitor_obj = None

    @classmethod
    def set_visitor_obj(cls, visitor_obj) -> None:
        """Set the visitor object.

        Args:
            visitor_obj: The visitor object.
        """
        cls.visitor_obj = visitor_obj

    @staticmethod
    def update_array_element(
        multi_dim_arr: np.ndarray, indices: list[tuple[int, int, int]], value: Any
    ) -> None:
        """Update the value of an array at the specified indices. Single element only.

        Args:
            multi_dim_arr (np.ndarray): The multi-dimensional array to update.
            indices (list[tuple[int,int,int]]): The indices to update.
            value (Any): The value to update.

        Returns:
            None
        """
        slicing = tuple(
            slice(start, stop + 1, step) if start != stop else start
            for start, stop, step in indices
        )
        multi_dim_arr[slicing] = value

    @staticmethod
    def extract_values_from_discrete_set(
        discrete_set: DiscreteSet, op_node: Optional[QASMNode] = None
    ) -> list[int]:
        """Extract the values from a discrete set.

        Args:
            discrete_set (DiscreteSet): The discrete set to extract values from.

        Returns:
            list[int]: The extracted values.
        """
        values = []
        for value in discrete_set.values:
            if not isinstance(value, IntegerLiteral):
                raise_qasm3_error(
                    f"Unsupported value '{Qasm3ExprEvaluator.evaluate_expression(value)[0]}' "
                    "in discrete set",
                    error_node=op_node if op_node else discrete_set,
                    span=op_node.span if op_node else discrete_set.span,
                )
            values.append(value.value)
        return values

    @staticmethod
    def get_qubits_from_range_definition(
        range_def: RangeDefinition,
        qreg_size: int,
        is_qubit_reg: bool,
        op_node: Optional[QASMNode] = None,
    ) -> list[int]:
        """Get the qubits from a range definition.
        Args:
            range_def (RangeDefinition): The range definition to get qubits from.
            qreg_size (int): The size of the register.
            is_qubit_reg (bool): Whether the register is a qubit register.
            op_node (Optional[QASMNode]): The operation node.
        Returns:
            list[int]: The list of qubit identifiers.
        """
        start_qid = (
            0
            if range_def.start is None
            else Qasm3ExprEvaluator.evaluate_expression(range_def.start)[0]
        )
        end_qid = (
            qreg_size
            if range_def.end is None
            else Qasm3ExprEvaluator.evaluate_expression(range_def.end)[0]
        )
        step = (
            1
            if range_def.step is None
            else Qasm3ExprEvaluator.evaluate_expression(range_def.step)[0]
        )
        Qasm3Validator.validate_register_index(
            start_qid, qreg_size, qubit=is_qubit_reg, op_node=op_node
        )
        Qasm3Validator.validate_register_index(
            end_qid - 1, qreg_size, qubit=is_qubit_reg, op_node=op_node
        )
        return list(range(start_qid, end_qid, step))

    @staticmethod
    def transform_gate_qubits(
        gate_op: QuantumGate | QuantumPhase, qubit_map: dict[str, IndexedIdentifier]
    ) -> None:
        """Transform the qubits of a gate operation with a qubit map.

        Args:
            gate_op (QuantumGate): The gate operation to transform.
            qubit_map (dict[str, IndexedIdentifier]): The qubit map to use for transformation.

        Returns:
            None
        """
        if isinstance(gate_op, QuantumPhase) and len(gate_op.qubits) == 0:
            gate_op.qubits = deepcopy(list(qubit_map.values()))
            return
        for i, qubit in enumerate(gate_op.qubits):
            if isinstance(qubit, IndexedIdentifier):
                raise_qasm3_error(
                    f"Indexing '{qubit.name.name}' not supported in gate definition "
                    f"for gate {gate_op.name}",
                    error_node=gate_op,
                    span=qubit.span,
                )
            gate_qubit_name = qubit.name
            assert isinstance(gate_qubit_name, str)
            gate_op.qubits[i] = qubit_map[gate_qubit_name]

    @staticmethod
    def transform_expression(expression, variable_map: dict[str, int | float | bool]):
        """Transform an expression by replacing variables with their values.

        Args:
            expression (Any): The expression to transform.
            variable_map (dict): The mapping of variables to their values.

        Returns:
            expression (Any): The transformed expression.
        """
        if expression is None:
            return None

        if isinstance(expression, (BooleanLiteral, IntegerLiteral, FloatLiteral)):
            return expression

        if isinstance(expression, BinaryExpression):
            lhs = Qasm3Transformer.transform_expression(expression.lhs, variable_map)
            rhs = Qasm3Transformer.transform_expression(expression.rhs, variable_map)
            expression.lhs = lhs
            expression.rhs = rhs

        if isinstance(expression, UnaryExpression):
            operand = Qasm3Transformer.transform_expression(expression.expression, variable_map)
            expression.expression = operand

        if isinstance(expression, Identifier):
            if expression.name in variable_map:
                value = variable_map[expression.name]
                if isinstance(value, int):
                    return IntegerLiteral(value)
                if isinstance(value, float):
                    return FloatLiteral(value)
                if isinstance(value, bool):
                    return BooleanLiteral(value)

        return expression

    @staticmethod
    def transform_gate_params(
        gate_op: QuantumGate | QuantumPhase, param_map: dict[str, int | float | bool]
    ) -> None:
        """Transform the parameters of a gate operation with a parameter map.

        Args:
            gate_op (QuantumGate): The gate operation to transform.
            param_map (dict[str, int |float |bool]): The parameter map to use
                                                            for transformation.

        Returns:
            None: arguments are transformed in place
        """
        # gate_op.arguments is a list of "actual" arguments used in the gate call inside body

        # param map is a "global dict for this gate" which contains the binding of the params
        # to the actual values used in the call
        if isinstance(gate_op, QuantumGate):
            for i, actual_arg in enumerate(gate_op.arguments):
                # recursively replace ALL instances of the parameter in the expression
                # with the actual value
                gate_op.arguments[i] = Qasm3Transformer.transform_expression(actual_arg, param_map)
        else:
            gate_op.argument = Qasm3Transformer.transform_expression(gate_op.argument, param_map)

    @staticmethod
    def get_branch_params(
        condition: Expression,
    ) -> BranchParams:
        """
        Get the branch parameters from the branching condition

        Args:
            condition (Any): The condition to analyze

        Returns:
            BranchParams
        """
        if isinstance(condition, Identifier):
            raise_qasm3_error(
                message="Only simple comparison supported in branching condition with "
                "classical register",
                error_node=condition,
                span=condition.span,
            )
        if isinstance(condition, UnaryExpression):
            if condition.op != UnaryOperator["!"]:
                raise_qasm3_error(
                    message="Only '!' supported in branching condition with classical register",
                    error_node=condition,
                    span=condition.span,
                )
            return BranchParams(
                condition.expression.index[0].value,
                condition.expression.collection.name,
                condition.op,
                False,
            )
        if isinstance(condition, BinaryExpression):
            if condition.op not in [BinaryOperator[o] for o in ["==", ">=", "<=", ">", "<"]]:
                raise_qasm3_error(
                    message="Only {==, >=, <=, >, <} supported in branching condition "
                    "with classical register",
                    error_node=condition,
                    span=condition.span,
                )

            if isinstance(condition.lhs, Identifier):
                # full register eg. if(c == 5)
                return BranchParams(
                    None,
                    condition.lhs.name,
                    condition.op,
                    # do not evaluate to bool
                    Qasm3ExprEvaluator.evaluate_expression(condition.rhs, reqd_type=Qasm3IntType)[
                        0
                    ],
                )
            return BranchParams(
                condition.lhs.index[0].value,
                condition.lhs.collection.name,
                condition.op,
                # evaluate to bool
                Qasm3ExprEvaluator.evaluate_expression(condition.rhs)[0] != 0,
            )
        if isinstance(condition, IndexExpression):
            if isinstance(condition.index, DiscreteSet):
                raise_qasm3_error(
                    message="DiscreteSet not supported in branching condition",
                    error_node=condition,
                    span=condition.span,
                )
            if isinstance(condition.index, list):
                if isinstance(condition.index[0], RangeDefinition):
                    raise_qasm3_error(
                        message="RangeDefinition not supported in branching condition",
                        error_node=condition,
                        span=condition.span,
                    )
                return BranchParams(
                    condition.index[0].value,
                    condition.collection.name,
                    BinaryOperator["=="],
                    True,
                )  # eg. if(c[0])
        # default case
        return BranchParams(None, "", None, None)

    @classmethod
    def transform_function_qubits(
        cls,
        q_op: QuantumGate | QuantumBarrier | QuantumReset | QuantumPhase,
        qubit_map: dict[tuple, tuple],
    ) -> list[IndexedIdentifier]:
        """Transform the qubits of a function call to the actual qubits.

        Args:
            visitor_obj: The visitor object.
            gate_op: The quantum operation to transform.
            formal_qreg_sizes (dict[str: int]): The formal qubit register sizes.
            qubit_map (dict[tuple: tuple]): The mapping of formal qubits to actual qubits.

        Returns:
            None
        """
        expanded_op_qubits = cls.visitor_obj._get_op_bits(q_op)

        transformed_qubits = []
        for qubit in expanded_op_qubits:
            formal_qreg_name = qubit.name.name
            formal_qreg_idx = qubit.indices[0][0].value

            # replace the formal qubit with the actual qubit
            actual_qreg_name, actual_qreg_idx = qubit_map[(formal_qreg_name, formal_qreg_idx)]
            transformed_qubits.append(
                IndexedIdentifier(
                    Identifier(actual_qreg_name),
                    [[IntegerLiteral(actual_qreg_idx)]],
                )
            )

        return transformed_qubits

    @classmethod
    def get_target_qubits(
        cls,
        target: Identifier | IndexExpression,
        qreg_size_map: dict[str, int],
        target_name: str,
    ) -> tuple:
        """Get the target qubits of a statement.

        Args:
            target (Any): The target of the statement.
            qreg_size_map (dict[str: int]): The quantum register size map.
            target_name (str): The name of the register.

        Returns:
            tuple: The target qubits.
        """
        target_qids = None
        target_qubits_size = None

        if isinstance(target, Identifier):  # "(q);"
            target_qids = list(range(qreg_size_map[target_name]))
            target_qubits_size = qreg_size_map[target_name]

        elif isinstance(target, IndexExpression):
            if isinstance(target.index, DiscreteSet):  # "(q[{0,1}]);"
                target_qids = Qasm3Transformer.extract_values_from_discrete_set(target.index)
                for qid in target_qids:
                    Qasm3Validator.validate_register_index(
                        qid, qreg_size_map[target_name], qubit=True, op_node=target
                    )
                target_qubits_size = len(target_qids)
            elif isinstance(target.index[0], (IntegerLiteral, Identifier)):  # "(q[0]); OR (q[i]);"
                target_qids = [Qasm3ExprEvaluator.evaluate_expression(target.index[0])[0]]
                Qasm3Validator.validate_register_index(
                    target_qids[0], qreg_size_map[target_name], qubit=True, op_node=target
                )
                target_qubits_size = 1
            elif isinstance(target.index[0], RangeDefinition):  # "(q[0:1:2]);"
                target_qids = Qasm3Transformer.get_qubits_from_range_definition(
                    target.index[0],
                    qreg_size_map[target_name],
                    is_qubit_reg=True,
                )
                target_qubits_size = len(target_qids)
        return target_qids, target_qubits_size

    @staticmethod
    def get_type_string(variable: Variable) -> str:
        """Get the type string for a variable."""
        base_type = variable.base_type
        base_size = variable.base_size
        dims = variable.dims
        is_array = dims and len(dims) > 0
        type_str = "" if not is_array else "array["

        type_str += VARIABLE_TYPE_MAP[base_type.__class__].__name__
        if base_type.__class__ == UintType:
            type_str = type_str.replace("int", "uint")
        if base_size:
            type_str += f"[{base_size}]"

        if is_array:
            type_str += f", {', '.join([str(dim) for dim in dims])}]"
        return type_str

    @staticmethod
    def consolidate_qubit_registers(  # pylint: disable=too-many-branches, too-many-locals, too-many-statements
        unrolled_stmts: Sequence[Statement] | Statement,
        qubit_register_offsets: dict[str, int],
        global_qreg_size_map: dict[str, int],
        device_qubits: int | None,
    ) -> Sequence[Statement] | Statement:
        """Transform statements by mapping qubit registers to device qubit register indices

        Args:
            unrolled_stmts : The statements or single statement to transform.
            qubit_register_offsets (dict): Mapping from register name to its
                                           offset in the global qubit array.
            global_qreg_size_map (dict): original global qubit register mapping.
            device_qubits (int): Total number of device qubits

        Returns:
            The transformed statements or statement with qubit registers mapped to device indices.
        """
        if device_qubits is None:
            device_qubits = sum(global_qreg_size_map.values())

        def _get_pyqasm_device_qubit_index(
            reg: str, idx: int, qubit_reg_offsets: dict[str, int], global_qreg: dict[str, int]
        ):
            _offsets = qubit_reg_offsets
            _n_qubits = global_qreg[reg]
            if not 0 <= idx < _n_qubits:
                raise IndexError(f"{reg}[{idx}] out of range (0..{_n_qubits-1})")
            return _offsets[reg] + idx

        if isinstance(unrolled_stmts, QuantumBarrier):
            _qubit_id = cast(Identifier, unrolled_stmts.qubits[0])  # type: ignore[union-attr]
            if not isinstance(_qubit_id, IndexedIdentifier):
                _start = _get_pyqasm_device_qubit_index(
                    _qubit_id.name, 0, qubit_register_offsets, global_qreg_size_map
                )
                _end = _get_pyqasm_device_qubit_index(
                    _qubit_id.name,
                    global_qreg_size_map[_qubit_id.name] - 1,
                    qubit_register_offsets,
                    global_qreg_size_map,
                )
                if _start == 0:
                    _qubit_id.name = f"__PYQASM_QUBITS__[:{_end+1}]"
                elif _end == device_qubits - 1:
                    _qubit_id.name = f"__PYQASM_QUBITS__[{_start}:]"
                else:
                    _qubit_id.name = f"__PYQASM_QUBITS__[{_start}:{_end+1}]"
            else:
                _qubit_str = cast(str, unrolled_stmts.qubits[0].name)  # type: ignore[union-attr]
                _qubit_ind = cast(
                    list, unrolled_stmts.qubits[0].indices
                )  # type: ignore[union-attr]
                for multi_ind in _qubit_ind:
                    for ind in multi_ind:
                        pyqasm_ind = _get_pyqasm_device_qubit_index(
                            _qubit_str.name, ind.value, qubit_register_offsets, global_qreg_size_map
                        )
                        ind.value = pyqasm_ind
                _qubit_str.name = "__PYQASM_QUBITS__"

        if isinstance(unrolled_stmts, list):  # pylint: disable=too-many-nested-blocks
            if isinstance(unrolled_stmts[0], QuantumMeasurementStatement):
                for stmt in unrolled_stmts:
                    _qubit_id = cast(
                        Identifier, stmt.measure.qubit.name
                    )  # type: ignore[union-attr]
                    _qubit_ind = cast(list, stmt.measure.qubit.indices)  # type: ignore[union-attr]
                    for multiple_ind in _qubit_ind:
                        for ind in multiple_ind:
                            _pyqasm_val = _get_pyqasm_device_qubit_index(
                                _qubit_id.name,
                                ind.value,
                                qubit_register_offsets,
                                global_qreg_size_map,
                            )
                            ind.value = _pyqasm_val
                    _qubit_id.name = "__PYQASM_QUBITS__"

            if isinstance(unrolled_stmts[0], QuantumReset):
                for stmt in unrolled_stmts:
                    _qubit_str = cast(str, stmt.qubits.name.name)  # type: ignore[union-attr]
                    _qubit_ind = cast(list, stmt.qubits.indices)  # type: ignore[union-attr]
                    for multiple_ind in _qubit_ind:
                        for ind in multiple_ind:
                            _pyqasm_val = _get_pyqasm_device_qubit_index(
                                _qubit_str, ind.value, qubit_register_offsets, global_qreg_size_map
                            )
                            ind.value = _pyqasm_val
                    stmt.qubits.name.name = "__PYQASM_QUBITS__"  # type: ignore[union-attr]

            if isinstance(unrolled_stmts[0], QuantumBarrier):
                for stmt in unrolled_stmts:
                    _qubit_ind_id = cast(
                        IndexedIdentifier, stmt.qubits[0]
                    )  # type: ignore[union-attr]
                    _original_qubit_name = _qubit_ind_id.name.name
                    for multiple_ind in _qubit_ind_id.indices:
                        for ind in multiple_ind:  # type: ignore[union-attr]
                            ind_val = cast(IntegerLiteral, ind)  # type: ignore[union-attr]
                            pyqasm_val = _get_pyqasm_device_qubit_index(
                                _original_qubit_name,
                                ind_val.value,
                                qubit_register_offsets,
                                global_qreg_size_map,
                            )
                            ind_val.value = pyqasm_val
                    _qubit_ind_id.name.name = "__PYQASM_QUBITS__"

            if isinstance(unrolled_stmts[0], QuantumGate):
                for stmt in unrolled_stmts:
                    stmt_qubits: list[IndexedIdentifier] = []
                    for qubit in stmt.qubits:
                        pyqasm_val = _get_pyqasm_device_qubit_index(
                            qubit.name.name,
                            qubit.indices[0][0].value,
                            qubit_register_offsets,
                            global_qreg_size_map,
                        )
                        stmt_qubits.append(
                            IndexedIdentifier(
                                Identifier("__PYQASM_QUBITS__"), [[IntegerLiteral(pyqasm_val)]]
                            )
                        )
                    stmt.qubits = stmt_qubits

        return unrolled_stmts
