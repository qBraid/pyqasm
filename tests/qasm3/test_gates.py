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
Module containing unit tests for unrolling quantum gates.

"""

import numpy as np
import openqasm3.ast as qasm3_ast
import pytest

from pyqasm.entrypoint import dumps, loads
from pyqasm.exceptions import ValidationError
from tests.qasm3.resources.gates import (
    CUSTOM_GATE_INCORRECT_TESTS,
    PHYSICAL_QUBIT_VALID_TESTS,
    SINGLE_QUBIT_GATE_INCORRECT_TESTS,
    custom_op_tests,
    double_op_tests,
    five_op_tests,
    four_op_tests,
    rotation_tests,
    single_op_tests,
    triple_op_tests,
)
from tests.utils import (
    assert_unitary_equal,
    check_custom_qasm_gate_op,
    check_custom_qasm_gate_op_with_external_gates,
    check_five_qubit_gate_op,
    check_four_qubit_gate_op,
    check_single_qubit_gate_op,
    check_single_qubit_rotation_op,
    check_three_qubit_gate_op,
    check_two_qubit_gate_op,
    check_unrolled_qasm,
    mcx_unitary,
    unitary_from_unrolled_ast,
)


# 7. Test gate operations in different ways
@pytest.mark.parametrize("circuit_name", single_op_tests)
def test_single_qubit_qasm3_gates(circuit_name, request):
    # see _generate_one_qubit_fixture for details
    qubit_list = [0, 1, 0, 0, 1]
    gate_name = circuit_name.removeprefix("Fixture_")

    qasm3_string = request.getfixturevalue(circuit_name)
    result = loads(qasm3_string)
    result.unroll()
    assert result.num_qubits == 2
    assert result.num_clbits == 0
    check_single_qubit_gate_op(result.unrolled_ast, 5, qubit_list, gate_name)


@pytest.mark.parametrize("circuit_name", double_op_tests)
def test_two_qubit_qasm3_gates(circuit_name, request):
    qubit_list = [[0, 1], [0, 1]]
    gate_name = circuit_name.removeprefix("Fixture_")

    qasm3_string = request.getfixturevalue(circuit_name)
    result = loads(qasm3_string)
    result.unroll()
    assert result.num_qubits == 2
    assert result.num_clbits == 0
    check_two_qubit_gate_op(result.unrolled_ast, 2, qubit_list, gate_name)


@pytest.mark.parametrize("circuit_name", rotation_tests)
def test_rotation_qasm3_gates(circuit_name, request):
    qubit_list = [0, 1, 0]
    param_list = [0.5, 0.5, 0.5]
    gate_name = circuit_name.removeprefix("Fixture_")

    qasm3_string = request.getfixturevalue(circuit_name)
    result = loads(qasm3_string)
    result.unroll()
    assert result.num_qubits == 2
    assert result.num_clbits == 0
    check_single_qubit_rotation_op(result.unrolled_ast, 3, qubit_list, param_list, gate_name)


@pytest.mark.parametrize("circuit_name", triple_op_tests)
def test_three_qubit_qasm3_gates(circuit_name, request):
    qubit_list = [[0, 1, 2], [0, 1, 2]]
    gate_name = circuit_name.removeprefix("Fixture_")

    qasm3_string = request.getfixturevalue(circuit_name)
    result = loads(qasm3_string)
    result.unroll()
    assert result.num_qubits == 3
    assert result.num_clbits == 0
    check_three_qubit_gate_op(result.unrolled_ast, 2, qubit_list, gate_name)


@pytest.mark.parametrize("circuit_name", four_op_tests)
def test_four_qubit_qasm3_gates(circuit_name, request):
    qubit_list = [[0, 1, 2, 3], [0, 1, 2, 3]]
    gate_name = circuit_name.removeprefix("Fixture_")

    qasm3_string = request.getfixturevalue(circuit_name)
    result = loads(qasm3_string)
    # we do not want to validate every gate inside it
    result.unroll(external_gates=[gate_name])
    assert result.num_qubits == 4
    assert result.num_clbits == 0
    check_four_qubit_gate_op(result.unrolled_ast, 2, qubit_list, gate_name)


@pytest.mark.parametrize("circuit_name", five_op_tests)
def test_five_qubit_qasm3_gates(circuit_name, request):
    qubit_list = [[0, 1, 2, 3, 4], [0, 1, 2, 3, 4]]
    gate_name = circuit_name.removeprefix("Fixture_")

    qasm3_string = request.getfixturevalue(circuit_name)
    result = loads(qasm3_string)
    # we do not want to validate every gate inside it
    result.unroll(external_gates=[gate_name])
    assert result.num_qubits == 5
    assert result.num_clbits == 0
    check_five_qubit_gate_op(result.unrolled_ast, 2, qubit_list, gate_name)


def test_gate_body_param_expression():
    qasm3_string = """
    OPENQASM 3;
    include "stdgates.inc";

    gate my_gate_2(p) q {
        ry(p * 2) q;
    }

    gate my_gate(a, b, c) q {
        rx(5 * a) q;
        rz(2 * b / a) q;
        my_gate_2(a) q;
        rx(!a) q; // not a = False
        rx(c) q;
    }

    qubit q;
    int[32] m = 3;
    float[32] n = 6.0;
    bool o = true;
    my_gate(m, n, o) q;
    """
    result = loads(qasm3_string)
    result.unroll()
    assert result.num_qubits == 1
    assert result.num_clbits == 0

    check_single_qubit_rotation_op(result.unrolled_ast, 3, [0, 0, 0], [5 * 3, 0.0, True], "rx")
    check_single_qubit_rotation_op(result.unrolled_ast, 1, [0], [2 * 6.0 / 3], "rz")
    check_single_qubit_rotation_op(result.unrolled_ast, 1, [0], [3 * 2], "ry")


def test_qasm_u3_gates():
    qasm3_string = """
    OPENQASM 3;
    include "stdgates.inc";

    qubit[2] q1;
    u3(0.5, 0.5, 0.5) q1[0];
    """
    result = loads(qasm3_string)
    result.unroll()
    assert result.num_qubits == 2
    assert result.num_clbits == 0
    check_single_qubit_rotation_op(result.unrolled_ast, 1, [0], [0.5, 0.5, 0.5], "u3")


def test_qasm_u3_gates_external():
    qasm3_string = """
    OPENQASM 3;
    include "stdgates.inc";

    qubit[2] q1;
    u3(0.5, 0.5, 0.5) q1[0];
    """
    result = loads(qasm3_string)
    result.unroll(external_gates=["u3"])
    assert result.num_qubits == 2
    assert result.num_clbits == 0
    check_single_qubit_gate_op(result.unrolled_ast, 1, [0], "u3")


def test_qasm_u3_gates_external_with_multiple_qubits():
    qasm3_string = """
    OPENQASM 3;
    include "stdgates.inc";

    qubit[2] q1;
    u3(0.5, 0.5, 0.5) q1;
    """
    result = loads(qasm3_string)
    result.unroll(external_gates=["u3"])
    assert result.num_qubits == 2
    assert result.num_clbits == 0
    check_single_qubit_gate_op(result.unrolled_ast, 2, [0, 1], "u3")


def test_qasm_u3_gates_external_with_ctrl():
    qasm3_string = """
    OPENQASM 3;
    include "stdgates.inc";
    qubit[2] q;
    ctrl @ u3(0.5, 0.5, 0.5) q[0], q[1];
    """
    expected_qasm = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[2] q;
    ctrl(1) @ u3(0.5, 0.5, 0.5) q[0], q[1];
    """
    result = loads(qasm3_string)
    result.unroll(external_gates=["u3"])
    check_unrolled_qasm(dumps(result), expected_qasm)


