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
    BinaryExpression,
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
    UnaryExpression,
)

from pyqasm.exceptions import QasmParsingError, ValidationError, raise_qasm3_error

if TYPE_CHECKING:
    from pyqasm.elements import Variable
    from pyqasm.expressions import Qasm3ExprEvaluator


def bits_to_int(value: Any, width: int) -> int:
    """Convert a ``bit[n]`` value in any legacy form to a masked ``int``.

    Accepts the historical representations (``str`` bitstring, ``numpy.ndarray`` of
    0/1, plain ``int``/``bool``) and returns a Python ``int`` with only the low
    ``width`` bits set. Bit 0 of a ``bit[n]`` register is the most-significant bit
    of the resulting integer.

    Args:
        value: The bit value to convert. Empty string yields ``0``.
        width: The register width, in bits. Must be non-negative.

    Returns:
        int: The width-masked integer representation.
    """
    if width <= 0:
        return 0
    mask = (1 << width) - 1
    if isinstance(value, str):
        if value == "":
            return 0
        return int(value, 2) & mask
    if isinstance(value, np.ndarray):
        flat = value.flatten()
        if flat.size == 0:
            return 0
        return int("".join(str(int(b)) for b in flat), 2) & mask
    return int(value) & mask


def int_to_bits(value: int, width: int) -> str:
    """Serialize an integer to a zero-padded, width-`n` bit string.

    Args:
        value: The integer value; only the low ``width`` bits are kept.
        width: The register width, in bits. Must be non-negative.

    Returns:
        str: The zero-padded binary representation. Empty string when ``width == 0``.
    """
    if width <= 0:
        return ""
    mask = (1 << width) - 1
    return format(int(value) & mask, f"0{width}b")


def slice_positions(start: int, end: int, step: int) -> range:
    """Return the positions selected by an inclusive OpenQASM range.

    OpenQASM ranges include both endpoints, so the stop bound is pushed one past
    ``end`` in the direction of travel.

    Args:
        start: The first position of the range.
        end: The last position of the range, inclusive.
        step: The stride; negative for a descending range. Must be non-zero.

    Returns:
        range: The selected positions, in traversal order.
    """
    return range(start, end + (1 if step > 0 else -1), step)


class Qasm3Analyzer:
    """Class with utility functions for analyzing QASM3 elements"""

    @staticmethod
    def normalize_index(  # pylint: disable=too-many-arguments
        source_index: int,
        size: int,
        var_name: str,
        index_node: Any,
        dim_num: Optional[int] = None,
        qubit: bool = False,
    ) -> int:
        """Normalize an index against a register or dimension of size ``size``.

        Applies the OpenQASM 3 rule that a negative index counts from the end:
        ``-1`` is the last element, ``-size`` is the first. After normalization the
        index must satisfy ``0 <= idx < size``; otherwise the caller-facing error
        reports the *source* index as it appears in the program.

        Args:
            source_index: The index value as evaluated from source (may be negative).
            size: The size of the register or dimension being indexed.
            var_name: The register or variable name (used in error messages).
            index_node: The AST node used for span attribution on error.
            dim_num: Optional zero-based dimension number for multi-dim arrays; if
                given, the error message mentions it.
            qubit: ``True`` for a qubit register (used for message phrasing).

        Returns:
            int: The normalized non-negative index.

        Raises:
            ValidationError: If the index is out of the range
                ``[-size, size - 1]`` after normalization.
        """
        idx = source_index + size if source_index < 0 else source_index
        if 0 <= idx < size:
            return idx
        register_kind = "qubit" if qubit else "clbit"
        span = getattr(index_node, "span", None)
        if dim_num is not None:
            message = (
                f"Index {source_index} out of bounds for dimension {dim_num} "
                f"of variable '{var_name}'. Expected index in range "
                f"[-{size}, {size - 1}]"
            )
        else:
            message = (
                f"Index {source_index} out of range for register of size {size} in "
                f"{register_kind}"
            )
        raise_qasm3_error(
            message=message,
            err_type=ValidationError,
            error_node=index_node,
            span=span,
        )
        # pragma: no cover - raise_qasm3_error never returns
        raise ValidationError(message)

    @staticmethod
    def analyze_classical_indices(  # pylint: disable=too-many-locals
        indices: list[Any], var: Variable, expr_evaluator: Qasm3ExprEvaluator
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
                dim_size = var_dimensions[i]

                if index.start is not None:
                    raw_start = expr_evaluator.evaluate_expression(index.start, reqd_type=IntType)[
                        0
                    ]
                    start_id = Qasm3Analyzer.normalize_index(
                        raw_start, dim_size, var.name, index, dim_num=i
                    )
                else:
                    start_id = 0

                if index.end is not None:
                    raw_end = expr_evaluator.evaluate_expression(index.end, reqd_type=IntType)[0]
                    end_id = Qasm3Analyzer.normalize_index(
                        raw_end, dim_size, var.name, index, dim_num=i
                    )
                else:
                    end_id = dim_size - 1

                step = 1
                if index.step is not None:
                    step = expr_evaluator.evaluate_expression(index.step, reqd_type=IntType)[0]

                _validate_step(start_id, end_id, step, index)

                indices_list.append((start_id, end_id, step))

            if isinstance(index, (Identifier, IntegerLiteral, Expression)):
                raw_value = expr_evaluator.evaluate_expression(index, reqd_type=IntType)[0]
                curr_dimension = var_dimensions[i]  # type: ignore[index]
                index_value = Qasm3Analyzer.normalize_index(
                    raw_value, curr_dimension, var.name, index, dim_num=i
                )

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
    def extract_duplicate_qubit(
        qubit_list: list[IndexedIdentifier | Identifier],
    ) -> tuple[str, int] | None:
        """
        Extracts the duplicate qubit from a list of qubits.

        Args:
            qubit_list (list[IndexedIdentifier | Identifier]): The list of qubits.

        Returns:
            tuple(string, int): The duplicate qubit name and id.
        """
        qubit_set: set[tuple[str, int]] = set()
        for qubit in qubit_list:
            qubit_key = Qasm3Analyzer.extract_qubit_key(qubit)
            if qubit_key in qubit_set:
                return qubit_key
            qubit_set.add(qubit_key)
        return None

    @staticmethod
    def extract_qubit_key(qubit: IndexedIdentifier | Identifier) -> tuple[str, int]:
        """
        Extract the (register name, index) identity key for a qubit operand.

        Args:
            qubit (IndexedIdentifier | Identifier): The qubit operand.

        Returns:
            tuple(string, int): The qubit register name and index.
        """
        if isinstance(qubit, Identifier):
            # Physical qubit: name is "$n", identity is the name itself.
            return (qubit.name, int(qubit.name[1:]))
        assert isinstance(qubit, IndexedIdentifier)
        return (qubit.name.name, qubit.indices[0][0].value)  # type: ignore

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

    @staticmethod
    def condition_depends_on_measurement(condition: Expression, measurement_set: set[str]) -> bool:
        """Recursively check if the condition depends on a classical register set by measurement."""

        def _depends(expr) -> bool:
            if isinstance(expr, Identifier):
                return expr.name in measurement_set

            if isinstance(expr, IndexExpression):
                # Check if the collection being indexed is in the measurement set
                if isinstance(expr.collection, Identifier):
                    return expr.collection.name in measurement_set
                return _depends(expr.collection) or _depends(expr.index)

            if isinstance(expr, BinaryExpression):
                return _depends(expr.lhs) or _depends(expr.rhs)

            if isinstance(expr, UnaryExpression):
                return _depends(expr.expression)
            return False

        return _depends(condition)
