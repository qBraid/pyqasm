# Copyright (C) 2024 qBraid
#
# This file is part of pyqasm
#
# Pyqasm is free software released under the GNU General Public License v3
# or later. You can redistribute and/or modify it under the terms of the GPL v3.
# See the LICENSE file in the project root or <https://www.gnu.org/licenses/gpl-3.0.html>.
#
# THERE IS NO WARRANTY for pyqasm, as per Section 15 of the GPL v3.

# pylint: disable=invalid-name

"""
Module defining QASM3 gate tests.

"""
import os

import pytest

from pyqasm.maps import (
    FOUR_QUBIT_OP_MAP,
    ONE_QUBIT_OP_MAP,
    ONE_QUBIT_ROTATION_MAP,
    THREE_QUBIT_OP_MAP,
    TWO_QUBIT_OP_MAP,
)
from tests.utils import CONTROLLED_ROTATION_TEST_ANGLE

CUSTOM_OPS = ["simple", "nested", "complex"]

RESOURCES_DIR = os.path.join(os.path.dirname(__file__), "qasm")

VALID_GATE_NAMES = set(
    ONE_QUBIT_OP_MAP.keys()
    | TWO_QUBIT_OP_MAP.keys()
    | ONE_QUBIT_ROTATION_MAP.keys()
    | THREE_QUBIT_OP_MAP.keys()
    | FOUR_QUBIT_OP_MAP.keys()
)


def resources_file(filename: str) -> str:
    return os.path.join(RESOURCES_DIR, f"{filename}")


def _fixture_name(s: str) -> str:
    return f"Fixture_{s}"


def _generate_one_qubit_fixture(gate_name: str):
    @pytest.fixture()
    def test_fixture():
        if gate_name not in VALID_GATE_NAMES:
            raise ValueError(f"Unknown qasm3 gate {gate_name}")
        qasm3_string = f"""
        OPENQASM 3;
        include "stdgates.inc";
        
        qubit[2] q;
        {gate_name} q;
        {gate_name} q[0];
        {gate_name} q[0:2];
        """
        return qasm3_string

    return test_fixture


# Generate simple single-qubit gate fixtures
for gate in ONE_QUBIT_OP_MAP:
    name = _fixture_name(gate)
    locals()[name] = _generate_one_qubit_fixture(gate)


def _generate_rotation_fixture(gate_name: str):
    @pytest.fixture()
    def test_fixture():
        if gate_name not in VALID_GATE_NAMES:
            raise ValueError(f"Unknown qasm3 gate {gate_name}")
        qasm3_string = f"""
        OPENQASM 3;
        include "stdgates.inc";
        
        qubit[2] q;
        {gate_name}(0.5) q;
        {gate_name}(0.5) q[0];
        """
        return qasm3_string

    return test_fixture


# Generate rotation gate fixtures
for gate in ONE_QUBIT_ROTATION_MAP:
    name = _fixture_name(gate)
    locals()[name] = _generate_rotation_fixture(gate)


def _generate_two_qubit_fixture(gate_name: str):
    @pytest.fixture()
    def test_fixture():
        if gate_name not in VALID_GATE_NAMES:
            raise ValueError(f"Unknown qasm3 gate {gate_name}")

        params = ""
        if gate_name in ["crz", "crx", "cry", "rzz", "rxx", "ryy"]:
            params = f"({CONTROLLED_ROTATION_TEST_ANGLE})"

        if gate_name in ["xx_plus_yy"]:
            params = f"({CONTROLLED_ROTATION_TEST_ANGLE},{CONTROLLED_ROTATION_TEST_ANGLE})"

        qasm3_string = f"""
        OPENQASM 3;
        include "stdgates.inc";

        qubit[2] q;
        {gate_name}{params} q[0], q[1];
        {gate_name}{params} q;
        """
        return qasm3_string

    return test_fixture


# Generate double-qubit gate fixtures
for gate in TWO_QUBIT_OP_MAP:
    name = _fixture_name(gate)
    locals()[name] = _generate_two_qubit_fixture(gate)