def test_qasm_u2_gates():
    qasm3_string = """
    OPENQASM 3;
    include "stdgates.inc";

    qubit[2] q1;
    u2(0.5, 0.5) q1[0];
    """
    result = loads(qasm3_string)
    result.unroll()
    assert result.num_qubits == 2
    assert result.num_clbits == 0
    check_single_qubit_rotation_op(result.unrolled_ast, 1, [0], [0.5, 0.5], "u2")


@pytest.mark.parametrize("test_name", custom_op_tests)
def test_custom_ops(test_name, request):
    qasm3_string = request.getfixturevalue(test_name)
    gate_type = test_name.removeprefix("Fixture_")
    result = loads(qasm3_string)
    result.unroll()

    assert result.num_qubits == 2
    assert result.num_clbits == 0

    # Check for custom gate definition
    check_custom_qasm_gate_op(result.unrolled_ast, gate_type)


def test_global_phase_gate():
    qasm3_string = """OPENQASM 3.0;
    qubit[2] q;
    gphase(pi/4);
    """

    qasm3_expected = """
    OPENQASM 3.0;
    qubit[2] q;
    gphase(0.7853981633974483);
    """
    module = loads(qasm3_string)
    module.unroll()

    assert module.num_qubits == 2
    assert module.num_clbits == 0

    check_unrolled_qasm(dumps(module), qasm3_expected)


