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
Statevector simulator for PyQASM.

"""

# pylint: disable=no-name-in-module,too-many-return-statements
# pylint: disable=too-many-locals,too-many-branches,too-many-statements
# pylint: disable=arguments-out-of-order,unused-argument

from collections import Counter
from dataclasses import dataclass

import numpy as np
from openqasm3.ast import (
    BinaryExpression,
    BinaryOperator,
    FloatLiteral,
    Identifier,
    IntegerLiteral,
    QuantumGate,
    UnaryExpression,
    UnaryOperator,
)

from pyqasm import loads
from pyqasm.accelerate.sv_sim import apply_circuit  # type: ignore[import-not-found]
from pyqasm.modules.base import QasmModule

try:
    import numba as nb  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - performance-only optional dependency

    class _NumbaCompat:
        """Fallback decorator shim when numba is not installed."""

        @staticmethod
        def njit(*args, **kwargs):  # noqa: ARG004
            if args and callable(args[0]):
                return args[0]

            def decorator(fn):
                return fn

            return decorator

    nb = _NumbaCompat()


_COMPLEX_ZERO = 0j
_PI = np.pi
_E = np.e
_T_PHASE = np.exp(1j * _PI / 4)
_TDG_PHASE = np.exp(-1j * _PI / 4)


@nb.njit(cache=True, nogil=True, fastmath=True)
def _rz_phases(theta: float) -> tuple[complex, complex]:
    """Parameterized Rz gate as diagonal phases."""
    half_theta = theta / 2
    return np.exp(-1j * half_theta), np.exp(1j * half_theta)


@nb.njit(cache=True, nogil=True, fastmath=True)
def ry(theta: float) -> np.ndarray:
    """Parameterized Ry gate."""
    c, s = np.cos(theta / 2), np.sin(theta / 2)
    mat = np.empty((2, 2), dtype=np.complex128)
    mat[0, 0] = c
    mat[0, 1] = -s
    mat[1, 0] = s
    mat[1, 1] = c
    return mat


@nb.njit(cache=True, nogil=True, fastmath=True)
def rx(theta: float) -> np.ndarray:
    """Parameterized Rx gate."""
    c, s = np.cos(theta / 2), np.sin(theta / 2)
    mat = np.empty((2, 2), dtype=np.complex128)
    mat[0, 0] = c
    mat[0, 1] = -1j * s
    mat[1, 0] = -1j * s
    mat[1, 1] = c
    return mat


def rz(theta: float) -> np.ndarray:
    """Parameterized Rz gate."""
    phase0, phase1 = _rz_phases(theta)
    return _diag_to_matrix(phase0, phase1)


@nb.njit(cache=True, nogil=True, fastmath=True)
def u3(theta: float, phi: float, lam: float) -> np.ndarray:
    """Parameterized U3 gate (generic single-qubit rotation)."""
    c, s = np.cos(theta / 2), np.sin(theta / 2)
    exp_phi = np.exp(1j * phi)
    exp_lam = np.exp(1j * lam)
    exp_philam = np.exp(1j * (phi + lam))
    mat = np.empty((2, 2), dtype=np.complex128)
    mat[0, 0] = c
    mat[0, 1] = -exp_lam * s
    mat[1, 0] = exp_phi * s
    mat[1, 1] = exp_philam * c
    return mat


@nb.njit(cache=True, nogil=True, fastmath=True)
def _diag_to_matrix(phase0: complex, phase1: complex) -> np.ndarray:
    """Convert diagonal phases to a 2x2 matrix."""
    mat = np.zeros((2, 2), dtype=np.complex128)
    mat[0, 0] = phase0
    mat[1, 1] = phase1
    return mat


@nb.njit(cache=True, nogil=True, fastmath=True)
def _is_diagonal_matrix(mat: np.ndarray, tol: float = 1e-10) -> bool:
    """Return whether a 2x2 matrix is diagonal within tolerance."""
    return (np.abs(mat[0, 1]) < tol) and (np.abs(mat[1, 0]) < tol)


@nb.njit(cache=True, nogil=True, fastmath=True)
def _diagonal_phases_from_matrix(mat: np.ndarray) -> tuple[complex, complex]:
    """Extract diagonal phases from a diagonal 2x2 matrix."""
    return mat[0, 0], mat[1, 1]


PARAMETERIZED_GATES = {
    "rz": rz,
    "ry": ry,
    "rx": rx,
    "u3": u3,
}

_CONST_X = np.array([[0, 1], [1, 0]], dtype=np.complex128)
_CONST_Y = np.array([[0, -1j], [1j, 0]], dtype=np.complex128)
_CONST_Z = np.array([[1, 0], [0, -1]], dtype=np.complex128)
_CONST_H = np.array([[1, 1], [1, -1]], dtype=np.complex128) / np.sqrt(2)
_CONST_ID = np.eye(2, dtype=np.complex128)
_CONST_S = np.array([[1, 0], [0, 1j]], dtype=np.complex128)
_CONST_T = np.array([[1, 0], [0, _T_PHASE]], dtype=np.complex128)
_CONST_SDG = np.array([[1, 0], [0, -1j]], dtype=np.complex128)
_CONST_TDG = np.array([[1, 0], [0, _TDG_PHASE]], dtype=np.complex128)
_CONST_SWAP = np.array(
    [[1, 0, 0, 0], [0, 0, 1, 0], [0, 1, 0, 0], [0, 0, 0, 1]], dtype=np.complex128
)

NON_PARAMETERIZED_GATES: dict[str, np.ndarray] = {
    "x": _CONST_X,
    "y": _CONST_Y,
    "z": _CONST_Z,
    "h": _CONST_H,
    "id": _CONST_ID,
    "s": _CONST_S,
    "t": _CONST_T,
    "sdg": _CONST_SDG,
    "tdg": _CONST_TDG,
    "swap": _CONST_SWAP,
}

# Fast-path single-qubit gate properties.  Diagonal gates are kept as phase
# pairs while fusing so they can flush directly to the diagonal Cython kernel
# instead of materializing a 2x2 matrix.
NON_PARAMETERIZED_GATE_PROPS: dict[str, tuple[bool, complex, complex, np.ndarray | None]] = {
    "x": (False, _COMPLEX_ZERO, _COMPLEX_ZERO, _CONST_X),
    "y": (False, _COMPLEX_ZERO, _COMPLEX_ZERO, _CONST_Y),
    "z": (True, 1.0 + _COMPLEX_ZERO, -1.0 + _COMPLEX_ZERO, None),
    "h": (False, _COMPLEX_ZERO, _COMPLEX_ZERO, _CONST_H),
    "id": (True, 1.0 + _COMPLEX_ZERO, 1.0 + _COMPLEX_ZERO, None),
    "s": (True, 1.0 + _COMPLEX_ZERO, 1j, None),
    "t": (True, 1.0 + _COMPLEX_ZERO, _T_PHASE, None),
    "sdg": (True, 1.0 + _COMPLEX_ZERO, -1j, None),
    "tdg": (True, 1.0 + _COMPLEX_ZERO, _TDG_PHASE, None),
}

CONTROLLED_GATE_SUB_UNITARIES: dict[str, np.ndarray] = {
    "cx": _CONST_X,
    "cy": _CONST_Y,
    "cz": _CONST_Z,
}

# Pre-flatten non-parameterized gates for Cython (contiguous 1D arrays)
GATE_CACHE: dict[str, np.ndarray] = {}
for _name, _mat in NON_PARAMETERIZED_GATES.items():
    GATE_CACHE[_name] = np.ascontiguousarray(_mat.ravel())
for _name, _mat in CONTROLLED_GATE_SUB_UNITARIES.items():
    GATE_CACHE[_name] = np.ascontiguousarray(_mat.ravel())

# Diagonal gate phases: gate_name -> (phase0, phase1) for diag(phase0, phase1)
DIAGONAL_PHASES: dict[str, tuple[complex, complex]] = {
    "z": (1.0, -1.0),
    "s": (1.0, 1j),
    "t": (1.0, _T_PHASE),
    "sdg": (1.0, -1j),
    "tdg": (1.0, _TDG_PHASE),
    "id": (1.0, 1.0),
}

# Controlled diagonal phases: gate_name -> phase (applied when control=1 AND target=1)
CONTROLLED_DIAGONAL_PHASES: dict[str, complex] = {
    "cz": -1.0,
}

# Integer opcodes for preprocessed instructions
_OP_SINGLE = 0
_OP_CONTROLLED = 1
_OP_DIAGONAL = 2
_OP_CTRL_DIAGONAL = 3
_OP_TWO_QUBIT = 4


def _try_eval_expression(expr) -> float | None:
    """Try to evaluate an AST expression to a float value."""
    if isinstance(expr, (IntegerLiteral, FloatLiteral)):
        return float(expr.value)
    if isinstance(expr, Identifier):
        if expr.name == "pi":
            return _PI
        if expr.name == "tau":
            return 2 * _PI
        if expr.name == "euler":
            return _E
        return None
    if isinstance(expr, BinaryExpression):
        lhs = _try_eval_expression(expr.lhs)
        rhs = _try_eval_expression(expr.rhs)
        if lhs is None or rhs is None:
            return None
        if expr.op is BinaryOperator["+"]:
            return lhs + rhs
        if expr.op is BinaryOperator["-"]:
            return lhs - rhs
        if expr.op is BinaryOperator["*"]:
            return lhs * rhs
        if expr.op is BinaryOperator["/"]:
            return lhs / rhs
        if expr.op is BinaryOperator["**"]:
            return lhs**rhs
        return None
    if isinstance(expr, UnaryExpression):
        operand = _try_eval_expression(expr.expression)
        if operand is None:
            return None
        if expr.op is UnaryOperator["-"]:
            return -operand
        return None
    return None


def _extract_params(statement):
    """Extract float parameters from a QuantumGate's arguments."""
    params = []
    for arg in statement.arguments:
        val = _try_eval_expression(arg)
        if val is not None:
            params.append(val)
    return params