def _generate_three_qubit_fixture(gate_name: str):
    @pytest.fixture()
    def test_fixture():
        if gate_name not in VALID_GATE_NAMES:
            raise ValueError(f"Unknown qasm3 gate {gate_name}")
        qasm3_string = f"""
        OPENQASM 3;
        include "stdgates.inc";

        qubit[3] q;
        {gate_name} q[0], q[1], q[2];
        {gate_name} q;
        """
        return qasm3_string

    return test_fixture


# Generate three-qubit gate fixtures
for gate in THREE_QUBIT_OP_MAP:
    name = _fixture_name(gate)
    locals()[name] = _generate_three_qubit_fixture(gate)


def _generate_four_qubit_fixture(gate_name: str):
    @pytest.fixture()
    def test_fixture():
        if gate_name not in VALID_GATE_NAMES:
            raise ValueError(f"Unknown qasm3 gate {gate_name}")
        qasm3_string = f"""
        OPENQASM 3;
        include "stdgates.inc";

        qubit[4] q;
        {gate_name} q[0], q[1], q[2], q[3];
        {gate_name} q;
        """
        return qasm3_string

    return test_fixture


# Generate four-qubit gate fixtures
for gate in FOUR_QUBIT_OP_MAP:
    name = _fixture_name(gate)
    locals()[name] = _generate_four_qubit_fixture(gate)


def _generate_custom_op_fixture(op_name: str):
    print(os.getcwd())

    @pytest.fixture()
    def test_fixture():
        if not op_name in CUSTOM_OPS:
            raise ValueError(f"Invalid fixture {op_name} for custom ops")
        path = resources_file(f"custom_gate_{op_name}.qasm")
        with open(path, "r", encoding="utf-8") as file:
            return file.read()

    return test_fixture


for test_name in CUSTOM_OPS:
    name = _fixture_name(test_name)
    locals()[name] = _generate_custom_op_fixture(test_name)

single_op_tests = [_fixture_name(s) for s in ONE_QUBIT_OP_MAP]
already_tested_single_op = ["id", "si", "ti", "v", "sx", "vi", "sxdg", "not"]
for gate in already_tested_single_op:
    single_op_tests.remove(_fixture_name(gate))

rotation_tests = [_fixture_name(s) for s in ONE_QUBIT_ROTATION_MAP if "u" not in s.lower()]
already_tested_rotation = ["prx", "gpi", "gpi2"]
for gate in already_tested_rotation:
    rotation_tests.remove(_fixture_name(gate))

double_op_tests = [_fixture_name(s) for s in TWO_QUBIT_OP_MAP]
already_tested_double_op = [
    "cv",
    "cy",
    "xx",
    "xy",
    "yy",
    "zz",
    "csx",
    "pswap",
    "cp",
    "cp00",
    "cp01",
    "cp10",
    "cphaseshift",
    "cu1",
    "cu",
    "cu3",
    "cphaseshift00",
    "cphaseshift01",
    "cphaseshift10",
    "ecr",
    "ms",
]
for gate in already_tested_double_op:
    double_op_tests.remove(_fixture_name(gate))

triple_op_tests = [_fixture_name(s) for s in THREE_QUBIT_OP_MAP]
already_tested_triple_op = ["ccnot", "cswap", "rccx", "toffoli"]
for gate in already_tested_triple_op:
    triple_op_tests.remove(_fixture_name(gate))

four_op_tests = [_fixture_name(s) for s in FOUR_QUBIT_OP_MAP]

custom_op_tests = [_fixture_name(s) for s in CUSTOM_OPS]