def test_global_phase_qubits_retained():
    """Test that global phase gate is retained when applied on specific qubits"""
    qasm3_string = """OPENQASM 3.0;
    gate custom a,b,c { 
       gphase(pi/8);
       h a;
    }
    qubit[23] q2;
    custom q2[0:3];
    """

    qasm3_expected = """
    OPENQASM 3.0;
    qubit[23] q2;
    gphase(0.39269908169872414) q2[0], q2[1], q2[2];
    h q2[0];
    """
    module = loads(qasm3_string)
    module.unroll()

    assert module.num_qubits == 23
    assert module.num_clbits == 0

    check_unrolled_qasm(dumps(module), qasm3_expected)


def test_global_phase_qubits_simplified():
    """Test that the global phase gate is simplified when applied on all qubits"""
    qasm3_string = """OPENQASM 3.0;
    qubit[3] q2;
    gate custom a,b,c {
        gphase(pi/8) a, b, c;
    }
    custom q2;
    """

    qasm3_expected = """
    OPENQASM 3.0;
    qubit[3] q2;
    gphase(0.39269908169872414);
    """
    module = loads(qasm3_string)
    module.unroll()

    assert module.num_qubits == 3
    assert module.num_clbits == 0

    check_unrolled_qasm(dumps(module), qasm3_expected)


def test_inverse_global_phase():
    """Test that the inverse of global phase gate is simplified"""
    qasm3_string = """OPENQASM 3.0;
    qubit[3] q2;
    gate custom a,b,c {
        inv @ gphase(pi/8) a, b, c;
    }
    custom q2;
    """

    qasm3_expected = """
    OPENQASM 3.0;
    qubit[3] q2;
    gphase(-0.39269908169872414);
    """
    module = loads(qasm3_string)
    module.unroll()

    assert module.num_qubits == 3
    assert module.num_clbits == 0

    check_unrolled_qasm(dumps(module), qasm3_expected)


