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
from pyqasm.accelerate.sv_sim import apply_circuit
from pyqasm.modules.base import QasmModule


def rz(theta: float) -> np.ndarray:
    """Parameterized Rz gate."""
    return np.array([[np.exp(-1j * theta / 2), 0], [0, np.exp(1j * theta / 2)]], dtype=complex)


def ry(theta: float) -> np.ndarray:
    """Parameterized Ry gate."""
    return np.array(
        [[np.cos(theta / 2), -np.sin(theta / 2)], [np.sin(theta / 2), np.cos(theta / 2)]],
        dtype=complex,
    )


def rx(theta: float) -> np.ndarray:
    """Parameterized Rx gate."""
    return np.array(
        [
            [np.cos(theta / 2), -1j * np.sin(theta / 2)],
            [-1j * np.sin(theta / 2), np.cos(theta / 2)],
        ],
        dtype=complex,
    )


def u3(theta: float, phi: float, lam: float) -> np.ndarray:
    """Parameterized U3 gate (generic single-qubit rotation)."""
    return np.array(
        [
            [np.cos(theta / 2), -np.exp(1j * lam) * np.sin(theta / 2)],
            [np.exp(1j * phi) * np.sin(theta / 2), np.exp(1j * (phi + lam)) * np.cos(theta / 2)],
        ],
        dtype=complex,
    )


PARAMETERIZED_GATES = {
    "rz": rz,
    "ry": ry,
    "rx": rx,
    "u3": u3,
}

NON_PARAMETERIZED_GATES: dict[str, np.ndarray] = {
    "x": np.array([[0, 1], [1, 0]], dtype=complex),
    "y": np.array([[0, -1j], [1j, 0]], dtype=complex),
    "z": np.array([[1, 0], [0, -1]], dtype=complex),
    "h": np.array([[1, 1], [1, -1]], dtype=complex) / np.sqrt(2),
    "id": np.array([[1, 0], [0, 1]], dtype=complex),
    "s": np.array([[1, 0], [0, 1j]], dtype=complex),
    "t": np.array([[1, 0], [0, np.exp(1j * np.pi / 4)]], dtype=complex),
    "sdg": np.array([[1, 0], [0, -1j]], dtype=complex),
    "tdg": np.array([[1, 0], [0, np.exp(-1j * np.pi / 4)]], dtype=complex),
    "swap": np.array([[1, 0, 0, 0], [0, 0, 1, 0], [0, 1, 0, 0], [0, 0, 0, 1]], dtype=complex),
}

