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
Module with analysis functions for QASM visitor

"""
from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, Optional

import numpy as np
from openqasm3.ast import (
    DiscreteSet,
    Expression,
    Identifier,
    IndexedIdentifier,
    IndexExpression,
    IntegerLiteral,
    IntType,
    QuantumGate,
    QuantumMeasurementStatement,
    RangeDefinition,
    Span,
)

from pyqasm.exceptions import QasmParsingError, ValidationError, raise_qasm3_error

if TYPE_CHECKING:
    from pyqasm.elements import Variable
    from pyqasm.expressions import Qasm3ExprEvaluator


class Qasm3Analyzer:
    """Class with utility functions for analyzing QASM3 elements"""

    @classmethod
    def analyze_classical_indices(
        cls, indices: list[Any], var: Variable, expr_evaluator: Qasm3ExprEvaluator
    ) -> list:
        """Validate the indices for a classical variable.

        Args:
            indices (list[Any]): The indices to validate.
            var (Variable): The variable to verify

        Raises:
            ValidationError: If the indices are invalid.

        Returns:
            list[list]: The list of indices. Note, we can also have a list of indices within
                        a list if the variable is a multi-dimensional array.
        """
        indices_list = []
        var_dimensions: Optional[list[int]] = var.dims

        if var_dimensions is None or len(var_dimensions) == 0:
            raise_qasm3_error(
                message=f"Indexing error. Variable {var.name} is not an array",
                err_type=ValidationError,
                error_node=indices[0],
                span=indices[0].span,
            )
        if isinstance(indices, DiscreteSet):
            indices = indices.values

        if len(indices) != len(var_dimensions):  # type: ignore[arg-type]
            raise_qasm3_error(
                message=f"Invalid number of indices for variable {var.name}. "
                f"Expected {len(var_dimensions)} but got {len(indices)}",  # type: ignore[arg-type]
                err_type=ValidationError,
                error_node=indices[0],
                span=indices[0].span,
            )

        def _validate_index(index, dimension, var_name, index_node, dim_num):
            if index < 0 or index >= dimension:
                raise_qasm3_error(
                    message=f"Index {index} out of bounds for dimension {dim_num} "
                    f"of variable '{var_name}'. Expected index in range [0, {dimension-1}]",
                    err_type=ValidationError,
                    error_node=index_node,
                    span=index_node.span,
                )

        def _validate_step(start_id, end_id, step, index_node):
            if (step < 0 and start_id < end_id) or (step > 0 and start_id > end_id):
                direction = "less than" if step < 0 else "greater than"
                raise_qasm3_error(
                    message=f"Index {start_id} is {direction} {end_id} but step"
                    f" is {'negative' if step < 0 else 'positive'}",
                    err_type=ValidationError,
                    error_node=index_node,
                    span=index_node.span,
                )

        for i, index in enumerate(indices):
            if not isinstance(index, (Identifier, Expression, RangeDefinition, IntegerLiteral)):
                raise_qasm3_error(
                    message=f"Unsupported index type '{type(index)}' for "
                    f"classical variable '{var.name}'",
                    err_type=ValidationError,
                    error_node=index,
                    span=index.span,
                )

            if isinstance(index, RangeDefinition):
                assert var_dimensions is not None

                start_id = 0
                if index.start is not None:
                    start_id = expr_evaluator.evaluate_expression(index.start, reqd_type=IntType)[0]

                end_id = var_dimensions[i] - 1
                if index.end is not None:
                    end_id = expr_evaluator.evaluate_expression(index.end, reqd_type=IntType)[0]

                step = 1
                if index.step is not None:
                    step = expr_evaluator.evaluate_expression(index.step, reqd_type=IntType)[0]

                _validate_index(start_id, var_dimensions[i], var.name, index, i)
                _validate_index(end_id, var_dimensions[i], var.name, index, i)
                _validate_step(start_id, end_id, step, index)

                indices_list.append((start_id, end_id, step))

            if isinstance(index, (Identifier, IntegerLiteral, Expression)):
                index_value = expr_evaluator.evaluate_expression(index, reqd_type=IntType)[0]
                curr_dimension = var_dimensions[i]  # type: ignore[index]
                _validate_index(index_value, curr_dimension, var.name, index, i)

                indices_list.append((index_value, index_value, 1))

        return indices_list

    @staticmethod
    def analyze_index_expression(
        index_expr: IndexExpression,
    ) -> tuple[str, list[Any | Expression | RangeDefinition]]:
        """Analyze an index expression to get the variable name and indices.

        Args:
            index_expr (IndexExpression): The index expression to analyze.

        Returns:
            tuple[str, list[Any]]: The variable name and indices in openqasm objects

        """
        indices: list[Any] = []
        var_name = ""
        comma_separated = False

        if isinstance(index_expr.collection, IndexExpression):
            while isinstance(index_expr, IndexExpression):
                if isinstance(index_expr.index, list):
                    indices.append(index_expr.index[0])
                    index_expr = index_expr.collection
        else:
            comma_separated = True
            indices = index_expr.index  # type: ignore[assignment]
        var_name = (
            index_expr.collection.name  # type: ignore[attr-defined]
            if comma_separated
            else index_expr.name  # type: ignore[attr-defined]
        )
        if not comma_separated:
            indices = indices[::-1]

        return var_name, indices

    @staticmethod
    def find_array_element(multi_dim_arr: np.ndarray, indices: list[tuple[int, int, int]]) -> Any:
        """Find the value of an array at the specified indices.

        Args:
            multi_dim_arr (np.ndarray): The multi-dimensional list to search.
            indices (list[tuple[int,int,int]]): The indices to search.

        Returns:
            Any: The value at the specified indices.
        """
        slicing = tuple(
            slice(start, end + 1, step) if start != end else start for start, end, step in indices
        )
        return multi_dim_arr[slicing]  # type: ignore[index]

    @staticmethod
    def get_op_bit_list(operation):
        """
        Get the list of qubits associated with an operation.

        Args:
            operation (QuantumOperation): The quantum operation.

        Returns:
            list: The list of qubits associated with the operation.
        """
        bit_list = []
        if isinstance(operation, QuantumMeasurementStatement):
            assert operation.target is not None
            bit_list = [operation.measure.qubit]
        else:
            bit_list = (
                operation.qubits
                if isinstance(operation.qubits, list)
                else [operation.qubits]  # type: ignore[assignment]
            )
        return bit_list

    @staticmethod  # pylint: disable-next=inconsistent-return-statements
    def extract_qasm_version(qasm: str) -> float:  # type: ignore[return]
        """
        Extracts the OpenQASM version from a given OpenQASM string.

        Args:
            qasm (str): The OpenQASM program as a string.

        Returns:
            The semantic version as a float.
        """
        qasm = re.sub(r"//.*", "", qasm)
        qasm = re.sub(r"/\*.*?\*/", "", qasm, flags=re.DOTALL)

        lines = qasm.strip().splitlines()

        for line in lines:
            line = line.strip()
            if line.startswith("OPENQASM"):
                match = re.match(r"OPENQASM\s+(\d+)(?:\.(\d+))?;", line)
                if match:
                    major = int(match.group(1))
                    minor = int(match.group(2)) if match.group(2) else 0
                    return float(f"{major}.{minor}")

        raise_qasm3_error("Could not determine the OpenQASM version.", err_type=QasmParsingError)

    @staticmethod
    def extract_duplicate_qubit(qubit_list: list[IndexedIdentifier]):
        """
        Extracts the duplicate qubit from a list of qubits.

        Args:
            qubit_list (list[IndexedIdentifier]): The list of qubits.

        Returns:
            tuple(string, int): The duplicate qubit name and id.
        """
        qubit_set = set()
        for qubit in qubit_list:
            assert isinstance(qubit, IndexedIdentifier)
            qubit_name = qubit.name.name
            qubit_id = qubit.indices[0][0].value  # type: ignore
            if (qubit_name, qubit_id) in qubit_set:
                return (qubit_name, qubit_id)
            qubit_set.add((qubit_name, qubit_id))
        return None

    @staticmethod
    def verify_gate_qubits(gate: QuantumGate, span: Optional[Span] = None):
        """
        Verify the qubits for a quantum gate.

        Args:
            gate (QuantumGate): The quantum gate.
            span (Span, optional): The span of the gate.

        Raises:
            ValidationError: If qubits are duplicated.

        Returns:
            None
        """
        # 1. check for duplicate bits
        duplicate_qubit = Qasm3Analyzer.extract_duplicate_qubit(gate.qubits)  # type: ignore
        if duplicate_qubit:
            qubit_name, qubit_id = duplicate_qubit
            raise_qasm3_error(
                f"Duplicate qubit '{qubit_name}[{qubit_id}]' arg in gate {gate.name.name}",
                error_node=gate,
                span=span,
            )