def test_duplicate_qubit_broadcast():
    qasm3_string = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[3] q;
    
    cx q[0], q[1], q[1], q[2];"""

    module = loads(qasm3_string)
    module.unroll()

    assert module.num_qubits == 3
    assert module.num_clbits == 0

    check_two_qubit_gate_op(module.unrolled_ast, 2, [[0, 1], [1, 2]], "cx")


@pytest.mark.parametrize("test_name", custom_op_tests)
def test_custom_ops_with_external_gates(test_name, request):
    qasm3_string = request.getfixturevalue(test_name)
    gate_type = test_name.removeprefix("Fixture_")
    result = loads(qasm3_string)
    result.unroll(external_gates=["custom", "custom1"])

    assert result.num_qubits == 2
    assert result.num_clbits == 0

    # Check for custom gate definition
    check_custom_qasm_gate_op_with_external_gates(result.unrolled_ast, gate_type)


def test_pow_gate_modifier():
    qasm3_string = """
    OPENQASM 3;
    include "stdgates.inc";
    qubit q;
    inv @ pow(2) @ pow(4) @ h q;
    pow(-2) @ h q;
    """
    result = loads(qasm3_string)
    result.unroll()
    assert result.num_qubits == 1
    assert result.num_clbits == 0
    check_single_qubit_gate_op(result.unrolled_ast, 10, [0] * 10, "h")


def test_inv_gate_modifier():
    qasm3_string = """
    OPENQASM 3;
    include "stdgates.inc";
    qubit q;
    inv @ h q;
    inv @ y q;
    inv @ rx(0.5) q;
    inv @ s q;

    qubit[2] q2;
    inv @ cx q2;
    inv @ ccx q[0], q2;
    """
    result = loads(qasm3_string)
    result.unroll()
    assert result.num_qubits == 3
    assert result.num_clbits == 0
    check_single_qubit_gate_op(result.unrolled_ast, 1, [0], "h")
    check_single_qubit_gate_op(result.unrolled_ast, 1, [0], "y")
    check_single_qubit_rotation_op(result.unrolled_ast, 1, [0], [-0.5], "rx")
    check_single_qubit_gate_op(result.unrolled_ast, 1, [0], "sdg")
    check_two_qubit_gate_op(result.unrolled_ast, 1, [[0, 1]], "cx")
    check_three_qubit_gate_op(result.unrolled_ast, 1, [[0, 0, 1]], "ccx")


def test_ctrl_gate_modifier():
    qasm3_string = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[4] q;
    ctrl @ z q[0], q[1];
    ctrl @ ctrl @ x q[0], q[1], q[2];
    ctrl(2) @ x q[1], q[2], q[3];
    """
    result = loads(qasm3_string)
    result.unroll()
    assert result.num_qubits == 4
    check_two_qubit_gate_op(result.unrolled_ast, 1, [[0, 1]], "cz")
    check_three_qubit_gate_op(result.unrolled_ast, 2, [[0, 1, 2], [1, 2, 3]], "ccx")


@pytest.mark.parametrize(
    "gate_name, num_qubits",
    [("c3x", 4), ("rc3x", 4), ("rcccx", 4), ("c4x", 5)],
)
def test_multi_controlled_x_decomposition(gate_name, num_qubits):
    """c3x / rc3x / c4x fully decompose into supported basis gates."""
    qubits = ", ".join(f"q[{i}]" for i in range(num_qubits))
    qasm3_string = f"""
    OPENQASM 3;
    include "stdgates.inc";
    qubit[{num_qubits}] q;
    {gate_name} {qubits};
    """
    result = loads(qasm3_string)
    result.unroll()
    assert result.num_qubits == num_qubits

    # The high-level gate is decomposed away, leaving only basis gates.
    allowed = {"h", "p", "cx", "t", "tdg", "rx", "rz", "x", "z", "cp", "ccx"}
    seen = set()
    for stmt in result.unrolled_ast.statements:
        if isinstance(stmt, qasm3_ast.QuantumGate):
            seen.add(stmt.name.name)
    assert gate_name not in seen
    assert seen.issubset(allowed), f"unexpected gates produced: {seen - allowed}"


@pytest.mark.parametrize(
    "named, chained, num_qubits",
    [
        # 3-controlled X: c3x == ctrl@ctrl@ctrl@x == ctrl@ccx
        ("c3x q[0], q[1], q[2], q[3];", "ctrl @ ctrl @ ctrl @ x q[0], q[1], q[2], q[3];", 4),
        ("c3x q[0], q[1], q[2], q[3];", "ctrl @ ccx q[0], q[1], q[2], q[3];", 4),
        # 4-controlled X: c4x == ctrl(4)@x == ctrl@c3x
        (
            "c4x q[0], q[1], q[2], q[3], q[4];",
            "ctrl(4) @ x q[0], q[1], q[2], q[3], q[4];",
            5,
        ),
        (
            "c4x q[0], q[1], q[2], q[3], q[4];",
            "ctrl @ c3x q[0], q[1], q[2], q[3], q[4];",
            5,
        ),
    ],
)
def test_ctrl_chain_beyond_two_controls(named, chained, num_qubits):
    """The ctrl modifier chain resolves beyond two controls via c3x / c4x."""
    header = f'OPENQASM 3;\ninclude "stdgates.inc";\nqubit[{num_qubits}] q;\n'

    named_result = loads(header + named)
    named_result.unroll()

    chained_result = loads(header + chained)
    chained_result.unroll()

    assert dumps(named_result) == dumps(chained_result)


