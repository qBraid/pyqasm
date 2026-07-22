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


def test_module_not_unrolled_raises():
    """A QasmModule that was never unrolled must raise instead of silently
    simulating the raw AST (which would drop control flow)."""
    module = loads('OPENQASM 3;\ninclude "stdgates.inc";\nqubit[1] q;\nsx q[0];\n')
    with pytest.raises(ValueError, match="has not been unrolled"):
        Simulator().run(module, shots=0)


def test_unsupported_single_qubit_gate_raises():
    """The unsupported-gate branch is defense in depth: every stdgates gate
    unrolls to the supported basis, so force an unknown name into the AST."""
    module = loads('OPENQASM 3;\ninclude "stdgates.inc";\nqubit[1] q;\nh q[0];\n')
    module.unroll()
    for statement in module._unrolled_ast.statements:
        if type(statement).__name__ == "QuantumGate":
            statement.name.name = "bogus"
    with pytest.raises(ValueError, match="not supported by the statevector simulator"):
        Simulator().run(module, shots=0)


def test_unsupported_two_qubit_gate_raises():
    module = loads('OPENQASM 3;\ninclude "stdgates.inc";\nqubit[2] q;\ncx q[0], q[1];\n')
    module.unroll()
    for statement in module._unrolled_ast.statements:
        if type(statement).__name__ == "QuantumGate":
            statement.name.name = "bogus2q"
    with pytest.raises(ValueError, match="not supported by the statevector simulator"):
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


# --------------------------------------------------------------------------
# Multi-register programs: operands must resolve through (register, index),
# not the register-local index alone. Regression for the silent wrong-answer
# bug where `a[0]` and `b[0]` both mapped to global qubit 0.
# --------------------------------------------------------------------------


def test_multi_register_bell_state():
    """Entangling across two registers must correlate the right qubits."""
    module = loads_unrolled(
        'OPENQASM 3;\ninclude "stdgates.inc";\n'
        "qubit[2] a;\nqubit[2] b;\nh a[0];\ncx a[0], b[0];\n"
    )
    result = Simulator(seed=0).run(module, shots=0)
    # a[0] is global qubit 0, b[0] is global qubit 2 -> |0000> + |0101>
    expected = np.zeros(16)
    expected[0b0000] = 0.5
    expected[0b0101] = 0.5
    assert np.allclose(result.probabilities, expected, atol=1e-12)


def test_multi_register_distinct_qubits():
    """x a[0]; h b[0] must act on two different qubits, not fuse onto one."""
    result = Simulator(seed=0).run(
        'OPENQASM 3;\ninclude "stdgates.inc";\nqubit[1] a;\nqubit[1] b;\nx a[0];\nh b[0];\n',
        shots=0,
    )
    assert np.allclose(result.probabilities, [0, 0.5, 0, 0.5], atol=1e-12)


def test_register_index_out_of_range_raises():
    module = loads_unrolled('OPENQASM 3;\ninclude "stdgates.inc";\nqubit[2] q;\nh q[0];\n')
    for statement in module._unrolled_ast.statements:
        if type(statement).__name__ == "QuantumGate":
            statement.qubits[0].indices[0][0].value = 5
    with pytest.raises(ValueError, match="out of range"):
        Simulator().run(module, shots=0)


# --------------------------------------------------------------------------
# ccx / toffoli: previously silently dropped (no else branch for 3-qubit
# gates), corrupting every circuit containing one.
# --------------------------------------------------------------------------


def _reference_ccx(num_qubits, controls, target):
    dim = 2**num_qubits
    mat = np.eye(dim, dtype=complex)
    i0 = (1 << controls[0]) | (1 << controls[1])
    i1 = i0 | (1 << target)
    mat[i0, i0] = 0
    mat[i1, i1] = 0
    mat[i0, i1] = 1
    mat[i1, i0] = 1
    return mat


def test_ccx_truth_table():
    """ccx flips the target iff both controls are set."""
    for prep, expected_index in [
        ("", 0b000),
        ("x q[0];", 0b001),
        ("x q[1];", 0b010),
        ("x q[0];\nx q[1];", 0b111),  # both controls -> target flipped
        ("x q[0];\nx q[1];\nx q[2];", 0b011),  # target un-flipped
    ]:
        result = Simulator(seed=0).run(
            'OPENQASM 3;\ninclude "stdgates.inc";\nqubit[3] q;\n'
            f"{prep}\nccx q[0], q[1], q[2];\n",
            shots=0,
        )
        expected = np.zeros(8)
        expected[expected_index] = 1
        assert np.allclose(result.probabilities, expected, atol=1e-12), prep


