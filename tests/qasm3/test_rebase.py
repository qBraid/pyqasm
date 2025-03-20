# Copyright (C) 2025 qBraid
#
# This file is part of PyQASM
#
# PyQASM is free software released under the GNU General Public License v3
# or later. You can redistribute and/or modify it under the terms of the GPL v3.
# See the LICENSE file in the project root or <https://www.gnu.org/licenses/gpl-3.0.html>.
#
# THERE IS NO WARRANTY for PyQASM, as per Section 15 of the GPL v3.

"""
Module containing unit tests for rebasing programms

"""
import pytest

from pyqasm.elements import BasisSet
from pyqasm.entrypoint import dumps, loads
from tests.utils import check_single_qubit_gate_op, check_unrolled_qasm


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
        (
            "rx(pi) q[0];",
            """
            h q[0];
            s q[0];
            s q[0];
            h q[0];
            """,
        ),
        (
            "rx(pi/2) q[0];",
            """
            h q[0];
            s q[0];
            h q[0];
            """,
        ),
        (
            "rx(pi/4) q[0];",
            """
            h q[0];
            t q[0];
            h q[0];
            """,
        ),
        (
            "ry(pi) q[0];",
            """
            sdg q[0];
            h q[0];
            s q[0];
            s q[0];
            h q[0];
            s q[0];
            """,
        ),
        (
            "ry(pi/2) q[0];",
            """
            sdg q[0];
            h q[0];
            s q[0];
            h q[0];
            s q[0];
            """,
        ),
        (
            "ry(pi/4) q[0];",
            """
            sdg q[0];
            h q[0];
            t q[0];
            h q[0];
            s q[0];
            """,
        ),
        (
            "rz(pi) q[0];",
            """
            s q[0];
            s q[0];
            """,
        ),
        (
            "rz(pi/2) q[0];",
            """
            s q[0];
            """,
        ),
        (
            "rz(pi/4) q[0];",
            """
            t q[0];
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