@pytest.mark.parametrize(
    "alias, canonical, num_qubits",
    [
        # Gate aliases must escalate controls identically to their canonical gate.
        ("ctrl @ cnot q[0], q[1], q[2];", "ctrl @ cx q[0], q[1], q[2];", 3),
        ("ctrl @ CX q[0], q[1], q[2];", "ctrl @ cx q[0], q[1], q[2];", 3),
        ("ctrl @ toffoli q[0], q[1], q[2], q[3];", "ctrl @ ccx q[0], q[1], q[2], q[3];", 4),
        ("ctrl @ ccnot q[0], q[1], q[2], q[3];", "ctrl @ ccx q[0], q[1], q[2], q[3];", 4),
        (
            "ctrl @ ctrl @ toffoli q[0], q[1], q[2], q[3], q[4];",
            "c4x q[0], q[1], q[2], q[3], q[4];",
            5,
        ),
    ],
)
def test_ctrl_chain_resolves_gate_aliases(alias, canonical, num_qubits):
    """Controlling an aliased gate (cnot/CX/toffoli/ccnot) matches the canonical gate."""
    header = f'OPENQASM 3;\ninclude "stdgates.inc";\nqubit[{num_qubits}] q;\n'

    alias_result = loads(header + alias)
    alias_result.unroll()

    canonical_result = loads(header + canonical)
    canonical_result.unroll()

    assert dumps(alias_result) == dumps(canonical_result)


def _unrolled_unitary(body, num_qubits):
    """Unroll a single-statement program and return its realised operator."""
    header = f'OPENQASM 3;\ninclude "stdgates.inc";\nqubit[{num_qubits}] q;\n'
    module = loads(header + body)
    module.unroll()
    return unitary_from_unrolled_ast(module.unrolled_ast, num_qubits)


@pytest.mark.parametrize(
    "body, num_qubits",
    [
        # Every spelling of the 3- and 4-controlled X must realise the same MCX
        # operator. This is the real correctness check: a wrong angle or a
        # swapped control/target survives a structural test but not this one.
        ("c3x q[0], q[1], q[2], q[3];", 4),
        ("ctrl @ ccx q[0], q[1], q[2], q[3];", 4),
        ("ctrl @ ctrl @ ctrl @ x q[0], q[1], q[2], q[3];", 4),
        ("ctrl @ ctrl @ cx q[0], q[1], q[2], q[3];", 4),
        ("c4x q[0], q[1], q[2], q[3], q[4];", 5),
        ("ctrl(4) @ x q[0], q[1], q[2], q[3], q[4];", 5),
        ("ctrl @ c3x q[0], q[1], q[2], q[3], q[4];", 5),
    ],
)
def test_multi_controlled_x_realises_mcx(body, num_qubits):
    """c3x / c4x and their ctrl-chain equivalents implement the exact MCX unitary."""
    assert_unitary_equal(_unrolled_unitary(body, num_qubits), mcx_unitary(num_qubits))


@pytest.mark.parametrize(
    "body, num_qubits, target",
    [
        # The target is the *last* listed qubit, not the highest index. Permuting
        # the operands must move the target accordingly.
        ("c3x q[3], q[0], q[1], q[2];", 4, 2),
        ("c3x q[1], q[3], q[0], q[2];", 4, 2),
        ("c4x q[4], q[3], q[2], q[1], q[0];", 5, 0),
    ],
)
def test_multi_controlled_x_operand_order(body, num_qubits, target):
    """Operand ordering selects the correct target qubit for the controlled-X."""
    assert_unitary_equal(
        _unrolled_unitary(body, num_qubits), mcx_unitary(num_qubits, target=target)
    )


