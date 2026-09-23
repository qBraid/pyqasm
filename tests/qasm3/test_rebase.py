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
Module containing unit tests for rebasing programms

"""

import numpy as np
import pytest

from pyqasm.elements import BasisSet
from pyqasm.entrypoint import dumps, loads
from pyqasm.exceptions import RebaseError
from tests.utils import (
    assert_unitary_equal,
    check_single_qubit_gate_op,
    check_unrolled_qasm,
    unitary_from_unrolled_ast,
)


@pytest.mark.parametrize(
    "input_gates, decomposed_gates",
    [
        ("x q[0];", "rx(3.141592653589793) q[0];"),
        ("y q[0];", "ry(3.141592653589793) q[0];"),
        ("z q[0];", "rz(3.141592653589793) q[0];"),
        (
            "h q[0];",
            """
            ry(1.5707963267948966) q[0];
            rx(3.141592653589793) q[0];
            """,
        ),
        ("s q[0];", "rz(1.5707963267948966) q[0];"),
        ("t q[0];", "rz(0.7853981633974483) q[0];"),
        ("sx q[0];", "rx(1.5707963267948966) q[0];"),
        ("sdg q[0];", "rz(-1.5707963267948966) q[0];"),
        ("tdg q[0];", "rz(-0.7853981633974483) q[0];"),
        (
            "cz q[0], q[1];",
            """
            ry(1.5707963267948966) q[1];
            rx(3.141592653589793) q[1];
            cx q[0], q[1];
            ry(1.5707963267948966) q[1];
            rx(3.141592653589793) q[1];
            """,
        ),
        (
            "swap q[0], q[1];",
            """
            cx q[0], q[1];
            cx q[1], q[0];
            cx q[0], q[1];
            """,
        ),
    ],
)
def test_rebase_rotational_cx(input_gates, decomposed_gates):
    """Test that the rebasing gates to rotational-CX basis works as expected."""

    qasm = f"""OPENQASM 3.0;
    include "stdgates.inc";
    qubit[2] q;
    bit[2] c;
    {input_gates}
    c[0] = measure q[0];
    """

    expected_qasm = f"""OPENQASM 3.0;
    include "stdgates.inc";
    qubit[2] q;
    bit[2] c;
    {decomposed_gates}
    c[0] = measure q[0];
    """

    result = loads(qasm)
    result.rebase(BasisSet.ROTATIONAL_CX)
    check_unrolled_qasm(dumps(result), expected_qasm)


@pytest.mark.parametrize(
    "input_gates, decomposed_gates",
    [
        (
            "x q[0];",
            """
            h q[0];
            s q[0];
            s q[0];
            h q[0];
            """,
        ),
        (
            "y q[0];",
            """
            s q[0];
            s q[0];
            h q[0];
            s q[0];
            s q[0];
            h q[0];
            """,
        ),
        (
            "z q[0];",
            """
            s q[0];
            s q[0];
            """,
        ),
        (
            "sx q[0];",
            """
            s q[0];
            s q[0];
            s q[0];
            h q[0];
            s q[0];
            s q[0];
            s q[0];
            """,
        ),
        (
            "cz q[0], q[1];",
            """
            h q[1];
            cx q[0], q[1];
            h q[1];
            """,
        ),
        (
            "swap q[0], q[1];",
            """
            cx q[0], q[1];
            cx q[1], q[0];
            cx q[0], q[1];
            """,
        ),
    ],
)
def test_rebase_clifford_t(input_gates, decomposed_gates):
    """Test that the rebasing gates to clifford-T basis works as expected"""

    qasm = f"""OPENQASM 3.0;
    include "stdgates.inc";
    qubit[2] q;
    bit[2] c;
    {input_gates}
    c[0] = measure q[0];
    """

    expected_qasm = f"""OPENQASM 3.0;
    include "stdgates.inc";
    qubit[2] q;
    bit[2] c;
    {decomposed_gates}
    c[0] = measure q[0];
    """

    result = loads(qasm)
    result.rebase(BasisSet.CLIFFORD_T)
    check_unrolled_qasm(dumps(result), expected_qasm)


@pytest.mark.parametrize(
    "input_gate, decomposed_gates",
    [
        ("rz(pi/4) q[0];", "t q[0];"),
        ("rz(-pi/4) q[0];", "tdg q[0];"),
        ("rz(pi/2) q[0];", "s q[0];"),
        ("rz(3*pi/4) q[0];", "s q[0];\nt q[0];"),
        ("rz(5*pi/4) q[0];", "sdg q[0];\ntdg q[0];"),
        ("rz(9*pi/4) q[0];", "t q[0];"),
        (
            "rx(pi/4) q[0];",
            """
            h q[0];
            t q[0];
            h q[0];
            """,
        ),
        (
            "ry(-pi/4) q[0];",
            """
            sdg q[0];
            h q[0];
            tdg q[0];
            h q[0];
            s q[0];
            """,
        ),
        ("rx(0) q[0];", ""),
    ],
)
def test_rebase_clifford_t_exact_rotations(input_gate, decomposed_gates):
    """Exact pi/4 rotations are preserved when rebasing to Clifford+T."""
    qasm = f"""OPENQASM 3.0;
    include "stdgates.inc";
    qubit[1] q;
    bit[1] c;
    {input_gate}
    c[0] = measure q[0];
    """

    expected_qasm = f"""OPENQASM 3.0;
    include "stdgates.inc";
    qubit[1] q;
    bit[1] c;
    {decomposed_gates}
    c[0] = measure q[0];
    """

    result = loads(qasm)
    result.rebase(BasisSet.CLIFFORD_T)
    check_unrolled_qasm(dumps(result), expected_qasm)


@pytest.mark.parametrize(
    "gate_name, pauli",
    [
        ("rx", np.array([[0, 1], [1, 0]], dtype=complex)),
        ("ry", np.array([[0, -1j], [1j, 0]], dtype=complex)),
        ("rz", np.diag([1, -1]).astype(complex)),
    ],
)
@pytest.mark.parametrize("quarter_turns", range(8))
def test_rebase_clifford_t_rotation_unitary(gate_name: str, pauli: np.ndarray, quarter_turns: int):
    """Every exact quarter turn has the expected unitary up to global phase."""
    qasm = f"""OPENQASM 3.0;
    include "stdgates.inc";
    qubit[1] q;
    {gate_name}({quarter_turns}*pi/4) q[0];
    """

    result = loads(qasm)
    result.rebase(BasisSet.CLIFFORD_T)

    angle = quarter_turns * np.pi / 4
    expected = np.cos(angle / 2) * np.eye(2) - 1j * np.sin(angle / 2) * pauli
    assert_unitary_equal(unitary_from_unrolled_ast(result.unrolled_ast, 1), expected)


@pytest.mark.parametrize("gate_name", ["rx", "ry", "rz"])
def test_rebase_clifford_t_rejects_inexact_rotations(gate_name):
    """Rotations outside the exact basis fail instead of disappearing."""
    qasm = f"""OPENQASM 3.0;
    include "stdgates.inc";
    qubit[1] q;
    {gate_name}(pi/3) q[0];
    """

    with pytest.raises(
        RebaseError,
        match=rf"Gate '{gate_name}'.*cannot be represented exactly",
    ):
        loads(qasm).rebase(BasisSet.CLIFFORD_T)


def test_rebase_clifford_t_rotation_in_branch():
    """Exact rotations inside conditional blocks are decomposed too."""
    qasm = """OPENQASM 3.0;
    include "stdgates.inc";
    qubit[1] q;
    bit[1] c;
    if (c[0] == true) {
        ry(-pi/4) q[0];
    }
    """

    expected_qasm = """OPENQASM 3.0;
    include "stdgates.inc";
    qubit[1] q;
    bit[1] c;
    if (c[0] == true) {
        sdg q[0];
        h q[0];
        tdg q[0];
        h q[0];
        s q[0];
    }
    """

    result = loads(qasm)
    result.rebase(BasisSet.CLIFFORD_T)
    check_unrolled_qasm(dumps(result), expected_qasm)


def test_rebase_if():
    """Test converting a QASM3 program that contains if statements"""

    qasm = """OPENQASM 3.0;
    include "stdgates.inc";
    qubit[1] q;
    bit[4] c;
    if(c == 3){
        h q[0];
    }
    if(c >= 3){
        h q[0];
    } else {
        x q[0];
    }
    if(c <= 3){
        h q[0];
    } else {
        x q[0];
    }
    if(c < 4){
        h q[0];
    } else {
        x q[0];
    }
    """
    expected_qasm = """OPENQASM 3.0;
    include "stdgates.inc";
    qubit[1] q;
    bit[4] c;
    if (c[0] == false) {
        if (c[1] == false) {
            if (c[2] == true) {
                if (c[3] == true) {
                    ry(1.5707963267948966) q[0];
                    rx(3.141592653589793) q[0];
                }
            }
        }
    }
    if (c[2] == true) {
        if (c[3] == true) {
            ry(1.5707963267948966) q[0];
            rx(3.141592653589793) q[0];
        } else {
            rx(3.141592653589793) q[0];
        }
    } else {
        rx(3.141592653589793) q[0];
    }
    if (c[0] == false) {
       if (c[1] == false) {
           ry(1.5707963267948966) q[0];
           rx(3.141592653589793) q[0];
       } else {
           rx(3.141592653589793) q[0];
       }
    } else {
        rx(3.141592653589793) q[0];
    }
    if (c[0] == false) {
       if (c[1] == false) {
           ry(1.5707963267948966) q[0];
           rx(3.141592653589793) q[0];
       } else {
           rx(3.141592653589793) q[0];
       }
    } else {
        rx(3.141592653589793) q[0];
    }
    """

    result = loads(qasm)
    result.rebase(BasisSet.ROTATIONAL_CX)
    check_unrolled_qasm(dumps(result), expected_qasm)


def test_rebase_invalid_basis_set():
    qasm = """
        OPENQASM 3.0;
        include "stdgates.inc";

        qubit[2] q;
        bit[2] c;

        h q[0];
        cx q[0], q[1];
        measure q->c;
        """

    result = loads(qasm)

    with pytest.raises(ValueError, match="Target basis set 'invalid_basis' is not defined."):
        result.rebase("invalid_basis")


def test_rebase_loop():
    """Test converting a QASM3 program that contains a for loop"""

    qasm = """
        OPENQASM 3.0;
        include "stdgates.inc";

        qubit[4] q;
        bit[4] c;

        for int i in [0:3]{
            z q[i];
        }
        measure q->c;
        """

    result = loads(qasm)
    result = result.rebase(BasisSet.CLIFFORD_T)

    check_single_qubit_gate_op(result.unrolled_ast, 8, [0, 0, 1, 1, 2, 2, 3, 3], "s")


def test_rebase_qasm_module_methods():
    """Test that all other methods of Qasm Modules works as expected after rebase"""

    qasm = """
        OPENQASM 3.0;
        include "stdgates.inc";
        
        qubit[3] q;
        bit[3] c;
        
        h q[0];
        cx q[0], q[1];
        
        barrier q;
        measure q[0]->c[0];
        """

    result = loads(qasm)
    result = result.rebase(BasisSet.ROTATIONAL_CX)

    # Check has and remove barrier
    assert result.has_barriers() is True
    result.remove_barriers()
    assert result.has_barriers() is False

    # Check har and remove measurement
    assert result.has_measurements() is True
    result.remove_measurements()
    assert result.has_measurements() is False

    # Check remove idle qubit
    assert result.num_qubits == 3
    result.remove_idle_qubits()
    assert result.num_qubits == 2

    # Check depth
    assert result.depth() == 3

    # Check reverse qubit order
    expected_reverse_qubit_order_qasm = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[2] q;
    bit[3] c;
    ry(1.5707963267948966) q[1];
    rx(3.141592653589793) q[1];
    cx q[1], q[0];
    """
    result.reverse_qubit_order()
    print(dumps(result))
    check_unrolled_qasm(dumps(result), expected_reverse_qubit_order_qasm)
