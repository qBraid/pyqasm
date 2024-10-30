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

CONTROLLED_ROTATION_ANGLE_1 = 0.5


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


def check_two_qubit_gate_op(unrolled_ast, num_gates, qubit_list, gate_name):
    qubit_id, gate_count = 0, 0
    if gate_name == "cnot":
        gate_name = "cx"

    if gate_name == "crx":
        param = CONTROLLED_ROTATION_ANGLE_1
        _check_crx_gate_op(unrolled_ast, num_gates, qubit_list[0], param)
    elif gate_name == "crz":
        param = CONTROLLED_ROTATION_ANGLE_1
        _check_crz_gate_op(unrolled_ast, num_gates, qubit_list[0], param)
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