def _preprocess(program, num_qubits):
    """Walk the AST once, producing packed numpy arrays with inline gate fusion.

    This keeps the existing no-cache semantics: every call preprocesses its
    input program.  The speedup comes from avoiding Python list growth,
    preserving diagonal gates as phase pairs while fusing, and using optional
    numba-compiled helpers for small matrix/phase constructors.
    """
    statements = (
        program._unrolled_ast.statements
        if len(program._unrolled_ast.statements) > 0
        else program.original_program.statements
    )

    # Conservative bound: pending one-qubit flushes plus SWAP expansion can
    # emit more instructions than source statements.  The bound is deliberately
    # simple and over-allocates a little to avoid dynamic list growth.
    max_instructions = max(1, len(statements) * 4 + num_qubits)
    opcodes = np.empty(max_instructions, dtype=np.int32)
    targets = np.empty(max_instructions, dtype=np.int32)
    controls = np.empty(max_instructions, dtype=np.int32)
    gate_params = np.empty(max_instructions * 4, dtype=np.complex128)
    diag_phases = np.empty(max_instructions * 2, dtype=np.complex128)
    two_qubit_offsets = np.empty(max_instructions, dtype=np.int32)
    two_qubit_gates = np.empty(max_instructions * 16, dtype=np.complex128)

    zero4 = np.zeros(4, dtype=np.complex128)
    zero2 = np.zeros(2, dtype=np.complex128)
    instruction_idx = 0
    tq_offset = 0

    # target -> (is_diagonal, phase0, phase1, matrix)
    pending: dict[int, tuple[bool, complex, complex, np.ndarray | None]] = {}

    def _write_single(target: int, mat: np.ndarray):
        nonlocal instruction_idx
        opcodes[instruction_idx] = _OP_SINGLE
        targets[instruction_idx] = target
        controls[instruction_idx] = -1
        gate_params[instruction_idx * 4 : instruction_idx * 4 + 4] = mat.ravel()
        diag_phases[instruction_idx * 2 : instruction_idx * 2 + 2] = zero2
        two_qubit_offsets[instruction_idx] = -1
        instruction_idx += 1

    def _write_diagonal(target: int, phase0: complex, phase1: complex):
        nonlocal instruction_idx
        opcodes[instruction_idx] = _OP_DIAGONAL
        targets[instruction_idx] = target
        controls[instruction_idx] = -1
        gate_params[instruction_idx * 4 : instruction_idx * 4 + 4] = zero4
        diag_phases[instruction_idx * 2 : instruction_idx * 2 + 2] = (phase0, phase1)
        two_qubit_offsets[instruction_idx] = -1
        instruction_idx += 1

    def _write_controlled(control: int, target: int, flat: np.ndarray):
        nonlocal instruction_idx
        opcodes[instruction_idx] = _OP_CONTROLLED
        targets[instruction_idx] = target
        controls[instruction_idx] = control
        gate_params[instruction_idx * 4 : instruction_idx * 4 + 4] = flat
        diag_phases[instruction_idx * 2 : instruction_idx * 2 + 2] = zero2
        two_qubit_offsets[instruction_idx] = -1
        instruction_idx += 1

    def _write_controlled_diagonal(control: int, target: int, phase: complex):
        nonlocal instruction_idx
        opcodes[instruction_idx] = _OP_CTRL_DIAGONAL
        targets[instruction_idx] = target
        controls[instruction_idx] = control
        gate_params[instruction_idx * 4 : instruction_idx * 4 + 4] = zero4
        diag_phases[instruction_idx * 2 : instruction_idx * 2 + 2] = (phase, 0j)
        two_qubit_offsets[instruction_idx] = -1
        instruction_idx += 1

    def _write_two_qubit(control: int, target: int, flat: np.ndarray):
        nonlocal instruction_idx, tq_offset
        opcodes[instruction_idx] = _OP_TWO_QUBIT
        targets[instruction_idx] = target
        controls[instruction_idx] = control
        gate_params[instruction_idx * 4 : instruction_idx * 4 + 4] = zero4
        diag_phases[instruction_idx * 2 : instruction_idx * 2 + 2] = zero2
        two_qubit_offsets[instruction_idx] = tq_offset
        two_qubit_gates[tq_offset : tq_offset + 16] = flat
        tq_offset += 16
        instruction_idx += 1

    def _flush_pending(target: int):
        if target not in pending:
            return
        is_diagonal, phase0, phase1, mat = pending.pop(target)

        if is_diagonal and (np.abs(phase0 - 1.0) < 1e-10) and (np.abs(phase1 - 1.0) < 1e-10):
            return
        if not is_diagonal and mat is not None and _is_diagonal_matrix(mat):
            is_diagonal = True
            phase0, phase1 = _diagonal_phases_from_matrix(mat)
            mat = None

        if is_diagonal:
            _write_diagonal(target, phase0, phase1)
        else:
            if mat is None:
                mat = _diag_to_matrix(phase0, phase1)
            _write_single(target, mat)

    def _flush_all():
        for target in list(pending.keys()):
            _flush_pending(target)

    def _accumulate(
        target: int,
        new_is_diagonal: bool,
        new_phase0: complex,
        new_phase1: complex,
        new_mat: np.ndarray | None,
    ):
        if target not in pending:
            pending[target] = (new_is_diagonal, new_phase0, new_phase1, new_mat)
            return

        current_is_diagonal, current_phase0, current_phase1, current_mat = pending[target]
        if current_is_diagonal and new_is_diagonal:
            pending[target] = (
                True,
                new_phase0 * current_phase0,
                new_phase1 * current_phase1,
                None,
            )
            return

        current_matrix = (
            _diag_to_matrix(current_phase0, current_phase1) if current_is_diagonal else current_mat
        )
        new_matrix = _diag_to_matrix(new_phase0, new_phase1) if new_is_diagonal else new_mat
        if current_matrix is None or new_matrix is None:
            raise ValueError("Invalid pending gate fusion state.")
        fused = new_matrix @ current_matrix
        if _is_diagonal_matrix(fused):
            phase0, phase1 = _diagonal_phases_from_matrix(fused)
            pending[target] = (True, phase0, phase1, None)
        else:
            pending[target] = (False, _COMPLEX_ZERO, _COMPLEX_ZERO, fused)

    for statement in statements:
        if not isinstance(statement, QuantumGate):
            continue

        gate_name = statement.name.name
        params = _extract_params(statement)

        if len(statement.qubits) == 1:
            target = statement.qubits[0].indices[0][0].value

            if gate_name in NON_PARAMETERIZED_GATE_PROPS:
                is_diagonal, phase0, phase1, mat = NON_PARAMETERIZED_GATE_PROPS[gate_name]
                _accumulate(target, is_diagonal, phase0, phase1, mat)
            elif gate_name == "rz" and len(params) == 1:
                phase0, phase1 = _rz_phases(params[0])
                _accumulate(target, True, phase0, phase1, None)
            elif gate_name in PARAMETERIZED_GATES:
                gate_fn = PARAMETERIZED_GATES[gate_name]
                required_params = 3 if gate_name == "u3" else 1
                if len(params) != required_params:
                    raise ValueError(f"Gate {gate_name} requires {required_params} parameter(s).")
                mat = gate_fn(*params)
                _accumulate(target, False, _COMPLEX_ZERO, _COMPLEX_ZERO, mat)
            else:
                raise ValueError(
                    f"Gate '{gate_name}' not supported by simulator. "
                    f"Call module.unroll() first."
                )

        elif len(statement.qubits) == 2:
            target = statement.qubits[1].indices[0][0].value
            control = statement.qubits[0].indices[0][0].value

            # Flush pending gates only when they do not commute with the
            # incoming two-qubit gate.  Diagonal one-qubit gates commute with
            # diagonal two-qubit gates (CZ/CRZ), so they can remain fused until
            # a later non-diagonal interaction or the final flush.
            for qubit in (control, target):
                if qubit not in pending:
                    continue
                is_diagonal, _, _, _ = pending[qubit]
                if (not is_diagonal) or gate_name not in {"cz", "crz"}:
                    _flush_pending(qubit)

            if gate_name == "swap":
                # Decompose SWAP into three controlled-X instructions.  This
                # stays on the optimized controlled-gate kernel and avoids the
                # generic 4x4 two-qubit path for this common gate.
                flat = GATE_CACHE["cx"]
                _write_controlled(control, target, flat)
                _write_controlled(target, control, flat)
                _write_controlled(control, target, flat)
            elif gate_name in CONTROLLED_DIAGONAL_PHASES:
                phase = CONTROLLED_DIAGONAL_PHASES[gate_name]
                _write_controlled_diagonal(control, target, phase)
            elif gate_name == "crz" and len(params) == 1:
                theta = params[0]
                _, phase_at_11 = _rz_phases(theta)
                _write_controlled_diagonal(control, target, phase_at_11)
            elif gate_name in CONTROLLED_GATE_SUB_UNITARIES:
                flat = GATE_CACHE[gate_name]
                _write_controlled(control, target, flat)
            else:
                raise ValueError(
                    f"Gate '{gate_name}' not supported by simulator. "
                    f"Call module.unroll() first."
                )

    # Flush remaining pending single-qubit gates
    _flush_all()

    n = instruction_idx
    if n == 0:
        return n, None, None, None, None, None, None, None

    if tq_offset > 0:
        two_qubit_gates_trimmed = np.ascontiguousarray(two_qubit_gates[:tq_offset])
    else:
        two_qubit_gates_trimmed = np.zeros(1, dtype=np.complex128)

    return (
        n,
        opcodes[:n],
        targets[:n],
        controls[:n],
        np.ascontiguousarray(gate_params[: n * 4]),
        np.ascontiguousarray(diag_phases[: n * 2]),
        two_qubit_offsets[:n],
        two_qubit_gates_trimmed,
    )