def test_rc3x_is_relative_phase_toffoli():
    """rc3x / rcccx is a relative-phase 3-controlled X: |U| matches the Toffoli."""
    rc3x_u = _unrolled_unitary("rc3x q[0], q[1], q[2], q[3];", 4)
    rcccx_u = _unrolled_unitary("rcccx q[0], q[1], q[2], q[3];", 4)
    toffoli3 = mcx_unitary(4)

    # rcccx is an alias for rc3x.
    assert np.allclose(rc3x_u, rcccx_u, atol=1e-7)
    # It must be unitary and share the Toffoli's permutation structure...
    assert np.allclose(rc3x_u @ rc3x_u.conj().T, np.eye(16), atol=1e-7)
    assert np.allclose(np.abs(rc3x_u), toffoli3, atol=1e-7)
    # ...but it is NOT the true Toffoli: it carries relative phases (that is the
    # whole point of the cheaper relative-phase decomposition).
    assert not np.allclose(rc3x_u, toffoli3, atol=1e-7)


@pytest.mark.parametrize(
    "body, num_qubits, reference",
    [
        # inv @ <self-inverse gate> must round-trip back to the gate itself.
        ("inv @ c3x q[0], q[1], q[2], q[3];", 4, lambda: mcx_unitary(4)),
        ("inv @ c4x q[0], q[1], q[2], q[3], q[4];", 5, lambda: mcx_unitary(5)),
    ],
)
def test_inverse_modifier_on_multi_controlled_x(body, num_qubits, reference):
    """inv @ c3x / c4x is supported and equals the (self-inverse) gate."""
    assert_unitary_equal(_unrolled_unitary(body, num_qubits), reference())


@pytest.mark.parametrize("gate", ["rc3x", "rcccx"])
def test_inverse_modifier_on_rc3x_round_trips(gate):
    """rc3x is not self-inverse, but inv @ rc3x is its true dagger (round-trips to I)."""
    body = f"{gate} q[0], q[1], q[2], q[3];\ninv @ {gate} q[0], q[1], q[2], q[3];"
    assert_unitary_equal(_unrolled_unitary(body, 4), np.eye(16))


def test_negctrl_chain_on_multi_controlled_x():
    """A negctrl mixed into the control chain flips on the |0> state of that control."""
    body = "negctrl @ ctrl @ ctrl @ x q[0], q[1], q[2], q[3];"
    actual = _unrolled_unitary(body, 4)

    expected = np.zeros((16, 16), dtype=complex)
    for basis in range(16):
        q0, q1, q2 = basis & 1, (basis >> 1) & 1, (basis >> 2) & 1
        # control q0 is negative (active on 0), q1/q2 positive, target is q3
        dest = basis ^ (1 << 3) if (q0 == 0 and q1 == 1 and q2 == 1) else basis
        expected[dest, basis] = 1
    assert_unitary_equal(actual, expected)


@pytest.mark.parametrize(
    "body, num_qubits",
    [
        # c4x has no controlled form (c5x is not defined), so a further control
        # cannot be resolved and must raise rather than silently mis-decompose.
        ("ctrl @ c4x q[0], q[1], q[2], q[3], q[4], q[5];", 6),
        ("ctrl(5) @ x q[0], q[1], q[2], q[3], q[4], q[5];", 6),
    ],
)
def test_too_many_controls_raises(body, num_qubits):
    """Control chains requiring an undefined gate raise a clear ValidationError."""
    header = f'OPENQASM 3;\ninclude "stdgates.inc";\nqubit[{num_qubits}] q;\n'
    with pytest.raises(ValidationError, match="controlled QASM operation"):
        loads(header + body).unroll()


def test_inverse_of_unsupported_four_qubit_gate_raises():
    """c3sx has no inverse decomposition; inv @ c3sx must fail loudly, not silently."""
    qasm3_string = """
    OPENQASM 3;
    include "stdgates.inc";
    qubit[4] q;
    inv @ c3sx q[0], q[1], q[2], q[3];
    """
    with pytest.raises(ValidationError, match="Unsupported / undeclared QASM operation"):
        loads(qasm3_string).unroll()


