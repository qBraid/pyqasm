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

"""Normalize conditional branches and print OpenQASM 2.0 programs."""

import io
from dataclasses import dataclass
from typing import Any, Sequence

import openqasm3.ast as qasm3_ast
from openqasm3.printer import PrinterState

from pyqasm.exceptions import ValidationError
from pyqasm.modules.qasm3 import Qasm3Printer


@dataclass(frozen=True)
class _FlattenedBranch:
    """A whole-register comparison and the statements it guards."""

    register: str
    value: int
    body: list[qasm3_ast.Statement]


def _qasm3_repr(node: qasm3_ast.QASMNode) -> str:
    """Render a node with the stock QASM 3 printer, for use in error messages."""
    out = io.StringIO()
    Qasm3Printer(out).visit(node)
    return out.getvalue().strip()


def _classical_register_sizes(
    statements: Sequence[qasm3_ast.Statement | qasm3_ast.Pragma],
) -> dict[str, int]:
    """Map each classical register declared in the statements to its declared size."""
    sizes = {}
    for statement in statements:
        if isinstance(statement, qasm3_ast.ClassicalDeclaration) and isinstance(
            statement.type, qasm3_ast.BitType
        ):
            size = statement.type.size
            if size is None:
                sizes[statement.identifier.name] = 1
            elif isinstance(size, qasm3_ast.IntegerLiteral):
                sizes[statement.identifier.name] = size.value
    return sizes


def _quantum_register_sizes(
    statements: Sequence[qasm3_ast.Statement | qasm3_ast.Pragma],
) -> dict[str, int]:
    """Map each quantum register declared in the statements to its declared size."""
    sizes = {}
    for statement in statements:
        if isinstance(statement, qasm3_ast.QubitDeclaration):
            size = statement.size
            sizes[statement.qubit.name] = (
                size.value if isinstance(size, qasm3_ast.IntegerLiteral) else 1
            )
    return sizes


def _single_index(operand: qasm3_ast.QASMNode | None) -> tuple[str, int] | None:
    """Decompose ``reg[i]`` into ``(reg, i)``, or ``None`` for any other operand shape."""
    if (
        isinstance(operand, qasm3_ast.IndexedIdentifier)
        and len(operand.indices) == 1
        and isinstance(operand.indices[0], list)
        and len(operand.indices[0]) == 1
        and isinstance(operand.indices[0][0], qasm3_ast.IntegerLiteral)
    ):
        return operand.name.name, operand.indices[0][0].value
    return None


def _collapse_broadcast_measurement(
    body: list[qasm3_ast.Statement], creg_sizes: dict[str, int], qreg_sizes: dict[str, int]
) -> qasm3_ast.QuantumMeasurementStatement | None:
    """Rebuild ``measure qreg -> creg`` from the per-bit statements unrolling expanded it into.

    A register-level measurement is one QASM 2.0 statement, so a branch guarding it is
    expressible as written. Emitting the expansion instead would need one ``if`` per bit,
    re-testing the register the body writes; see the hazard check in :func:`_flatten_branch`.
    Returns ``None`` unless the body is exactly a full, in-order broadcast.
    """
    pairs = []
    for statement in body:
        if not isinstance(statement, qasm3_ast.QuantumMeasurementStatement):
            return None
        qubit = _single_index(statement.measure.qubit)
        target = _single_index(statement.target)
        if qubit is None or target is None:
            return None
        pairs.append((qubit, target))

    (qreg, _), (creg, _) = pairs[0]
    size = len(pairs)
    if qreg_sizes.get(qreg) != size or creg_sizes.get(creg) != size:
        return None
    if pairs != [((qreg, index), (creg, index)) for index in range(size)]:
        return None

    return qasm3_ast.QuantumMeasurementStatement(
        measure=qasm3_ast.QuantumMeasurement(qubit=qasm3_ast.Identifier(name=qreg)),
        target=qasm3_ast.Identifier(name=creg),
    )


