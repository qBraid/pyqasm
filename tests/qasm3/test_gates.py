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
Module containing unit tests for unrolling quantum gates.

"""
import pytest

from pyqasm.entrypoint import dumps, loads
from pyqasm.exceptions import ValidationError
from tests.qasm3.resources.gates import (
    CUSTOM_GATE_INCORRECT_TESTS,
    SINGLE_QUBIT_GATE_INCORRECT_TESTS,
    custom_op_tests,
    double_op_tests,
    four_op_tests,
    rotation_tests,
    single_op_tests,
    triple_op_tests,
)
from tests.utils import (
    check_custom_qasm_gate_op,
    check_custom_qasm_gate_op_with_external_gates,
    check_four_qubit_gate_op,
    check_single_qubit_gate_op,
    check_single_qubit_rotation_op,
    check_three_qubit_gate_op,
    check_two_qubit_gate_op,
    check_unrolled_qasm,
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


@pytest.mark.parametrize("test_name", SINGLE_QUBIT_GATE_INCORRECT_TESTS.keys())
def test_incorrect_single_qubit_gates(test_name):
    qasm_input, error_message = SINGLE_QUBIT_GATE_INCORRECT_TESTS[test_name]
    with pytest.raises(ValidationError, match=error_message):
        loads(qasm_input).validate()


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


def test_nested_gate_modifiers():
    qasm3_string = """
    OPENQASM 3;
    include "stdgates.inc";
    qubit[2] q;
    gate custom2 p, q{
        y p;
        z q;
    }
    gate custom p, q {
        pow(1) @ custom2 p, q;
    }
    pow(1) @ inv @ pow(2) @ custom q;
    pow(-1) @ custom q;
    """
    result = loads(qasm3_string)
    result.unroll()
    assert result.num_qubits == 2
    assert result.num_clbits == 0
    check_single_qubit_gate_op(result.unrolled_ast, 3, [1, 1, 1], "z")
    check_single_qubit_gate_op(result.unrolled_ast, 3, [0, 0, 0], "y")


def test_unsupported_modifiers():
    # TO DO : add implementations, but till then we have tests
    for modifier in ["ctrl", "negctrl"]:
        with pytest.raises(
            NotImplementedError,
            match=r"Controlled modifier gates not yet supported .*",
        ):
            loads(
                f"""
                OPENQASM 3;
                include "stdgates.inc";
                qubit[2] q;
                {modifier} @ h q[0], q[1];
                """
            ).validate()


@pytest.mark.parametrize("test_name", CUSTOM_GATE_INCORRECT_TESTS.keys())
def test_incorrect_custom_ops(test_name):
    qasm_input, error_message = CUSTOM_GATE_INCORRECT_TESTS[test_name]
    with pytest.raises(ValidationError, match=error_message):
        loads(qasm_input).validate()