def test_ccx_statevector_exact():
    """ccx on a non-trivial superposition matches the exact unitary, phases included."""
    sv = run_sv(
        'OPENQASM 3;\ninclude "stdgates.inc";\nqubit[3] q;\n'
        "ry(0.7) q[0];\nry(1.1) q[1];\nry(0.4) q[2];\nccx q[0], q[1], q[2];\n"
    )

    def _ry(theta):
        c, s = np.cos(theta / 2), np.sin(theta / 2)
        return np.array([[c, -s], [s, c]], dtype=complex)

    prep = np.zeros(8, dtype=complex)
    prep[0] = 1.0
    for qubit, theta in [(0, 0.7), (1, 1.1), (2, 0.4)]:
        prep = _embed(_ry(theta), qubit, 3) @ prep
    expected = _reference_ccx(3, (0, 1), 2) @ prep
    assert np.allclose(sv, expected, atol=1e-12)


def test_ccx_nonadjacent_qubits():
    """ccx with non-adjacent and permuted operand order."""
    sv = run_sv(
        'OPENQASM 3;\ninclude "stdgates.inc";\nqubit[4] q;\n'
        "x q[3];\nx q[1];\nccx q[3], q[1], q[0];\n"
    )
    expected = np.zeros(16, dtype=complex)
    expected[0b1011] = 1  # q3, q1 set -> q0 flipped
    assert np.allclose(sv, expected, atol=1e-12)


def test_ccx_identical_qubits_raises():
    module = loads_unrolled(
        'OPENQASM 3;\ninclude "stdgates.inc";\nqubit[3] q;\nccx q[0], q[1], q[2];\n'
    )
    for statement in module._unrolled_ast.statements:
        if type(statement).__name__ == "QuantumGate":
            statement.qubits[1].indices[0][0].value = 0  # duplicate control
    with pytest.raises(ValueError, match="distinct"):
        Simulator().run(module, shots=0)


# --------------------------------------------------------------------------
# Statements with real semantics must raise instead of being silently
# dropped; harmless statements must still be accepted.
# --------------------------------------------------------------------------


def test_reset_raises():
    with pytest.raises(NotImplementedError, match="reset"):
        Simulator().run(
            'OPENQASM 3;\ninclude "stdgates.inc";\nqubit[1] q;\nx q[0];\nreset q[0];\n',
            shots=0,
        )


def test_mid_circuit_measurement_raises():
    with pytest.raises(NotImplementedError, match="[Mm]id-circuit"):
        Simulator().run(
            'OPENQASM 3;\ninclude "stdgates.inc";\nqubit[2] q;\nbit[2] c;\n'
            "h q[0];\nc[0] = measure q[0];\nx q[1];\n",
            shots=0,
        )


def test_branching_raises():
    module = loads(
        'OPENQASM 3;\ninclude "stdgates.inc";\nqubit[2] q;\nbit[2] c;\n'
        "h q[0];\nc[0] = measure q[0];\nif (c[0] == 1) { x q[1]; }\n"
    )
    module.unroll()
    with pytest.raises(NotImplementedError):
        Simulator().run(module, shots=0)


def test_terminal_measurement_accepted():
    """Terminal measurement is honored by the sampling step and must not raise."""
    result = Simulator(seed=0).run(
        'OPENQASM 3;\ninclude "stdgates.inc";\nqubit[1] q;\nbit[1] c;\n'
        "h q[0];\nc[0] = measure q[0];\n",
        shots=100,
    )
    assert sum(result.measurement_counts.values()) == 100


def test_barrier_is_noop():
    result = Simulator(seed=0).run(
        'OPENQASM 3;\ninclude "stdgates.inc";\nqubit[2] q;\nh q[0];\nbarrier q;\ncx q[0], q[1];\n',
        shots=0,
    )
    assert np.allclose(result.probabilities, [0.5, 0, 0, 0.5], atol=1e-12)


# --------------------------------------------------------------------------
# p / sx support: main's c3x/c4x decompositions emit literal `p` gates, which
# previously failed with a misleading "call unroll() first" error.
# --------------------------------------------------------------------------


def test_p_gate_exact():
    """h; p(theta); h on |0>: amplitudes ((1+e^it)/2, (1-e^it)/2).

    ``external_gates=["p"]`` keeps the literal `p` in the AST so this exercises
    the simulator's own diagonal fast path (the unroller's rz-chain
    decomposition would only agree up to global phase).
    """
    theta = 0.37
    sv = run_sv(
        f'OPENQASM 3;\ninclude "stdgates.inc";\nqubit[1] q;\nh q[0];\np({theta}) q[0];\nh q[0];\n',
        external_gates=["p"],
    )
    expected = np.array([(1 + np.exp(1j * theta)) / 2, (1 - np.exp(1j * theta)) / 2])
    assert np.allclose(sv, expected, atol=1e-12)
    # And the decomposed path agrees up to global phase.
    decomposed = run_sv(
        f'OPENQASM 3;\ninclude "stdgates.inc";\nqubit[1] q;\nh q[0];\np({theta}) q[0];\nh q[0];\n'
    )
    assert_sv_close(decomposed, expected)


def test_sx_squared_is_x():
    sv = run_sv('OPENQASM 3;\ninclude "stdgates.inc";\nqubit[1] q;\nsx q[0];\nsx q[0];\n')
    assert np.allclose(np.abs(sv) ** 2, [0, 1], atol=1e-12)


