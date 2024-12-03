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
Module containing utility functions for unit tests.

"""
import openqasm3.ast as qasm3_ast

from pyqasm.maps import CONSTANTS_MAP

CONTROLLED_ROTATION_TEST_ANGLE = 0.5


def check_unrolled_qasm(unrolled_qasm, expected_qasm):
    """Check that the unrolled qasm matches the expected qasm.

    Args:
        unrolled_qasm (str): The unrolled qasm to check.
        expected_qasm (str): The expected qasm to check against

    Raises:
        AssertionError: If the unrolled qasm does not match the expected qasm.
    """
    # check line by line
    unrolled_qasm = [line for line in unrolled_qasm.split("\n") if line.strip()]
    expected_qasm = [line for line in expected_qasm.split("\n") if line.strip()]

    assert len(unrolled_qasm) == len(expected_qasm)

    for unrolled_line, expected_line in zip(unrolled_qasm, expected_qasm):
        # replace ' with " for comparison
        unrolled_line = unrolled_line.replace("'", '"')
        expected_line = expected_line.replace("'", '"')
        assert unrolled_line.strip() == expected_line.strip()


def check_single_qubit_gate_op(unrolled_ast, num_gates, qubit_list, gate_name):
    qubit_id, gate_count = 0, 0
    for stmt in unrolled_ast.statements:
        if isinstance(stmt, qasm3_ast.QuantumGate) and stmt.name.name == gate_name:
            assert len(stmt.qubits) == 1
            assert stmt.qubits[0].indices[0][0].value == qubit_list[qubit_id]
            qubit_id += 1
            gate_count += 1

    assert gate_count == num_gates


def check_global_phase_op(unrolled_ast, num_gates, qubit_list, phase_list):
    # qubit_list is list [list]
    # qubit_list = [ [], [0,1,2], [3,4,5] ] means gphase applied on ALL , 3 , 3 qubits  with given
    # phase values
    qubits_id, phase_id = 0, 0
    gate_count = 0
    for stmt in unrolled_ast.statements:
        if isinstance(stmt, qasm3_ast.QuantumPhase):
            assert len(stmt.qubits) == len(qubit_list[qubits_id])
            assert stmt.argument.value == phase_list[phase_id]
            for i, _ in enumerate(stmt.qubits):
                assert stmt.qubits[i].indices[0][0].value == qubit_list[qubits_id][i]
            qubits_id += 1
            phase_id += 1
            gate_count += 1

    assert gate_count == num_gates


def _check_ch_gate_op(unrolled_ast, num_gates, qubits):
    check_single_qubit_gate_op(unrolled_ast, num_gates, [qubits[1]] * num_gates, "s")
    check_single_qubit_gate_op(unrolled_ast, 2 * num_gates, [qubits[1]] * 2 * num_gates, "h")
    check_single_qubit_gate_op(unrolled_ast, num_gates, [qubits[1]] * num_gates, "t")
    check_two_qubit_gate_op(unrolled_ast, num_gates, [qubits] * num_gates, "cx")
    check_single_qubit_gate_op(unrolled_ast, num_gates, [qubits[1]] * num_gates, "tdg")
    check_single_qubit_gate_op(unrolled_ast, num_gates, [qubits[1]] * num_gates, "sdg")


def _check_iswap_gate_op(unrolled_ast, num_gates, qubits):
    check_single_qubit_gate_op(unrolled_ast, 2 * num_gates, qubits * num_gates, "s")
    cx_gate_qubits = [qubits, qubits[::-1]] * num_gates
    check_two_qubit_gate_op(unrolled_ast, 2 * num_gates, cx_gate_qubits, "cx")
    check_single_qubit_gate_op(unrolled_ast, 2 * num_gates, qubits * num_gates, "h")


def _check_crx_gate_op(unrolled_ast, num_gates, qubits, theta):
    num_u3_gates = 3 * num_gates
    check_u3_gate_op(
        unrolled_ast,
        num_u3_gates,
        [qubits[1]] * num_u3_gates,
        [
            [0, 0, CONSTANTS_MAP["pi"] / 2],
            [-1 * theta / 2, 0, 0],
            [theta / 2, -CONSTANTS_MAP["pi"] / 2, 0],
        ]
        * num_gates,
    )

    num_cx_gates = 2 * num_gates
    check_two_qubit_gate_op(unrolled_ast, num_cx_gates, [qubits] * num_cx_gates, "cx")


def _check_crz_gate_op(unrolled_ast, num_gates, qubits, theta):
    num_u3_gates = 2 * num_gates
    num_cx_gates = 2 * num_gates
    check_u3_gate_op(
        unrolled_ast,
        num_u3_gates,
        [qubits[1]] * num_u3_gates,
        [
            [0, 0, theta / 2],
            [0, 0, -theta / 2],
        ]
        * num_gates,
    )
    check_two_qubit_gate_op(unrolled_ast, num_cx_gates, [qubits] * num_u3_gates, "cx")


def _check_cry_gate_op(unrolled_ast, num_gates, qubits, theta):
    num_u3_gates = 2 * num_gates
    num_cx_gates = 2 * num_gates
    check_u3_gate_op(
        unrolled_ast,
        num_u3_gates,
        [qubits[1]] * num_u3_gates,
        [
            [theta / 2, 0, 0],
            [-theta / 2, 0, 0],
        ]
        * num_gates,
    )
    check_two_qubit_gate_op(unrolled_ast, num_cx_gates, [qubits] * num_u3_gates, "cx")


def _check_rxx_gate_op(unrolled_ast, num_gates, qubits, theta):
    num_global_phase = num_gates
    num_h_gates = 4 * num_gates
    # because H is applied as H(q0) H(q1) H(q1) H(q0) in  1 rxx gate
    h_qubit_list = (qubits + qubits[::-1]) * num_gates
    num_cx_gates = 2 * num_gates
    num_rz_gates = num_gates
    check_global_phase_op(
        unrolled_ast, num_global_phase, [[]] * num_gates, [-theta / 2] * num_gates
    )
    check_single_qubit_gate_op(unrolled_ast, num_h_gates, h_qubit_list, "h")
    check_two_qubit_gate_op(unrolled_ast, num_cx_gates, [qubits] * num_cx_gates, "cx")
    check_single_qubit_rotation_op(
        unrolled_ast, num_rz_gates, [qubits[1]] * num_gates, [theta] * num_gates, "rz"
    )


def _check_ryy_gate_op(unrolled_ast, num_gates, qubits, theta):
    num_rx_gates = 4 * num_gates
    rx_qubit_list = qubits * 2 * num_gates
    rx_param_list = [
        CONSTANTS_MAP["pi"] / 2,
        CONSTANTS_MAP["pi"] / 2,
        -CONSTANTS_MAP["pi"] / 2,
        -CONSTANTS_MAP["pi"] / 2,
    ] * num_gates
    num_cx_gates = 2 * num_gates
    cx_qubit_list = [qubits, qubits] * num_gates
    num_rz_gates = num_gates

    check_single_qubit_rotation_op(unrolled_ast, num_rx_gates, rx_qubit_list, rx_param_list, "rx")
    check_two_qubit_gate_op(unrolled_ast, num_cx_gates, cx_qubit_list, "cx")
    check_single_qubit_rotation_op(
        unrolled_ast, num_rz_gates, [qubits[1]] * num_gates, [theta] * num_gates, "rz"
    )


def _check_rzz_gate_op(unrolled_ast, num_gates, qubits, theta):
    num_global_phase = num_gates
    num_cx_gates = 2 * num_gates
    num_u3_gates = num_gates

    check_global_phase_op(
        unrolled_ast, num_global_phase, [[]] * num_gates, [-theta / 2] * num_gates
    )
    check_two_qubit_gate_op(unrolled_ast, num_cx_gates, [qubits] * num_cx_gates, "cx")
    check_u3_gate_op(
        unrolled_ast,
        num_u3_gates,
        [qubits[1]] * num_u3_gates,
        [
            [0, 0, theta],
        ]
        * num_gates,
    )


def _check_xx_yy_gate_op(unrolled_ast, num_gates, qubits, theta):
    phi = theta
    num_rz_gates = 6 * num_gates
    rz_qubit_list = [qubits[0], qubits[1], qubits[0]] * 2 * num_gates
    rz_param_list = [
        phi,
        -1 * CONSTANTS_MAP["pi"] / 2,
        CONSTANTS_MAP["pi"] / 2,
        -1 * CONSTANTS_MAP["pi"] / 2,
        CONSTANTS_MAP["pi"] / 2,
        -1 * phi,
    ] * num_gates
    num_cx_gates = 2 * num_gates
    cx_qubit_list = [qubits[::-1]] * num_cx_gates
    num_ry_gates = 2 * num_gates
    ry_qubit_list = qubits * num_ry_gates
    ry_param_list = [-1 * theta / 2] * num_ry_gates

    check_single_qubit_rotation_op(unrolled_ast, num_rz_gates, rz_qubit_list, rz_param_list, "rz")
    check_single_qubit_gate_op(unrolled_ast, num_gates, [qubits[0]] * num_gates, "s")
    check_single_qubit_gate_op(unrolled_ast, num_gates, [qubits[1]] * num_gates, "sx")
    check_two_qubit_gate_op(unrolled_ast, num_cx_gates, cx_qubit_list, "cx")
    check_single_qubit_rotation_op(unrolled_ast, num_ry_gates, ry_qubit_list, ry_param_list, "ry")
    check_single_qubit_gate_op(unrolled_ast, num_gates, [qubits[1]] * num_gates, "sxdg")
    check_single_qubit_gate_op(unrolled_ast, num_gates, [qubits[0]] * num_gates, "sdg")


def check_two_qubit_gate_op(unrolled_ast, num_gates, qubit_list, gate_name):
    qubit_id, gate_count = 0, 0
    if gate_name == "cnot":
        gate_name = "cx"

    controlled_gate_tests = {"ch": _check_ch_gate_op, "iswap": _check_iswap_gate_op}
    controlled_rotation_gate_tests = {
        "crx": _check_crx_gate_op,
        "crz": _check_crz_gate_op,
        "cry": _check_cry_gate_op,
        "rxx": _check_rxx_gate_op,
        "ryy": _check_ryy_gate_op,
        "rzz": _check_rzz_gate_op,
        "xx_plus_yy": _check_xx_yy_gate_op,
    }
    if gate_name in controlled_gate_tests:
        controlled_gate_tests[gate_name](unrolled_ast, num_gates, qubit_list[0])
    elif gate_name in controlled_rotation_gate_tests:
        controlled_rotation_gate_tests[gate_name](
            unrolled_ast, num_gates, qubit_list[0], CONTROLLED_ROTATION_TEST_ANGLE
        )
    else:
        for stmt in unrolled_ast.statements:
            if isinstance(stmt, qasm3_ast.QuantumGate) and stmt.name.name == gate_name.lower():
                assert len(stmt.qubits) == 2
                assert stmt.qubits[0].indices[0][0].value == qubit_list[qubit_id][0]
                assert stmt.qubits[1].indices[0][0].value == qubit_list[qubit_id][1]
                qubit_id += 1
                gate_count += 1

        assert gate_count == num_gates


def check_three_qubit_gate_op(unrolled_ast, num_gates, qubit_list, gate_name):
    qubit_id, gate_count = 0, 0

    for stmt in unrolled_ast.statements:
        if isinstance(stmt, qasm3_ast.QuantumGate) and stmt.name.name == gate_name.lower():
            assert len(stmt.qubits) == 3
            assert stmt.qubits[0].indices[0][0].value == qubit_list[qubit_id][0]
            assert stmt.qubits[1].indices[0][0].value == qubit_list[qubit_id][1]
            assert stmt.qubits[2].indices[0][0].value == qubit_list[qubit_id][2]
            qubit_id += 1
            gate_count += 1

    assert gate_count == num_gates


def check_four_qubit_gate_op(unrolled_ast, num_gates, qubit_list, gate_name):
    qubit_id, gate_count = 0, 0

    for stmt in unrolled_ast.statements:
        if isinstance(stmt, qasm3_ast.QuantumGate) and stmt.name.name == gate_name.lower():
            assert len(stmt.qubits) == 4
            for i in range(4):
                assert stmt.qubits[i].indices[0][0].value == qubit_list[qubit_id][i]
            qubit_id += 1
            gate_count += 1

    assert gate_count == num_gates


def check_u3_gate_op(unrolled_ast, num_gates, qubit_list, param_list):
    op_count = 0
    q_id = 0
    pi = CONSTANTS_MAP["pi"]
    u3_gate_list = ["rz", "rx", "rz", "rx", "rz"]

    for params in param_list:
        theta, phi, lam = params
        u3_param_list = [lam, pi / 2, theta + pi, pi / 2, phi + pi]
        u3_gates_id = 0

        for stmt in unrolled_ast.statements:
            if (
                isinstance(stmt, qasm3_ast.QuantumGate)
                and stmt.name.name == u3_gate_list[u3_gates_id]
                and len(stmt.qubits) == 1
                and stmt.qubits[0].indices[0][0].value == qubit_list[q_id]
                and stmt.arguments[0].value == u3_param_list[u3_gates_id]
            ):
                u3_gates_id += 1
                if u3_gates_id == 5:
                    u3_gates_id = 0
                    op_count += 1
                    q_id += 1
                    break  # break out of the loop to check the next set of params

    assert op_count == num_gates


def _check_phase_shift_gate_op(unrolled_ast, num_gates, qubit_list, param_list):
    num_h_gates = 2 * num_gates
    h_qubit_list = [qubit for qubit in qubit_list for _ in range(2)]
    num_rx_gates = 1 * num_gates

    check_single_qubit_gate_op(unrolled_ast, num_h_gates, h_qubit_list, "h")
    check_single_qubit_rotation_op(unrolled_ast, num_rx_gates, qubit_list, param_list, "rx")


def check_measure_op(unrolled_ast, num_ops, meas_pairs):
    """Check that the unrolled ast contains the correct number of measurements.

    Args:
        unrolled_ast (qasm3_ast.Program): The unrolled ast to check.
        num_ops (int): The number of measurements to check for.
        meas_pairs (list[tuple[(str, int), (str, int)]]): The list of measurement
                                                          pairs to check for.
    """

    meas_count = 0
    for stmt in unrolled_ast.statements:
        if isinstance(stmt, qasm3_ast.QuantumMeasurementStatement):
            source_name = stmt.measure.qubit.name.name
            source_index = stmt.measure.qubit.indices[0][0].value
            target_name = stmt.target.name.name
            target_index = stmt.target.indices[0][0].value

            # preserve order of measurement pairs
            assert (source_name, source_index) == meas_pairs[meas_count][0]
            assert (target_name, target_index) == meas_pairs[meas_count][1]
            meas_count += 1

    assert meas_count == num_ops


def check_single_qubit_rotation_op(unrolled_ast, num_gates, qubit_list, param_list, gate_name):
    if gate_name == "u3":
        check_u3_gate_op(unrolled_ast, num_gates, qubit_list, [param_list])
        return
    if gate_name == "u2":
        param_list = [CONSTANTS_MAP["pi"] / 2, param_list[0], param_list[1]]
        check_u3_gate_op(unrolled_ast, num_gates, qubit_list, [param_list])
        return
    if gate_name in ["p", "phaseshift"]:
        _check_phase_shift_gate_op(unrolled_ast, num_gates, qubit_list, param_list)
        return
    qubit_id, param_id, gate_count = 0, 0, 0
    for stmt in unrolled_ast.statements:
        if isinstance(stmt, qasm3_ast.QuantumGate) and stmt.name.name == gate_name:
            assert len(stmt.qubits) == 1
            assert stmt.qubits[0].indices[0][0].value == qubit_list[qubit_id]
            assert stmt.arguments[0].value == param_list[param_id]
            qubit_id += 1
            param_id += 1
            gate_count += 1
    assert gate_count == num_gates


def _validate_simple_custom_gate(unrolled_ast):
    check_single_qubit_gate_op(unrolled_ast, 1, [0], "h")
    check_single_qubit_gate_op(unrolled_ast, 1, [1], "z")
    check_single_qubit_rotation_op(unrolled_ast, 1, [0], [1.1], "rx")
    check_two_qubit_gate_op(unrolled_ast, 1, [(0, 1)], "cx")


def _validate_nested_custom_gate(unrolled_ast):
    check_single_qubit_gate_op(unrolled_ast, 2, [1, 0], "h")
    check_single_qubit_rotation_op(unrolled_ast, 1, [1], [4.8], "rz")
    check_two_qubit_gate_op(unrolled_ast, 1, [[0, 1]], "cx")
    check_single_qubit_rotation_op(unrolled_ast, 1, [1], [4.8], "rx")
    check_single_qubit_rotation_op(unrolled_ast, 1, [1], [5], "ry")


def _validate_complex_custom_gate(unrolled_ast):
    check_single_qubit_gate_op(unrolled_ast, 1, [0], "h")
    check_single_qubit_gate_op(unrolled_ast, 1, [0], "x")
    check_single_qubit_rotation_op(unrolled_ast, 1, [0], [0.5], "rx")
    check_single_qubit_rotation_op(unrolled_ast, 1, [0], [0.1], "ry")
    check_single_qubit_rotation_op(unrolled_ast, 1, [0], [0.2], "rz")
    check_two_qubit_gate_op(unrolled_ast, 1, [[0, 1]], "cx")


def check_custom_qasm_gate_op(unrolled_ast, test_type):
    test_function_map = {
        "simple": _validate_simple_custom_gate,
        "nested": _validate_nested_custom_gate,
        "complex": _validate_complex_custom_gate,
    }
    if test_type not in test_function_map:
        raise ValueError(f"Unknown test type {test_type}")
    test_function_map[test_type](unrolled_ast)


def check_custom_qasm_gate_op_with_external_gates(unrolled_ast, test_type):
    if test_type == "simple":
        check_two_qubit_gate_op(unrolled_ast, 1, [(0, 1)], "custom")
    elif test_type == "nested":
        check_two_qubit_gate_op(unrolled_ast, 1, [(0, 1)], "custom")
    elif test_type == "complex":
        # Only custom1 is external, custom2 and custom3 should be unrolled
        check_single_qubit_gate_op(unrolled_ast, 1, [0], "custom1")
        check_single_qubit_gate_op(unrolled_ast, 1, [0], "ry")
        check_single_qubit_gate_op(unrolled_ast, 1, [0], "rz")
        check_two_qubit_gate_op(unrolled_ast, 1, [[0, 1]], "cx")
    else:
        raise ValueError(f"Unknown test type {test_type}")