# qasm_input, expected_error
SINGLE_QUBIT_GATE_INCORRECT_TESTS = {
    "missing_register": (
        """
        OPENQASM 3;
        include "stdgates.inc";

        qubit[2] q1;
        h q2;  // undeclared register
        """,
        "Missing register declaration for q2 .*",
    ),
    "undeclared_1qubit_op": (
        """
        OPENQASM 3;
        include "stdgates.inc";

        qubit[2] q1;
        u_abc(0.5, 0.5, 0.5) q1;  // unsupported gate
        """,
        "Unsupported / undeclared QASM operation: u_abc",
    ),
    "undeclared_1qubit_op_with_indexing": (
        """
        OPENQASM 3;
        include "stdgates.inc";

        qubit[2] q1;
        ms(0,0,0) q1;
        u_abc(0.5, 0.5, 0.5) q1[0], q1[1];  // unsupported gate
        """,
        "Unsupported / undeclared QASM operation: u_abc",
    ),
    "undeclared_3qubit_op": (
        """
        OPENQASM 3;
        include "stdgates.inc";

        qubit[3] q1;
        u_abc(0.5, 0.5, 0.5) q1[0], q1[1], q1[2];  // unsupported gate
        """,
        "Unsupported / undeclared QASM operation: u_abc",
    ),
    "invalid_gate_application": (
        """
        OPENQASM 3;
        include "stdgates.inc";

        qubit[3] q1;
        cx q1;  // invalid application of gate, as we apply it to 3 qubits in blocks of 2
        """,
        "Invalid number of qubits 3 for operation cx",
    ),
    "unsupported_parameter_type": (
        """
        OPENQASM 3;
        include "stdgates.inc";

        qubit[2] q1;
        rx(a) q1; // unsupported parameter type
        """,
        "Undefined identifier a in.*",
    ),
}

# qasm_input, expected_error
CUSTOM_GATE_INCORRECT_TESTS = {
    "incorrect_gphase_usage": (
        """
        OPENQASM 3.0;
        qubit q;
        gphase(pi) q;
        """,
        r"Qubit arguments not allowed for phase operation",
    ),
    "undeclared_custom": (
        """
        OPENQASM 3;
        include "stdgates.inc";

        qubit[2] q1;
        custom_gate q1;  // undeclared gate
        """,
        "Unsupported / undeclared QASM operation: custom_gate",
    ),
    "parameter_mismatch": (
        """
        OPENQASM 3;
        include "stdgates.inc";

        gate custom_gate(a,b) p, q{
            rx(a) p;
            ry(b) q;
        }

        qubit[2] q1;
        custom_gate(0.5) q1;  // parameter count mismatch
        """,
        "Parameter count mismatch for gate custom_gate: expected 2 arguments, but got 1 instead.",
    ),
    "qubit_mismatch": (
        """
        OPENQASM 3;
        include "stdgates.inc";

        gate custom_gate(a,b) p, q{
            rx(a) p;
            ry(b) q;
        }

        qubit[3] q1;
        custom_gate(0.5, 0.5) q1;  // qubit count mismatch
        """,
        "Qubit count mismatch for gate custom_gate: expected 2 qubits, but got 3 instead.",
    ),
    "indexing_not_supported": (
        """
        OPENQASM 3;
        include "stdgates.inc";

        gate custom_gate(a,b) p, q{
            rx(a) p;
            ry(b) q[0];
        }

        qubit[2] q1;
        custom_gate(0.5, 0.5) q1;  // indexing not supported
        """,
        "Indexing .* not supported in gate definition",
    ),
    "recursive_definition": (
        """
        OPENQASM 3;
        include "stdgates.inc";

        gate custom_gate(a,b) p, q{
            custom_gate(a,b) p, q;
        }

        qubit[2] q1;
        custom_gate(0.5, 0.5) q1;  // recursive definition
        """,
        "Recursive definitions not allowed .*",
    ),
    "duplicate_definition": (
        """
        OPENQASM 3;
        include "stdgates.inc";

        gate custom_gate(a,b) p, q{
            rx(a) p;
            ry(b) q;
        }

        gate custom_gate(a,b) p, q{
            rx(a) p;
            ry(b) q;
        }

        qubit[2] q1;
        custom_gate(0.5, 0.5) q1;  // duplicate definition
        """,
        "Duplicate gate definition for custom_gate",
    ),
}
