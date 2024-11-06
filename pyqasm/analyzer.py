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
Module with analysis functions for QASM visitor

"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional, Union

import numpy as np
from openqasm3 import parse
from openqasm3.ast import (
    DiscreteSet,
    Expression,
    Identifier,
    IndexExpression,
    IntegerLiteral,
    IntType,
    QuantumMeasurementStatement,
    RangeDefinition,
)
from openqasm3.parser import QASM3ParsingError

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
            indices (list[list[Any]]): The indices to validate.
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
                span=indices[0].span,
            )
        if isinstance(indices, DiscreteSet):
            indices = indices.values

        if len(indices) != len(var_dimensions):  # type: ignore[arg-type]
            raise_qasm3_error(
                message=f"Invalid number of indices for variable {var.name}. "
                f"Expected {len(var_dimensions)} but got {len(indices)}",  # type: ignore[arg-type]
                err_type=ValidationError,
                span=indices[0].span,
            )

        def _validate_index(index, dimension, var_name, span, dim_num):
            if index < 0 or index >= dimension:
                raise_qasm3_error(
                    message=f"Index {index} out of bounds for dimension {dim_num} "
                    f"of variable {var_name}",
                    err_type=ValidationError,
                    span=span,
                )

        def _validate_step(start_id, end_id, step, span):
            if (step < 0 and start_id < end_id) or (step > 0 and start_id > end_id):
                direction = "less than" if step < 0 else "greater than"
                raise_qasm3_error(
                    message=f"Index {start_id} is {direction} {end_id} but step"
                    f" is {'negative' if step < 0 else 'positive'}",
                    err_type=ValidationError,
                    span=span,
                )

        for i, index in enumerate(indices):
            if not isinstance(index, (Identifier, Expression, RangeDefinition, IntegerLiteral)):
                raise_qasm3_error(
                    message=f"Unsupported index type {type(index)} for "
                    f"classical variable {var.name}",
                    err_type=ValidationError,
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

                _validate_index(start_id, var_dimensions[i], var.name, index.span, i)
                _validate_index(end_id, var_dimensions[i], var.name, index.span, i)
                _validate_step(start_id, end_id, step, index.span)

                indices_list.append((start_id, end_id, step))

            if isinstance(index, (Identifier, IntegerLiteral, Expression)):
                index_value = expr_evaluator.evaluate_expression(index, reqd_type=IntType)[0]
                curr_dimension = var_dimensions[i]  # type: ignore[index]
                _validate_index(index_value, curr_dimension, var.name, index.span, i)

                indices_list.append((index_value, index_value, 1))

        return indices_list

    @staticmethod
    def analyze_index_expression(
        index_expr: IndexExpression,
    ) -> tuple[str, list[Union[Any, Expression, RangeDefinition]]]:
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

    @staticmethod
    def extract_qasm_version(qasm: str) -> int:  # type: ignore # pylint: disable=R1710
        """
        Parses an OpenQASM program string to determine its major version, either 2 or 3.

        Args:
            qasm (str): The OpenQASM program string.

        Returns:
            int: The OpenQASM version as an integer.

        Raises:
            QasmError: If the string does not represent a valid OpenQASM program.
        """
        try:
            # TODO: optimize this to just check the start of the program for version
            parsed_program = parse(qasm)
            assert parsed_program.version is not None
            version = int(float(parsed_program.version))
            return version
        except (QASM3ParsingError, ValueError, TypeError):
            raise_qasm3_error(
                "Could not determine the OpenQASM version.", err_type=QasmParsingError
            )
