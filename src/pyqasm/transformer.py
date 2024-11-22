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
Module with transformation functions for QASM3 visitor

"""
from copy import deepcopy
from typing import Any, Optional, Union

import numpy as np
from openqasm3.ast import (
    BinaryExpression,
    BinaryOperator,
    BooleanLiteral,
    DiscreteSet,
    FloatLiteral,
    Identifier,
    IndexedIdentifier,
    IndexExpression,
    IntegerLiteral,
)
from openqasm3.ast import IntType as Qasm3IntType
from openqasm3.ast import (
    QuantumBarrier,
    QuantumGate,
    QuantumPhase,
    QuantumReset,
    RangeDefinition,
    UintType,
    UnaryExpression,
    UnaryOperator,
)

from pyqasm.elements import Variable
from pyqasm.exceptions import raise_qasm3_error
from pyqasm.expressions import Qasm3ExprEvaluator
from pyqasm.maps import VARIABLE_TYPE_MAP
from pyqasm.validator import Qasm3Validator

# mypy: disable-error-code="attr-defined, union-attr"


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
    def extract_values_from_discrete_set(discrete_set: DiscreteSet) -> list[int]:
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
                    f"Unsupported discrete set value {value} in discrete set",
                    span=discrete_set.span,
                )
            values.append(value.value)
        return values

    @staticmethod
    def get_qubits_from_range_definition(
        range_def: RangeDefinition, qreg_size: int, is_qubit_reg: bool
    ) -> list[int]:
        """Get the qubits from a range definition.
        Args:
            range_def (RangeDefinition): The range definition to get qubits from.
            qreg_size (int): The size of the register.
            is_qubit_reg (bool): Whether the register is a qubit register.
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
        Qasm3Validator.validate_register_index(start_qid, qreg_size, qubit=is_qubit_reg)
        Qasm3Validator.validate_register_index(end_qid - 1, qreg_size, qubit=is_qubit_reg)
        return list(range(start_qid, end_qid, step))

    @staticmethod
    def transform_gate_qubits(
        gate_op: Union[QuantumGate, QuantumPhase], qubit_map: dict[str, IndexedIdentifier]
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
                    f"Indexing '{qubit.name.name}' not supported in gate definition",
                    span=qubit.span,
                )
            gate_qubit_name = qubit.name
            assert isinstance(gate_qubit_name, str)
            gate_op.qubits[i] = qubit_map[gate_qubit_name]

    @staticmethod
    def transform_expression(expression, variable_map: dict[str, Union[int, float, bool]]):
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
        gate_op: Union[QuantumGate, QuantumPhase], param_map: dict[str, Union[int, float, bool]]
    ) -> None:
        """Transform the parameters of a gate operation with a parameter map.

        Args:
            gate_op (QuantumGate): The gate operation to transform.
            param_map (dict[str, Union[int, float, bool]]): The parameter map to use
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
    def get_branch_params(condition: Any) -> tuple[Optional[int], str, Optional[bool]]:
        """
        Get the branch parameters from the branching condition

        Args:
            condition (Any): The condition to analyze

        Returns:
            tuple[Optional[int], str, Any]: register_idx, register_name, value of RHS
        """
        if isinstance(condition, Identifier):
            raise_qasm3_error(
                message="Only simple comparison supported in branching condition with "
                "classical register",
                span=condition.span,
            )
        if isinstance(condition, UnaryExpression):
            if condition.op != UnaryOperator["!"]:
                raise_qasm3_error(
                    message="Only '!' supported in branching condition with classical register",
                    span=condition.span,
                )
            return (
                condition.expression.index[0].value,
                condition.expression.collection.name,
                False,
            )
        if isinstance(condition, BinaryExpression):
            if condition.op != BinaryOperator["=="]:
                raise_qasm3_error(
                    message="Only '==' supported in branching condition with classical register",
                    span=condition.span,
                )

            if isinstance(condition.lhs, Identifier):
                # full register eg. if(c == 5)
                return (
                    None,
                    condition.lhs.name,
                    # do not evaluate to bool
                    Qasm3ExprEvaluator.evaluate_expression(condition.rhs, reqd_type=Qasm3IntType)[
                        0
                    ],
                )
            return (
                condition.lhs.index[0].value,
                condition.lhs.collection.name,
                # evaluate to bool
                Qasm3ExprEvaluator.evaluate_expression(condition.rhs)[0] != 0,
            )
        if isinstance(condition, IndexExpression):
            if isinstance(condition.index, DiscreteSet):
                raise_qasm3_error(
                    message="DiscreteSet not supported in branching condition",
                    span=condition.span,
                )
            if isinstance(condition.index, list):
                if isinstance(condition.index[0], RangeDefinition):
                    raise_qasm3_error(
                        message="RangeDefinition not supported in branching condition",
                        span=condition.span,
                    )
                return (condition.index[0].value, condition.collection.name, True)  # eg. if(c[0])
        # default case
        return None, "", None

    @classmethod
    def transform_function_qubits(
        cls,
        q_op: Union[QuantumGate, QuantumBarrier, QuantumReset, QuantumPhase],
        formal_qreg_sizes: dict[str, int],
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
        expanded_op_qubits = cls.visitor_obj._get_op_bits(q_op, formal_qreg_sizes)

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
        target: Union[Identifier, IndexExpression],
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
                        qid, qreg_size_map[target_name], qubit=True
                    )
                target_qubits_size = len(target_qids)
            elif isinstance(target.index[0], (IntegerLiteral, Identifier)):  # "(q[0]); OR (q[i]);"
                target_qids = [Qasm3ExprEvaluator.evaluate_expression(target.index[0])[0]]
                Qasm3Validator.validate_register_index(
                    target_qids[0], qreg_size_map[target_name], qubit=True
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
