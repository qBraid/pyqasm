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
