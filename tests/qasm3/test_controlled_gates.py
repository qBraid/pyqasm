# Copyright 2026 qBraid
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

"""Tests for the ctrl modifier on standard gates without a dedicated controlled form."""

import numpy as np
import pytest

from pyqasm.entrypoint import dumps, loads
from pyqasm.exceptions import ValidationError
from tests.utils import assert_unitary_equal, unitary_from_unrolled_ast

ANGLES = (0.3, 0.5, 0.7, 1.1)

_X = np.array([[0, 1], [1, 0]], dtype=complex)
_Y = np.array([[0, -1j], [1j, 0]], dtype=complex)
_H = np.array([[1, 1], [1, -1]], dtype=complex) / np.sqrt(2)
_SX = np.array([[1 + 1j, 1 - 1j], [1 - 1j, 1 + 1j]], dtype=complex) / 2
_SWAP = np.eye(4, dtype=complex)[[0, 2, 1, 3]]


def _p(lam):
    return np.diag([1, np.exp(1j * lam)])


def _u(theta, phi, lam):
    cos, sin = np.cos(theta / 2), np.sin(theta / 2)
    return np.array(
        [[cos, -np.exp(1j * lam) * sin], [np.exp(1j * phi) * sin, np.exp(1j * (phi + lam)) * cos]]
    )


def _rx(theta):
    cos, sin = np.cos(theta / 2), np.sin(theta / 2)
    return np.array([[cos, -1j * sin], [-1j * sin, cos]])


def _prx(theta, phi):
    cos, sin = np.cos(theta / 2), np.sin(theta / 2)
    return np.array([[cos, -1j * np.exp(-1j * phi) * sin], [-1j * np.exp(1j * phi) * sin, cos]])


# Textbook matrices, written independently of the U-form table in pyqasm.maps.gates.
ONE_QUBIT_GATES = {
    "id": np.eye(2, dtype=complex),
    "x": _X,
    "not": _X,
    "y": _Y,
    "z": _p(np.pi),
    "h": _H,
    "s": _p(np.pi / 2),
    "sdg": _p(-np.pi / 2),
    "si": _p(-np.pi / 2),
    "t": _p(np.pi / 4),
    "tdg": _p(-np.pi / 4),
    "ti": _p(-np.pi / 4),
    "sx": _SX,
    "v": _SX,
    "sxdg": _SX.conj().T,
    "vi": _SX.conj().T,
    "rx(0.3)": _rx(0.3),
    "ry(0.3)": np.array([[np.cos(0.15), -np.sin(0.15)], [np.sin(0.15), np.cos(0.15)]]),
    "rz(0.3)": np.diag([np.exp(-0.15j), np.exp(0.15j)]),
    "p(0.3)": _p(0.3),
    "phaseshift(0.3)": _p(0.3),
    "u1(0.3)": _p(0.3),
    "U(0.3, 0.5, 0.7)": _u(*ANGLES[:3]),
    "u(0.3, 0.5, 0.7)": _u(*ANGLES[:3]),
    "u3(0.3, 0.5, 0.7)": _u(*ANGLES[:3]),
    "u2(0.5, 0.7)": _u(np.pi / 2, 0.5, 0.7),
    "prx(0.3, 0.5)": _prx(0.3, 0.5),
    "gpi(0.5)": np.array([[0, np.exp(-0.5j)], [np.exp(0.5j), 0]]),
    "gpi2(0.5)": _prx(np.pi / 2, 0.5),
}


def _controlled(matrix, num_ctrls):
    """Apply ``matrix`` to the last qubits only when the first ``num_ctrls`` qubits are 1.

    Both ``matrix`` and the result are little-endian, like ``unitary_from_unrolled_ast``.
    """
    num_targets = int(np.log2(matrix.shape[0]))
    dim = 2 ** (num_ctrls + num_targets)
    ctrl_mask = 2**num_ctrls - 1
    result = np.zeros((dim, dim), dtype=complex)
    for basis in range(dim):
        if basis & ctrl_mask != ctrl_mask:
            result[basis, basis] = 1
            continue
        for target_out in range(2**num_targets):
            result[(target_out << num_ctrls) | ctrl_mask, basis] = matrix[
                target_out, basis >> num_ctrls
            ]
    return result


def _unrolled_unitary(body, num_qubits):
    """Unroll ``body`` and return its operator, checking the output parses again."""
    module = loads(f'OPENQASM 3.0;\ninclude "stdgates.inc";\nqubit[{num_qubits}] q;\n{body}')
    module.unroll()
    loads(dumps(module)).validate()
    return unitary_from_unrolled_ast(module.unrolled_ast, num_qubits)


def _operands(num_qubits):
    return ", ".join(f"q[{i}]" for i in range(num_qubits))


@pytest.mark.parametrize("gate", ONE_QUBIT_GATES)
def test_one_qubit_reference_matches_unrolled_gate(gate):
    """The reference matrices agree with pyqasm's own unrolling of the bare gate."""
    assert_unitary_equal(_unrolled_unitary(f"{gate} q[0];", 1), ONE_QUBIT_GATES[gate])


@pytest.mark.parametrize("num_ctrls", [1, 2, 3])
@pytest.mark.parametrize("gate", ONE_QUBIT_GATES)
def test_ctrl_one_qubit_gate_is_exact(gate, num_ctrls):
    """ctrl(n) @ gate realises the controlled gate, including the base gate's phase."""
    body = f"ctrl({num_ctrls}) @ {gate} {_operands(num_ctrls + 1)};"
    assert_unitary_equal(
        _unrolled_unitary(body, num_ctrls + 1),
        _controlled(ONE_QUBIT_GATES[gate], num_ctrls),
    )