def _parse_branch_condition(condition: qasm3_ast.Expression) -> tuple[str, int | None, int]:
    """Decompose a branch condition into ``(register name, bit index, value)``.

    ``bit index`` is ``None`` for a whole-register comparison (``c == 2``) and an
    integer for the single-bit comparisons that unrolling produces (``c[0] == true``).
    """
    if (
        not isinstance(condition, qasm3_ast.BinaryExpression)
        or condition.op != qasm3_ast.BinaryOperator["=="]
    ):
        operator = (
            f", which uses '{condition.op.name}',"
            if isinstance(condition, qasm3_ast.BinaryExpression)
            and condition.op != qasm3_ast.BinaryOperator["=="]
            else ""
        )
        raise ValidationError(
            f"Branch condition '{_qasm3_repr(condition)}'{operator} is not supported in QASM 2.0, "
            "which only allows 'if (creg == int)'"
        )

    lhs, rhs = condition.lhs, condition.rhs
    if not isinstance(rhs, (qasm3_ast.IntegerLiteral, qasm3_ast.BooleanLiteral)):
        raise ValidationError(
            f"Branch condition '{_qasm3_repr(condition)}' is not supported in QASM 2.0, "
            "which only allows comparison against an integer literal"
        )
    value = int(rhs.value)

    if isinstance(lhs, qasm3_ast.Identifier):
        return lhs.name, None, value

    if (
        isinstance(lhs, qasm3_ast.IndexExpression)
        and isinstance(lhs.collection, qasm3_ast.Identifier)
        and isinstance(lhs.index, list)
        and len(lhs.index) == 1
        and isinstance(lhs.index[0], qasm3_ast.IntegerLiteral)
    ):
        return lhs.collection.name, lhs.index[0].value, value

    raise ValidationError(
        f"Branch condition '{_qasm3_repr(condition)}' is not supported in QASM 2.0, "
        "which only allows 'if (creg == int)'"
    )


def _add_chain_constraint(
    reg_name: str,
    bit_index: int | None,
    value: int,
    reg_value: int | None,
    bit_values: dict[int, bool],
) -> int | None:
    """Fold one link of a branch chain into the constraints collected so far.

    Every link's constraint has to survive into the single comparison QASM 2 allows,
    so a link that contradicts or duplicates an earlier one has nowhere to go and must
    not be quietly dropped by the collapse in :func:`_flatten_branch`.
    """
    if bit_index is None:
        if reg_value is not None:
            raise ValidationError(
                f"Branch on '{reg_name}' nests another whole-register comparison, "
                "which is not supported in QASM 2.0"
            )
        return value

    if bit_index in bit_values:
        raise ValidationError(
            f"Branch on '{reg_name}' tests bit {bit_index} more than once, "
            "which is not supported in QASM 2.0"
        )
    if value not in (0, 1):
        raise ValidationError(
            f"Branch on '{reg_name}' compares bit {bit_index} against {value}; "
            "a single bit can only be compared against 0 or 1"
        )
    bit_values[bit_index] = bool(value)
    return reg_value