def test_negctrl_gate_modifier():
    qasm3_string = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[2] q;
    negctrl @ z q[0], q[1];
    """
    result = loads(qasm3_string)
    result.unroll()
    assert result.num_qubits == 2
    check_single_qubit_gate_op(result.unrolled_ast, 2, [0, 0], "x")
    check_two_qubit_gate_op(result.unrolled_ast, 1, [[0, 1]], "cz")


def test_ctrl_in_custom_gate():
    qasm3_string = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[3] q;
    gate custom a, b, c {
        ctrl @ x a, b;
        ctrl(2) @ x a, b, c;
    }
    custom q[0], q[1], q[2];
    """
    result = loads(qasm3_string)
    result.unroll()
    assert result.num_qubits == 3
    assert result.num_clbits == 0
    check_two_qubit_gate_op(result.unrolled_ast, 1, [[0, 1]], "cx")
    check_three_qubit_gate_op(result.unrolled_ast, 1, [[0, 1, 2]], "ccx")


def test_ctrl_in_subroutine():
    qasm3_string = """
    OPENQASM 3.0;
    include "stdgates.inc";
    def f(qubit a, qubit b) {
        ctrl @ x a, b;
        return;
    }
    qubit[2] q;
    f(q[0], q[1]);
    """

    result = loads(qasm3_string)
    result.unroll()
    assert result.num_qubits == 2
    assert result.num_clbits == 0
    check_two_qubit_gate_op(result.unrolled_ast, 1, [[0, 1]], "cx")


def test_ctrl_in_if_block():
    qasm3_string = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[2] q;
    bit b;
    b = measure q[0];
    if(b == 1) {
        ctrl @ x q[0], q[1];
    }
    """
    expected_qasm = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[2] q;
    bit[1] b;
    b[0] = measure q[0];
    if (b[0] == true) {
        cx q[0], q[1];
    }
    """
    result = loads(qasm3_string)
    result.unroll()
    check_unrolled_qasm(dumps(result), expected_qasm)