@pytest.mark.parametrize("gate", ["x", "z", "tdg", "sx", "u(0.3, 0.5, 0.7)"])
def test_ctrl_beyond_four_controls(gate):
    """Five controls go past c4x, through the recursive multi-controlled X."""
    body = f"ctrl(5) @ {gate} {_operands(6)};"
    assert_unitary_equal(_unrolled_unitary(body, 6), _controlled(ONE_QUBIT_GATES[gate], 5))


@pytest.mark.parametrize(
    "gate, num_ctrls, matrix",
    [
        ("cs", 1, _controlled(_p(np.pi / 2), 1)),
        ("csdg", 1, _controlled(_p(-np.pi / 2), 1)),
        ("csx", 1, _controlled(_SX, 1)),
        ("cy", 2, _controlled(_Y, 1)),
        ("cz", 1, _controlled(_p(np.pi), 1)),
        ("ch", 1, _controlled(_H, 1)),
        ("crx(0.3)", 1, _controlled(_rx(0.3), 1)),
        ("cp(0.3)", 2, _controlled(_p(0.3), 1)),
        ("cu1(0.3)", 1, _controlled(_p(0.3), 1)),
        ("cu3(0.3, 0.5, 0.7)", 1, _controlled(_u(*ANGLES[:3]), 1)),
        ("cu(0.3, 0.5, 0.7, 1.1)", 1, _controlled(np.exp(1.1j) * _u(*ANGLES[:3]), 1)),
        ("swap", 2, _SWAP),
        ("cswap", 1, _controlled(_SWAP, 1)),
        ("c3sx", 1, _controlled(_SX, 3)),
    ],
)
def test_ctrl_controlled_standard_gate_is_exact(gate, num_ctrls, matrix):
    """ctrl @ a standard controlled gate adds controls to its single-qubit or swap base."""
    num_qubits = num_ctrls + int(np.log2(matrix.shape[0]))
    body = f"ctrl({num_ctrls}) @ {gate} {_operands(num_qubits)};"
    assert_unitary_equal(_unrolled_unitary(body, num_qubits), _controlled(matrix, num_ctrls))


def test_ctrl_custom_gate_with_multi_controlled_z():
    """The program from issue #252: a custom gate containing ctrl(2) @ z, controlled again."""
    body = """
    gate z_on_two3 aa, ab, ac {
        x ac;
        ctrl(2) @ z aa, ab, ac;
        x ac;
    }
    ctrl @ z_on_two3 q[0], q[1], q[2], q[3];
    """
    x_on_last = np.kron(_X, np.eye(4))
    ccz = _controlled(_p(np.pi), 2)
    assert_unitary_equal(_unrolled_unitary(body, 4), _controlled(x_on_last @ ccz @ x_on_last, 1))


def test_ctrl_gates_from_failed_iqm_job():
    """The ctrl statements of a qBraid job on IQM Emerald that pyqasm rejected unroll."""
    body = "ctrl @ tdg q[1], q[3];\nctrl @ sx q[0], q[2];\nctrl @ sdg q[2], q[1];"
    module = loads(f'OPENQASM 3.0;\ninclude "stdgates.inc";\nqubit[4] q;\n{body}')
    module.unroll()
    loads(dumps(module)).validate()
    assert "ctrl" not in dumps(module)


@pytest.mark.parametrize("gate", ["tdg", "sx", "u(0.3, 0.5, 0.7)"])
def test_ctrl_one_qubit_gate_operand_order(gate):
    """The last operand is the target, whichever qubit index it has."""
    swap = _SWAP.astype(complex)
    assert_unitary_equal(
        _unrolled_unitary(f"ctrl @ {gate} q[1], q[0];", 2),
        swap @ _controlled(ONE_QUBIT_GATES[gate], 1) @ swap,
    )


@pytest.mark.parametrize(
    "body, matrix",
    [
        ("inv @ ctrl @ t q[0], q[1];", _controlled(_p(-np.pi / 4), 1)),
        ("ctrl(2) @ gphase(0.3) q[0], q[1];", _controlled(_p(0.3), 1)),
    ],
)
def test_ctrl_combined_with_other_modifiers(body, matrix):
    """inv and gphase route through the same controlled decomposition."""
    assert_unitary_equal(_unrolled_unitary(body, 2), matrix)


def test_negctrl_one_qubit_gate():
    """negctrl @ tdg applies the gate when the control is |0>."""
    x_on_ctrl = np.kron(np.eye(2), _X)
    assert_unitary_equal(
        _unrolled_unitary("negctrl @ tdg q[0], q[1];", 2),
        x_on_ctrl @ _controlled(_p(-np.pi / 4), 1) @ x_on_ctrl,
    )


def test_ctrl_unsupported_multi_qubit_gate_raises():
    """Gates that do not reduce to a single-qubit or swap base are still rejected."""
    module = loads(
        'OPENQASM 3.0;\ninclude "stdgates.inc";\nqubit[3] q;\nctrl @ iswap q[0], q[1], q[2];'
    )
    with pytest.raises(ValidationError, match="Unsupported controlled QASM operation: iswap"):
        module.unroll()


@pytest.mark.parametrize("gate, num_qubits", [("ctrl(11) @ x", 12), ("ctrl(7) @ c4x", 12)])
def test_ctrl_too_many_controls_raises(gate, num_qubits):
    """Control counts past MAX_DECOMPOSED_CTRLS are rejected instead of unrolled."""
    module = loads(
        f'OPENQASM 3.0;\ninclude "stdgates.inc";\nqubit[{num_qubits}] q;\n'
        f"{gate} {_operands(num_qubits)};"
    )
    with pytest.raises(ValidationError, match="with 11 controls"):
        module.unroll()