def _flatten_branch(
    statement: qasm3_ast.BranchingStatement,
    creg_sizes: dict[str, int],
    qreg_sizes: dict[str, int],
) -> _FlattenedBranch:
    """Reduce a branching statement to the ``if (creg == int) <statement>`` form of QASM 2.

    Unrolling rewrites ``if (c == 2)`` into a chain of nested single-bit tests, one per
    bit of ``c``; QASM 2 has no bit indexing in conditions and no nested ``if``, so the
    chain is walked back into the whole-register comparison it came from.
    """
    bit_values: dict[int, bool] = {}
    body: list[qasm3_ast.Statement] = []
    reg_name = None
    reg_value = None
    current = statement

    while True:
        if current.else_block:
            raise ValidationError(
                "'else' blocks are not supported in QASM 2.0, which only allows "
                "'if (creg == int) <statement>'"
            )

        name, bit_index, value = _parse_branch_condition(current.condition)
        if reg_name is not None and name != reg_name:
            raise ValidationError(
                f"Nested branches on different registers ('{reg_name}' and '{name}') are not "
                "supported in QASM 2.0, which has no nested 'if' statements"
            )
        reg_name = name
        reg_value = _add_chain_constraint(reg_name, bit_index, value, reg_value, bit_values)

        body = current.if_block
        # unrolling nests one branch per bit, so keep walking while the body is
        # nothing but the next branch in that chain
        if len(body) == 1 and isinstance(body[0], qasm3_ast.BranchingStatement):
            current = body[0]
            continue
        break

    assert reg_name is not None
    if any(isinstance(stmt, qasm3_ast.BranchingStatement) for stmt in body):
        raise ValidationError(
            f"Nested 'if' statements inside the body of a branch on '{reg_name}' are not "
            "supported in QASM 2.0"
        )

    if bit_values:
        if reg_value is not None:
            raise ValidationError(
                f"Branch on '{reg_name}' mixes whole-register and single-bit comparisons, "
                "which is not supported in QASM 2.0"
            )
        size = creg_sizes.get(reg_name)
        if size is None:
            raise ValidationError(
                f"Missing declaration for classical register '{reg_name}' used in a branch"
            )
        if set(bit_values) != set(range(size)):
            missing = sorted(set(range(size)) - set(bit_values))
            raise ValidationError(
                f"Branch on '{reg_name}' constrains only bits {sorted(bit_values)} of a "
                f"{size}-bit register (bits {missing} are unconstrained); QASM 2.0 can only "
                "compare a classical register against an integer"
            )
        # c[0] is the least significant bit of c
        reg_value = sum(1 << index for index, set_ in bit_values.items() if set_)

    assert reg_value is not None

    if len(body) > 1:
        # a register-level measurement survives unrolling as one statement per bit; put it
        # back together so the branch is emitted as the single statement it was written as
        collapsed = _collapse_broadcast_measurement(body, creg_sizes, qreg_sizes)
        if collapsed is not None:
            body = [collapsed]

    # a multi-statement body is emitted as one guarded statement each, which re-tests the
    # register before every statement; that is only faithful while the body leaves it alone
    if len(body) > 1 and any(_writes_to_register(stmt, reg_name) for stmt in body):
        raise ValidationError(
            f"Branch on '{reg_name}' has a body of {len(body)} statements, at least one of "
            f"which writes to '{reg_name}' -- the register the branch tests. QASM 2.0 guards a "
            "single statement per 'if', so emitting one guard per statement would re-evaluate "
            "the condition mid-body and change the program's meaning"
        )

    return _FlattenedBranch(reg_name, reg_value, body)


def _writes_to_register(statement: qasm3_ast.Statement, reg_name: str) -> bool:
    """Whether ``statement`` assigns to any bit of the classical register ``reg_name``."""
    if isinstance(statement, qasm3_ast.QuantumMeasurementStatement):
        target = statement.target
        if isinstance(target, qasm3_ast.IndexedIdentifier):
            return target.name.name == reg_name
        if isinstance(target, qasm3_ast.Identifier):
            return target.name == reg_name
    return False


def validate_branch(
    statement: qasm3_ast.BranchingStatement,
    declarations: Sequence[qasm3_ast.Statement | qasm3_ast.Pragma],
) -> None:
    """Reject branch shapes that the QASM 2 printer cannot express.

    Validation and printing use the same normalization, including after module
    transformations have replaced a register comparison with per-bit tests.
    """
    _flatten_branch(
        statement,
        _classical_register_sizes(declarations),
        _quantum_register_sizes(declarations),
    )


class Qasm2Printer(Qasm3Printer):
    """``openqasm3`` printer that emits OpenQASM 2.0 branching syntax.

    OpenQASM 2.0 has no braced blocks: a conditional is ``if (creg == int) <statement>``
    with exactly one statement and no ``else``. The base printer always emits the QASM 3
    braced form, which downstream QASM 2 parsers reject.
    """

    def __init__(
        self,
        *args: Any,
        creg_sizes: dict[str, int] | None = None,
        qreg_sizes: dict[str, int] | None = None,
        statements: Sequence[qasm3_ast.Statement | qasm3_ast.Pragma] = (),
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self._creg_sizes = creg_sizes or _classical_register_sizes(statements)
        self._qreg_sizes = qreg_sizes or _quantum_register_sizes(statements)

    def visit_BranchingStatement(  # pylint: disable=invalid-name
        self, node: qasm3_ast.BranchingStatement, context: PrinterState
    ) -> None:
        branch = _flatten_branch(node, self._creg_sizes, self._qreg_sizes)

        # a single QASM 2 conditional guards a single statement, so a body that
        # unrolled into several statements becomes one guarded statement each
        for statement in branch.body:
            # `_start_line` and `skip_next_indent` are openqasm3 printer internals, so an
            # upstream change could alter emission silently; the brace assertions in
            # tests/qasm2/test_branching.py are what turn that into a test failure
            self._start_line(context)
            self.stream.write(f"if ({branch.register} == {branch.value}) ")
            context.skip_next_indent = True
            self.visit(statement, context)