CONTROLLED_GATE_SUB_UNITARIES: dict[str, np.ndarray] = {
    "cx": np.array([[0, 1], [1, 0]], dtype=complex),
    "cy": np.array([[0, -1j], [1j, 0]], dtype=complex),
    "cz": np.array([[1, 0], [0, -1]], dtype=complex),
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
    "t": (1.0, np.exp(1j * np.pi / 4)),
    "sdg": (1.0, -1j),
    "tdg": (1.0, np.exp(-1j * np.pi / 4)),
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

# Binary/unary operator maps for expression evaluation
_BINARY_OPS = {
    BinaryOperator["+"]: lambda a, b: a + b,
    BinaryOperator["-"]: lambda a, b: a - b,
    BinaryOperator["*"]: lambda a, b: a * b,
    BinaryOperator["/"]: lambda a, b: a / b,
    BinaryOperator["**"]: lambda a, b: a**b,
}

_UNARY_OPS = {
    UnaryOperator["-"]: lambda a: -a,
}


def _try_eval_expression(expr) -> float | None:
    """Try to evaluate an AST expression to a float value."""
    if isinstance(expr, (IntegerLiteral, FloatLiteral)):
        return float(expr.value)
    if isinstance(expr, Identifier):
        if expr.name == "pi":
            return np.pi
        if expr.name == "tau":
            return 2 * np.pi
        if expr.name == "euler":
            return np.e
        return None
    if isinstance(expr, BinaryExpression):
        lhs = _try_eval_expression(expr.lhs)
        rhs = _try_eval_expression(expr.rhs)
        if lhs is None or rhs is None:
            return None
        op_fn = _BINARY_OPS.get(expr.op)
        if op_fn is not None:
            return op_fn(lhs, rhs)
        return None
    if isinstance(expr, UnaryExpression):
        operand = _try_eval_expression(expr.expression)
        if operand is None:
            return None
        op_fn = _UNARY_OPS.get(expr.op)
        if op_fn is not None:
            return op_fn(operand)
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
    """Walk the AST once, producing packed numpy arrays with inline gate fusion."""
    opcodes_list = []
    targets_list = []
    controls_list = []
    gate_params_list = []  # 4 complex per instruction (2x2 gate entries)
    diag_phases_list = []  # 2 complex per instruction (phase0, phase1)
    two_qubit_gates_list = []  # variable: 16 entries per two-qubit gate
    two_qubit_offsets_list = []  # offset into two_qubit_gates per instruction

    _zero4 = [0j, 0j, 0j, 0j]
    _zero2 = [0j, 0j]
    tq_offset = 0

    # Fusion state: pending accumulated 2x2 matrix per target qubit
    pending = {}  # target -> np.ndarray (2x2)

    def _flush_pending(target):
        if target not in pending:
            return
        mat = pending.pop(target)
        opcodes_list.append(_OP_SINGLE)
        targets_list.append(target)
        controls_list.append(-1)
        gate_params_list.extend(mat.ravel())
        diag_phases_list.extend(_zero2)
        two_qubit_offsets_list.append(-1)

    def _flush_all():
        for t in list(pending.keys()):
            _flush_pending(t)

    def _accumulate(target, mat_2x2):
        if target in pending:
            pending[target] = mat_2x2 @ pending[target]
        else:
            pending[target] = mat_2x2

    # Choose statement source: unrolled AST if available, else original program
    statements = (
        program._unrolled_ast.statements
        if len(program._unrolled_ast.statements) > 0
        else program.original_program.statements
    )

    for statement in statements:
        if not isinstance(statement, QuantumGate):
            continue

        gate_name = statement.name.name
        params = _extract_params(statement)

        if len(statement.qubits) == 1:
            target = statement.qubits[0].indices[0][0].value

            if gate_name in DIAGONAL_PHASES:
                phase0, phase1 = DIAGONAL_PHASES[gate_name]
                mat = np.array([[phase0, 0], [0, phase1]], dtype=np.complex128)
                _accumulate(target, mat)
            elif gate_name == "rz" and len(params) == 1:
                theta = params[0]
                phase0 = np.exp(-1j * theta / 2)
                phase1 = np.exp(1j * theta / 2)
                mat = np.array([[phase0, 0], [0, phase1]], dtype=np.complex128)
                _accumulate(target, mat)
            elif gate_name in NON_PARAMETERIZED_GATES:
                mat = NON_PARAMETERIZED_GATES[gate_name]
                _accumulate(target, mat)
            elif gate_name in PARAMETERIZED_GATES:
                gate_fn = PARAMETERIZED_GATES[gate_name]
                required_params = gate_fn.__code__.co_argcount
                if len(params) != required_params:
                    raise ValueError(f"Gate {gate_name} requires {required_params} parameter(s).")
                mat = gate_fn(*params)
                _accumulate(target, mat)
            else:
                raise ValueError(
                    f"Gate '{gate_name}' not supported by simulator. "
                    f"Call module.unroll() first."
                )

        elif len(statement.qubits) == 2:
            target = statement.qubits[1].indices[0][0].value
            control = statement.qubits[0].indices[0][0].value

            # Flush any pending single-qubit gates on affected qubits
            _flush_pending(target)
            _flush_pending(control)

            if gate_name == "swap":
                flat = GATE_CACHE["swap"]
                opcodes_list.append(_OP_TWO_QUBIT)
                targets_list.append(target)
                controls_list.append(control)
                gate_params_list.extend(_zero4)
                diag_phases_list.extend(_zero2)
                two_qubit_offsets_list.append(tq_offset)
                two_qubit_gates_list.extend(flat)
                tq_offset += 16
            elif gate_name in CONTROLLED_DIAGONAL_PHASES:
                phase = CONTROLLED_DIAGONAL_PHASES[gate_name]
                opcodes_list.append(_OP_CTRL_DIAGONAL)
                targets_list.append(target)
                controls_list.append(control)
                gate_params_list.extend(_zero4)
                diag_phases_list.extend([phase, 0j])
                two_qubit_offsets_list.append(-1)
            elif gate_name == "crz" and len(params) == 1:
                theta = params[0]
                sub_unitary = rz(theta)
                flat = sub_unitary.ravel()
                opcodes_list.append(_OP_CONTROLLED)
                targets_list.append(target)
                controls_list.append(control)
                gate_params_list.extend(flat)
                diag_phases_list.extend(_zero2)
                two_qubit_offsets_list.append(-1)
            elif gate_name in CONTROLLED_GATE_SUB_UNITARIES:
                flat = GATE_CACHE[gate_name]
                opcodes_list.append(_OP_CONTROLLED)
                targets_list.append(target)
                controls_list.append(control)
                gate_params_list.extend(flat)
                diag_phases_list.extend(_zero2)
                two_qubit_offsets_list.append(-1)
            else:
                raise ValueError(
                    f"Gate '{gate_name}' not supported by simulator. "
                    f"Call module.unroll() first."
                )

    # Flush remaining pending single-qubit gates
    _flush_all()

    n = len(opcodes_list)
    if n == 0:
        return n, None, None, None, None, None, None, None

    opcodes = np.array(opcodes_list, dtype=np.int32)
    targets = np.array(targets_list, dtype=np.int32)
    controls = np.array(controls_list, dtype=np.int32)
    gate_params = np.ascontiguousarray(np.array(gate_params_list, dtype=np.complex128))
    diag_phases = np.ascontiguousarray(np.array(diag_phases_list, dtype=np.complex128))
    two_qubit_offsets = np.array(two_qubit_offsets_list, dtype=np.int32)
    if two_qubit_gates_list:
        two_qubit_gates = np.ascontiguousarray(
            np.array(two_qubit_gates_list, dtype=np.complex128)
        )
    else:
        two_qubit_gates = np.zeros(1, dtype=np.complex128)

    return n, opcodes, targets, controls, gate_params, diag_phases, two_qubit_offsets, two_qubit_gates


@dataclass(frozen=True)
class SimulatorResult:
    """Class to store the result of a statevector simulation."""

    probabilities: np.ndarray
    measurement_counts: Counter[str, int]
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

        n, opcodes, targets, controls, gate_params, diag_phases, tq_offsets, tq_gates = \
            _preprocess(program, num_qubits)

        if n > 0:
            apply_circuit(
                sv, num_qubits, opcodes, targets, controls,
                gate_params, diag_phases, tq_offsets, tq_gates, n,
            )

        if shots < 0:
            raise ValueError("Shots must be greater than or equal to 0.")

        probabilities = np.abs(sv) ** 2
        samples = self._rng.choice(len(probabilities), size=shots, p=probabilities)
        counts = Counter(format(s, f"0{num_qubits}b")[::-1] for s in samples)

        return SimulatorResult(probabilities, counts, sv)