@dataclass(frozen=True)
class SimulatorResult:
    """Class to store the result of a statevector simulation."""

    probabilities: np.ndarray
    measurement_counts: Counter[str]
    final_statevector: np.ndarray


class Simulator:
    """
    Statevector simulator

    """

    def __init__(self, seed: None | int = None):
        """
        Initialize the statevector simulator.

        Parameters:
            seed (None | int): A seed to initialize the `np.random.BitGenerator`.
                If None, then fresh, unpredictable entropy will be pulled from
                the OS using `np.random.SeedSequence`.
        """
        self._rng = np.random.default_rng(seed)

    def run(self, program: QasmModule | str, shots: int = 1) -> SimulatorResult:
        """Run the statevector simulator.

        For QasmModule input, the module is used as-is. Call module.unroll()
        and module.remove_idle_qubits() beforehand if needed.

        For string input, loads/unrolls/removes idle qubits automatically.

        Args:
            program (QasmModule | str): The program to simulate.
            shots (int): The number of shots to simulate. Defaults to 1.

        Returns:
            SimulatorResult: The result of the simulation.

        Raises:
            ValueError: If shots is less than 0, or if the program contains
                an unsupported gate or invalid syntax.
        """
        if isinstance(program, str):
            program = loads(program)
            program.unroll()
            program.remove_idle_qubits()

        num_qubits = program.num_qubits
        sv = np.zeros(2**num_qubits, dtype=np.complex128)
        sv[0] = 1.0

        n, opcodes, targets, controls, gate_params, diag_phases, tq_offsets, tq_gates = _preprocess(
            program, num_qubits
        )

        if n > 0:
            apply_circuit(
                sv,
                num_qubits,
                opcodes,
                targets,
                controls,
                gate_params,
                diag_phases,
                tq_offsets,
                tq_gates,
                n,
            )

        if shots < 0:
            raise ValueError("Shots must be greater than or equal to 0.")

        probabilities = np.abs(sv) ** 2
        samples = self._rng.choice(len(probabilities), size=shots, p=probabilities)
        counts = Counter(format(s, f"0{num_qubits}b")[::-1] for s in samples)

        return SimulatorResult(probabilities, counts, sv)
