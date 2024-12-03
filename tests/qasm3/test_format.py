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
Module containing unit tests for program formatting

"""
import pytest

from pyqasm.entrypoint import dumps, loads
from tests.utils import check_unrolled_qasm


def test_comments_removed_from_qasm():
    qasm3_string = """
    OPENQASM 3;
    include "stdgates.inc";
    // This is a comment
    qubit q;
    // This is another comment
    h q;
    """
    expected_qasm3_string = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit q;
    h q;
    """

    result = loads(qasm3_string)
    actual_qasm3_string = dumps(result)

    check_unrolled_qasm(actual_qasm3_string, expected_qasm3_string)


def test_empty_lines_removed_from_qasm():
    qasm3_string = """
    OPENQASM 3.0;


    include "stdgates.inc";



    qubit q;
    h q;



    
    """
    expected_qasm3_string = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit q;
    h q;
    """

    result = loads(qasm3_string)
    actual_qasm3_string = dumps(result)

    check_unrolled_qasm(actual_qasm3_string, expected_qasm3_string)


def test_convert_qasm_pi_to_decimal_qasm3_fns_gates_vars():
    """Test converting pi symbol to decimal in a qasm3 string
    with custom functions, gates, and variables."""
    qasm3_string = """
    OPENQASM 3;
    include "stdgates.inc";

    gate pipe q {
        gpi(0) q;
    }

    const int[32] primeN = 3;
    const float[32] c = primeN*pi/4;
    qubit[3] q;

    def spiral(qubit[primeN] q_func) {
    for int i in [0:primeN-1] { 
        pipe q_func[i]; 
        }
    }

    spiral(q);

    ry(c) q[0];

    bit[3] result;
    result = measure q;
    """

    expected_qasm3_string = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[3] q;
    gpi(0) q[0];
    gpi(0) q[1];
    gpi(0) q[2];
    ry(2.356194490192345) q[0];
    bit[3] result;
    result[0] = measure q[0];
    result[1] = measure q[1];
    result[2] = measure q[2];"""

    result = loads(qasm3_string)
    result.unroll(external_gates=["gpi"])
    actual_qasm3_string = dumps(result)

    check_unrolled_qasm(actual_qasm3_string, expected_qasm3_string)


def test_convert_qasm_pi_to_decimal():
    """Test converting pi symbol to decimal in qasm string with gpi2 gate on its own."""
    qasm3_string = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[2] q;
    gpi(pi/4) q[0];
    h q[0];
    rx(pi / 4) q[0];
    ry(2*pi) q[0];
    rz(3 * pi/4) q[0];
    cry(pi/4/2) q[0], q[1];
    """

    expected_qasm3_string = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[2] q;
    gpi(0.7853981633974483) q[0];
    h q[0];
    rx(0.7853981633974483) q[0];
    ry(6.283185307179586) q[0];
    rz(2.356194490192345) q[0];
    cry(0.39269908169872414) q[0], q[1];
    """
    result = loads(qasm3_string)
    result.unroll(external_gates=["gpi", "cry"])
    actual_qasm3_string = dumps(result)

    check_unrolled_qasm(actual_qasm3_string, expected_qasm3_string)


@pytest.mark.parametrize(
    "qasm_input, expected_result",
    [
        (
            """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[2] q;
    cry((0.39269908169872414)) q[0], q[1];
    """,
            """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[2] q;
    cry(0.39269908169872414) q[0], q[1];
    """,
        ),
        (
            """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[2] q;
    crx(-(0.39269908169872414)) q[0], q[1];
    """,
            """OPENQASM 3.0;
    include "stdgates.inc";
    qubit[2] q;
    crx(-0.39269908169872414) q[0], q[1];""",
        ),
        (
            """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[2] q;
    cry((0.7853981633974483)) q[0], q[1];
    ry(-(0.39269908169872414)) q[1];
    """,
            """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[2] q;
    cry(0.7853981633974483) q[0], q[1];
    ry(-0.39269908169872414) q[1];
    """,
        ),
    ],
)
def test_simplify_redundant_parentheses(qasm_input, expected_result):
    """Test simplifying redundant parentheses in qasm string"""
    module = loads(qasm_input)
    module.unroll(external_gates=["cry", "crx", "ry"])
    actual_result = dumps(module)
    check_unrolled_qasm(actual_result, expected_result)