def test_c3x_runs():
    """c3x decomposes through `p` gates on main; the simulator must accept it."""
    result = Simulator(seed=0).run(
        'OPENQASM 3;\ninclude "stdgates.inc";\nqubit[4] q;\n'
        "x q[0];\nx q[1];\nx q[2];\nc3x q[0], q[1], q[2], q[3];\n",
        shots=0,
    )
    expected = np.zeros(16)
    expected[0b1111] = 1
    assert np.allclose(result.probabilities, expected, atol=1e-9)


def test_c4x_runs():
    result = Simulator(seed=0).run(
        'OPENQASM 3;\ninclude "stdgates.inc";\nqubit[5] q;\n'
        "x q[0];\nx q[1];\nx q[2];\nx q[3];\nc4x q[0], q[1], q[2], q[3], q[4];\n",
        shots=0,
    )
    expected = np.zeros(32)
    expected[0b11111] = 1
    assert np.allclose(result.probabilities, expected, atol=1e-9)


# --------------------------------------------------------------------------
# Result conventions and resource guards.
# --------------------------------------------------------------------------


def test_counts_keys_match_probabilities_indexing():
    """Counts keys are the binary rendering of the probabilities index (qubit 0
    rightmost, matching qiskit), so probabilities[int(key, 2)] is the outcome's
    probability. Regression for the reversed-keys bug."""
    result = Simulator(seed=0).run(
        'OPENQASM 3;\ninclude "stdgates.inc";\nqubit[3] q;\nid q[0];\nid q[1];\nx q[2];\n',
        shots=10,
    )
    assert dict(result.measurement_counts) == {"100": 10}
    assert result.probabilities[int("100", 2)] == pytest.approx(1.0)


def test_max_qubits_guard(monkeypatch):
    """Over-ceiling programs raise instead of dying on the 2**n allocation."""
    monkeypatch.setenv("PYQASM_SIM_MAX_QUBITS", "8")
    qasm = 'OPENQASM 3;\ninclude "stdgates.inc";\nqubit[9] q;\n' + "".join(
        f"h q[{i}];\n" for i in range(9)
    )
    with pytest.raises(ValueError, match="ceiling"):
        Simulator().run(qasm, shots=0)


def test_shots_validated_before_simulation():
    with pytest.raises(ValueError, match="Shots must be"):
        Simulator().run("OPENQASM 3;\nqubit[1] q;\n", shots=-1)


# --------------------------------------------------------------------------
# Kernel argument validation: malformed calls raise ValueError instead of
# corrupting memory / crashing the interpreter.
# --------------------------------------------------------------------------


def test_kernel_validation_rejects_malformed_calls():
    # pylint: disable-next=import-outside-toplevel,no-name-in-module
    from pyqasm.accelerate import sv_sim

    identity = np.array([1, 0, 0, 1], dtype=np.complex128)
    sv = np.zeros(8, dtype=np.complex128)
    sv[0] = 1

    with pytest.raises(ValueError, match="out of range"):
        sv_sim.apply_single_qubit_gate(sv, 3, 40, identity)
    with pytest.raises(ValueError, match="does not match"):
        sv_sim.apply_single_qubit_gate(sv, 30, 0, identity)
    with pytest.raises(ValueError, match="4 elements"):
        sv_sim.apply_single_qubit_gate(sv, 3, 0, np.array([1], dtype=np.complex128))
    with pytest.raises(ValueError, match="both"):
        sv_sim.apply_controlled_gate(sv, 3, 1, 1, identity)
    with pytest.raises(ValueError, match="does not match"):
        sv_sim.apply_single_qubit_gate(np.zeros(0, dtype=np.complex128), 1, 0, identity)


def test_apply_circuit_validation():
    # pylint: disable-next=import-outside-toplevel,no-name-in-module
    from pyqasm.accelerate import sv_sim

    sv = np.zeros(8, dtype=np.complex128)
    sv[0] = 1
    zeros_i32 = np.zeros(1, dtype=np.int32)
    gate_params = np.zeros(4, dtype=np.complex128)
    diag_phases = np.zeros(2, dtype=np.complex128)
    tq_gates = np.zeros(16, dtype=np.complex128)

    with pytest.raises(ValueError, match="shorter than"):
        sv_sim.apply_circuit(
            sv,
            3,
            zeros_i32,
            zeros_i32,
            zeros_i32,
            gate_params,
            diag_phases,
            zeros_i32,
            tq_gates,
            10_000_000,
        )
    with pytest.raises(ValueError, match="out of range"):
        sv_sim.apply_circuit(
            sv,
            3,
            np.array([0], dtype=np.int32),
            np.array([40], dtype=np.int32),
            zeros_i32,
            gate_params,
            diag_phases,
            zeros_i32,
            tq_gates,
            1,
        )
    with pytest.raises(ValueError, match="offset"):
        sv_sim.apply_circuit(
            sv,
            3,
            np.array([4], dtype=np.int32),
            np.array([1], dtype=np.int32),
            zeros_i32,
            gate_params,
            diag_phases,
            np.array([1 << 28], dtype=np.int32),
            tq_gates,
            1,
        )