def test_ctrl_in_for_loop():
    qasm3_string = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[4] q;

    for int i in [0:2]{
        ctrl @ x q[i], q[i+1];
    }
    """
    result = loads(qasm3_string)
    result.unroll()
    assert result.num_qubits == 4
    check_two_qubit_gate_op(result.unrolled_ast, 3, [(0, 1), (1, 2), (2, 3)], "cx")


def test_ctrl_unroll():
    qasm3_string = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[2] a;
    qubit b;
    ctrl (2) @ x a, b[0];
    """
    expected_qasm = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[2] a;
    qubit[1] b;
    ccx a[0], a[1], b[0];
    """
    result = loads(qasm3_string)
    result.unroll()
    check_unrolled_qasm(dumps(result), expected_qasm)


def test_ctrl_gphase_eq_p():
    qasm3_str_gphase = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit a;
    ctrl @ gphase(1) a;
    """
    qasm3_str_p = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit a;
    p(1) a;
    """
    result_gphase, result_p = loads(qasm3_str_gphase), loads(qasm3_str_p)
    result_gphase.unroll()
    result_p.unroll()
    check_unrolled_qasm(dumps(result_gphase), dumps(result_p))


def test_nested_gate_modifiers():
    qasm3_string = """
    OPENQASM 3;
    include "stdgates.inc";
    qubit[3] q;
    gate custom2 p, q{
        x p;
        z q;
        ctrl @ x q, p;
    }
    gate custom p, q {
        pow(1) @ custom2 p, q;
    }
    pow(1) @ inv @ pow(2) @ custom q[0], q[1];
    ctrl @ pow(-1) @ custom q[0], q[1], q[2];
    """
    result = loads(qasm3_string)
    result.unroll()
    assert result.num_qubits == 3
    assert result.num_clbits == 0
    check_single_qubit_gate_op(result.unrolled_ast, 2, [1, 1, 1], "z")
    check_single_qubit_gate_op(result.unrolled_ast, 2, [0, 0, 0], "x")
    check_two_qubit_gate_op(result.unrolled_ast, 1, [[0, 2]], "cz")
    check_two_qubit_gate_op(result.unrolled_ast, 3, [[1, 0], [1, 0], [0, 1]], "cx")
    check_three_qubit_gate_op(result.unrolled_ast, 1, [[0, 2, 1]], "ccx")


@pytest.mark.parametrize(
    "test",
    [
        (
            """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[2] q;
    h q;
    bit b;
    b = measure q[0];
    ctrl(b+1) @ x q[0], q[1];
    """,
            "Controlled modifier arguments must be compile-time constants.*",
            8,
            4,
            "ctrl(b + 1) @ x q[0], q[1];",
        ),
        (
            """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[2] q;
    ctrl(1.5) @ x q[0], q[1];
    """,
            "Controlled modifier argument must be a positive integer.*",
            5,
            4,
            "ctrl(1.5) @ x q[0], q[1];",
        ),
        (
            """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit q;
    pow(1.5) @ x q;
    """,
            "Power modifier argument must be an integer.*",
            5,
            4,
            "pow(1.5) @ x q[0];",
        ),
    ],
)
def test_modifier_arg_error(test, caplog):
    qasm3_string, error_message, line_num, col_num, line = test
    with pytest.raises(ValidationError, match=error_message):
        with caplog.at_level("ERROR"):
            loads(qasm3_string).validate()

    assert f"Error at line {line_num}, column {col_num}" in caplog.text
    assert line in caplog.text


@pytest.mark.parametrize("test_name", CUSTOM_GATE_INCORRECT_TESTS.keys())
def test_incorrect_custom_ops(test_name, caplog):
    qasm_input, error_message, line_num, col_num, line = CUSTOM_GATE_INCORRECT_TESTS[test_name]
    with pytest.raises(ValidationError, match=error_message):
        with caplog.at_level("ERROR"):
            loads(qasm_input).validate()

    assert f"Error at line {line_num}, column {col_num}" in caplog.text
    assert line in caplog.text


@pytest.mark.parametrize("test_name", SINGLE_QUBIT_GATE_INCORRECT_TESTS.keys())
def test_incorrect_single_qubit_gates(test_name, caplog):
    qasm_input, error_message, line_num, col_num, line = SINGLE_QUBIT_GATE_INCORRECT_TESTS[
        test_name
    ]
    with pytest.raises(ValidationError, match=error_message):
        with caplog.at_level("ERROR"):
            loads(qasm_input).validate()

    assert f"Error at line {line_num}, column {col_num}" in caplog.text
    assert line in caplog.text


# ── Physical-qubit tests ────────────────────────────────────────────────────


@pytest.mark.parametrize("test_name", PHYSICAL_QUBIT_VALID_TESTS.keys())
def test_physical_qubit_validate(test_name):
    qasm_input, expected_qubits, expected_clbits = PHYSICAL_QUBIT_VALID_TESTS[test_name]
    result = loads(qasm_input)
    result.validate()
    assert result.num_qubits == expected_qubits
    assert result.num_clbits == expected_clbits


def test_physical_qubit_unroll():
    """Physical qubits inside a custom gate are expanded without errors."""
    qasm_input = """
    OPENQASM 3.0;
    include "stdgates.inc";
    gate my_rx(p) q { rx(p) q; }
    my_rx(0.5) $0;
    """
    result = loads(qasm_input)
    result.unroll()
    assert result.num_qubits == 1
    assert result.num_clbits == 0


def test_physical_qubit_duplicate_detection():
    """Duplicate physical qubits in a two-qubit gate are caught."""
    qasm_input = """
    OPENQASM 3.0;
    include "stdgates.inc";
    cx $0, $0;
    """
    with pytest.raises(ValidationError, match=r"Duplicate qubit"):
        loads(qasm_input).validate()
