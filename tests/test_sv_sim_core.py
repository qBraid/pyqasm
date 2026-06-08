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
Qiskit-free tests for the PyQASM statevector simulator.

``test_sv_sim.py`` compares against Qiskit and is skipped wherever Qiskit is not
installed (e.g. the wheel-build containers). The tests here have no third-party
dependency so they run everywhere, and they focus on correctness of the
fast-path gate handling, fusion, and error behaviour rather than raw numerics.
"""

import numpy as np
import pytest
from openqasm3.ast import (
    BinaryExpression,
    BinaryOperator,
    BooleanLiteral,
    FloatLiteral,
    Identifier,
    IntegerLiteral,
    UnaryExpression,
    UnaryOperator,
)

from pyqasm import loads
from pyqasm.simulator.statevector import (
    Simulator,
    _try_eval_expression,
    rz,
)

# --- tiny reference statevector simulator (little-endian: qubit i is bit i) ---

_I = np.eye(2, dtype=complex)
_REF_GATES = {
    "x": np.array([[0, 1], [1, 0]], dtype=complex),
    "y": np.array([[0, -1j], [1j, 0]], dtype=complex),
    "z": np.array([[1, 0], [0, -1]], dtype=complex),
    "h": np.array([[1, 1], [1, -1]], dtype=complex) / np.sqrt(2),
    "s": np.array([[1, 0], [0, 1j]], dtype=complex),
    "sdg": np.array([[1, 0], [0, -1j]], dtype=complex),
    "t": np.array([[1, 0], [0, np.exp(1j * np.pi / 4)]], dtype=complex),
    "tdg": np.array([[1, 0], [0, np.exp(-1j * np.pi / 4)]], dtype=complex),
    "id": _I,
}


def _embed(mat, target, num_qubits):
    op = np.array([[1]], dtype=complex)
    for qubit in range(num_qubits):
        op = np.kron(mat if qubit == target else _I, op)
    return op


def _embed_controlled(mat, control, target, num_qubits):
    p0 = np.array([[1, 0], [0, 0]], dtype=complex)
    p1 = np.array([[0, 0], [0, 1]], dtype=complex)
    op0 = op1 = np.array([[1]], dtype=complex)
    for qubit in range(num_qubits):
        if qubit == control:
            op0, op1 = np.kron(p0, op0), np.kron(p1, op1)
        elif qubit == target:
            op0, op1 = np.kron(_I, op0), np.kron(mat, op1)
        else:
            op0, op1 = np.kron(_I, op0), np.kron(_I, op1)
    return op0 + op1


def reference_statevector(ops, num_qubits):
    """ops: list of (name, [qubits], [params]). Returns the final statevector."""
    sv = np.zeros(2**num_qubits, dtype=complex)
    sv[0] = 1.0
    for name, qubits, params in ops:
        if name in _REF_GATES:
            sv = _embed(_REF_GATES[name], qubits[0], num_qubits) @ sv
        elif name == "rz":
            mat = np.array([[np.exp(-1j * params[0] / 2), 0], [0, np.exp(1j * params[0] / 2)]])
            sv = _embed(mat, qubits[0], num_qubits) @ sv
        elif name in ("cx", "cy", "cz"):
            sv = _embed_controlled(_REF_GATES[name[1:]], qubits[0], qubits[1], num_qubits) @ sv
        elif name == "crz":
            mat = np.array([[np.exp(-1j * params[0] / 2), 0], [0, np.exp(1j * params[0] / 2)]])
            sv = _embed_controlled(mat, qubits[0], qubits[1], num_qubits) @ sv
        else:
            raise ValueError(f"reference simulator has no gate {name!r}")
    return sv


def assert_sv_close(actual, expected, atol=1e-9):
    """Compare statevectors up to an irrelevant global phase."""
    idx = int(np.argmax(np.abs(expected)))
    phase = actual[idx] / expected[idx]
    assert abs(abs(phase) - 1) < atol, "statevectors differ by more than a global phase"
    assert np.allclose(actual, phase * expected, atol=atol)


def run_sv(qasm, external_gates=None):
    module = loads(qasm)
    module.unroll(external_gates=external_gates)
    return Simulator(seed=0).run(module, shots=0).final_statevector


# --------------------------------------------------------------------------
# crz fast path regression: a controlled-Rz phases BOTH target=0 and target=1
# when the control is set. The fast path must equal pyqasm's own (qiskit-
# verified) full decomposition; the earlier implementation only phased the
# |control=1, target=1> amplitude, which is a controlled-phase gate.
# --------------------------------------------------------------------------


@pytest.mark.parametrize("theta", [0.0, 0.7, np.pi / 2, np.pi, -1.3, 2 * np.pi])
@pytest.mark.parametrize("control, target", [(0, 1), (1, 0)])
def test_crz_fast_path_matches_decomposition(theta, control, target):
    qasm = (
        "OPENQASM 3;\n"
        'include "stdgates.inc";\n'
        "qubit[2] q;\n"
        "h q[0];\n"
        "h q[1];\n"
        f"crz({theta}) q[{control}], q[{target}];\n"
    )
    fast = run_sv(qasm, external_gates=["crz"])  # hits the crz fast path
    decomposed = run_sv(qasm)  # full rz/rx/cx decomposition (oracle)
    assert_sv_close(fast, decomposed)


def test_crz_phases_control_one_target_zero():
    """Directly pin the |control=1, target=0> phase the bug used to drop."""
    theta = 1.0
    qasm = (
        "OPENQASM 3;\n"
        'include "stdgates.inc";\n'
        "qubit[2] q;\n"
        "x q[0];\n"  # control = 1, target = 0  -> basis index 1
        f"crz({theta}) q[0], q[1];\n"
    )
    sv = run_sv(qasm, external_gates=["crz"])
    expected = reference_statevector([("x", [0], []), ("crz", [0, 1], [theta])], 2)
    assert_sv_close(sv, expected)
    # the amplitude at |control=1,target=0> (index 1) must carry e^{-i*theta/2}
    assert np.isclose(sv[1], np.exp(-1j * theta / 2))


# --------------------------------------------------------------------------
# Known-action checks for the directly-supported fast-path gates.
# --------------------------------------------------------------------------


@pytest.mark.parametrize("gate", ["x", "y", "z", "h", "s", "sdg", "t", "tdg", "id"])
def test_single_qubit_gate_action(gate):
    qasm = f'OPENQASM 3;\ninclude "stdgates.inc";\nqubit[1] q;\nx q[0];\n{gate} q[0];\n'
    sv = Simulator(seed=0).run(loads_unrolled(qasm), shots=0).final_statevector
    expected = reference_statevector([("x", [0], []), (gate, [0], [])], 1)
    assert_sv_close(sv, expected)


def test_cz_swap_cx_action():
    # cz on |11> -> -|11>
    cz_sv = run_sv(
        'OPENQASM 3;\ninclude "stdgates.inc";\nqubit[2] q;\nx q[0];\nx q[1];\ncz q[0], q[1];\n'
    )
    assert_sv_close(
        cz_sv, reference_statevector([("x", [0], []), ("x", [1], []), ("cz", [0, 1], [])], 2)
    )
    # swap |q1=0,q0=1> (index 1) -> |q1=1,q0=0> (index 2)
    swap_sv = run_sv(
        'OPENQASM 3;\ninclude "stdgates.inc";\nqubit[2] q;\nx q[0];\nswap q[0], q[1];\n'
    )
    assert np.isclose(swap_sv[2], 1.0)
    # cx control=q0,target=q1 on |01> (index 1) -> |11> (index 3)
    cx_sv = run_sv('OPENQASM 3;\ninclude "stdgates.inc";\nqubit[2] q;\nx q[0];\ncx q[0], q[1];\n')
    assert np.isclose(cx_sv[3], 1.0)


def test_u3_fast_path_matches_decomposition():
    qasm = 'OPENQASM 3;\ninclude "stdgates.inc";\nqubit[1] q;\nh q[0];\nu3(0.7, 1.1, -0.4) q[0];\n'
    assert_sv_close(run_sv(qasm, external_gates=["u3"]), run_sv(qasm))


# --------------------------------------------------------------------------
# Gate fusion: a run of diagonal gates fuses into phases, and a following
# non-diagonal gate forces the accumulated matrix path + flush.
# --------------------------------------------------------------------------


def test_diagonal_then_nondiagonal_fusion():
    qasm = (
        'OPENQASM 3;\ninclude "stdgates.inc";\nqubit[1] q;\n'
        "h q[0];\n"  # non-diagonal
        "z q[0];\ns q[0];\nt q[0];\n"  # fused diagonal run
        "h q[0];\n"  # forces flush + non-diagonal accumulation
        "rz(0.5) q[0];\n"
    )
    sv = run_sv(qasm)
    expected = reference_statevector(
        [
            ("h", [0], []),
            ("z", [0], []),
            ("s", [0], []),
            ("t", [0], []),
            ("h", [0], []),
            ("rz", [0], [0.5]),
        ],
        1,
    )
    assert_sv_close(sv, expected)


def test_diagonal_gates_commute_through_cz():
    # Diagonal single-qubit gates remain fused across CZ; result must still be correct.
    qasm = (
        'OPENQASM 3;\ninclude "stdgates.inc";\nqubit[2] q;\n'
        "h q[0];\nh q[1];\nz q[0];\ncz q[0], q[1];\ns q[1];\n"
    )
    sv = run_sv(qasm)
    expected = reference_statevector(
        [("h", [0], []), ("h", [1], []), ("z", [0], []), ("cz", [0, 1], []), ("s", [1], [])],
        2,
    )
    assert_sv_close(sv, expected)


# --------------------------------------------------------------------------
# Error handling and edge cases.
# --------------------------------------------------------------------------


def test_unsupported_single_qubit_gate_raises():
    module = loads('OPENQASM 3;\ninclude "stdgates.inc";\nqubit[1] q;\nsx q[0];\n')
    with pytest.raises(ValueError, match="not supported by simulator"):
        Simulator().run(module, shots=0)


def test_unsupported_two_qubit_gate_raises():
    module = loads('OPENQASM 3;\ninclude "stdgates.inc";\nqubit[2] q;\ncp(0.5) q[0], q[1];\n')
    with pytest.raises(ValueError, match="not supported by simulator"):
        Simulator().run(module, shots=0)


def test_negative_shots_raises():
    with pytest.raises(ValueError, match="Shots must be"):
        Simulator().run('OPENQASM 3;\ninclude "stdgates.inc";\nqubit[1] q;\nh q[0];\n', shots=-1)


def test_empty_circuit_returns_ground_state():
    result = Simulator(seed=0).run("OPENQASM 3;\nqubit[2] q;\n", shots=5)
    assert np.isclose(result.final_statevector[0], 1.0)
    assert sum(result.measurement_counts.values()) == 5


def test_shots_sampling_is_seed_deterministic():
    qasm = 'OPENQASM 3;\ninclude "stdgates.inc";\nqubit[2] q;\nh q[0];\ncx q[0], q[1];\n'
    first = Simulator(seed=7).run(qasm, shots=128).measurement_counts
    second = Simulator(seed=7).run(qasm, shots=128).measurement_counts
    assert first == second
    assert sum(first.values()) == 128
    # Bell state only populates |00> and |11>; each key is num_qubits long.
    assert set(first) <= {"00", "11"}


def test_string_input_removes_idle_qubits():
    # q[1] is idle, so the reported circuit collapses to a single qubit.
    result = Simulator(seed=0).run(
        'OPENQASM 3;\ninclude "stdgates.inc";\nqubit[2] q;\nx q[0];\n', shots=4
    )
    assert len(result.final_statevector) == 2
    assert set(result.measurement_counts) == {"1"}


# --------------------------------------------------------------------------
# Helper-level unit tests.
# --------------------------------------------------------------------------


def test_rz_helper_matrix():
    mat = rz(np.pi / 2)
    expected = np.array([[np.exp(-1j * np.pi / 4), 0], [0, np.exp(1j * np.pi / 4)]])
    assert np.allclose(mat, expected)


def test_try_eval_expression_constants_and_operators():
    assert _try_eval_expression(IntegerLiteral(value=3)) == 3.0
    assert _try_eval_expression(FloatLiteral(value=1.5)) == 1.5
    assert _try_eval_expression(Identifier(name="pi")) == pytest.approx(np.pi)
    assert _try_eval_expression(Identifier(name="tau")) == pytest.approx(2 * np.pi)
    assert _try_eval_expression(Identifier(name="euler")) == pytest.approx(np.e)
    # unknown identifier is not evaluable
    assert _try_eval_expression(Identifier(name="theta")) is None

    def binop(op, lhs, rhs):
        return BinaryExpression(
            op=BinaryOperator[op], lhs=FloatLiteral(value=lhs), rhs=FloatLiteral(value=rhs)
        )

    assert _try_eval_expression(binop("+", 1, 2)) == 3.0
    assert _try_eval_expression(binop("-", 5, 2)) == 3.0
    assert _try_eval_expression(binop("*", 3, 4)) == 12.0
    assert _try_eval_expression(binop("/", 8, 2)) == 4.0
    assert _try_eval_expression(binop("**", 2, 3)) == 8.0
    # unevaluable operand propagates as None
    nested = BinaryExpression(
        op=BinaryOperator["+"], lhs=Identifier(name="x"), rhs=FloatLiteral(value=1.0)
    )
    assert _try_eval_expression(nested) is None

    neg = UnaryExpression(op=UnaryOperator["-"], expression=FloatLiteral(value=2.5))
    assert _try_eval_expression(neg) == -2.5
    assert (
        _try_eval_expression(
            UnaryExpression(op=UnaryOperator["-"], expression=Identifier(name="x"))
        )
        is None
    )

    # Operators / node types the evaluator does not handle return None rather
    # than raising, so an un-evaluable parameter is simply skipped downstream.
    assert _try_eval_expression(binop("%", 5, 2)) is None
    assert (
        _try_eval_expression(
            UnaryExpression(op=UnaryOperator["!"], expression=FloatLiteral(value=1.0))
        )
        is None
    )
    assert _try_eval_expression(BooleanLiteral(value=True)) is None


def test_zero_angle_rotation_is_identity():
    """A lone zero-angle rotation produces a matrix tagged non-diagonal that is
    actually the (diagonal) identity; the fusion flush must detect and apply it
    as a no-op. ``rx(0)`` is kept alone on q[0] so it is not fused with another
    non-diagonal gate first."""
    sv = run_sv('OPENQASM 3;\ninclude "stdgates.inc";\nqubit[2] q;\nh q[1];\nrx(0) q[0];\n')
    expected = reference_statevector([("h", [1], [])], 2)
    assert_sv_close(sv, expected)


def loads_unrolled(qasm):
    module = loads(qasm)
    module.unroll()
    return module
