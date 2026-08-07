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
Module containing unit tests for parsing and unrolling programs that contain quantum
declarations.

"""

import pytest

from pyqasm.entrypoint import dumps, loads
from pyqasm.exceptions import ValidationError
from tests.utils import check_unrolled_qasm


# 1. Test qubit declarations in different ways
def test_qubit_declarations():
    """Test qubit declarations in different ways"""
    qasm3_string = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit q1;
    qubit[2] q2;
    qreg q3[3];
    qubit[1] q4;

    const int[32] N = 10;
    qubit[N] q5;
    """

    expected_qasm = """OPENQASM 3.0;
    include "stdgates.inc";
    qubit[1] q1;
    qubit[2] q2;
    qubit[3] q3;
    qubit[1] q4;
    qubit[10] q5;
    """

    result = loads(qasm3_string)
    result.unroll()
    unrolled_qasm = dumps(result)

    check_unrolled_qasm(unrolled_qasm, expected_qasm)


# 2. Test clbit declarations in different ways
def test_clbit_declarations():
    """Test clbit declarations in different ways"""
    qasm3_string = """
    OPENQASM 3.0;
    include "stdgates.inc";
    bit c1;
    bit[2] c2;
    creg c3[3];
    bit[1] c4;

    const int[32] size = 10;
    bit[size] c5;
    """

    expected_qasm = """OPENQASM 3.0;
    include "stdgates.inc";
    bit[1] c1;
    bit[2] c2;
    bit[3] c3;
    bit[1] c4;
    bit[10] c5;
    """

    result = loads(qasm3_string)
    result.unroll()
    unrolled_qasm = dumps(result)

    check_unrolled_qasm(unrolled_qasm, expected_qasm)


# 3. Test qubit and clbit declarations in different ways
def test_qubit_clbit_declarations():
    """Test qubit and clbit declarations in different ways"""
    qasm3_string = """
    OPENQASM 3.0;
    include "stdgates.inc";

    // qubit declarations
    qubit q1;
    qubit[2] q2;
    qreg q3[3];
    qubit[1] q4;

    // clbit declarations
    bit c1;
    bit[2] c2;
    creg c3[3];
    bit[1] c4;
    """

    expected_qasm = """OPENQASM 3.0;
    include "stdgates.inc";
    qubit[1] q1;
    qubit[2] q2;
    qubit[3] q3;
    qubit[1] q4;
    bit[1] c1;
    bit[2] c2;
    bit[3] c3;
    bit[1] c4;
    """

    result = loads(qasm3_string)
    result.unroll()
    unrolled_qasm = dumps(result)

    check_unrolled_qasm(unrolled_qasm, expected_qasm)


@pytest.mark.parametrize(
    "qasm_code,error_message,line_num,col_num,err_line",
    [
        (
            """
            OPENQASM 3.0;
            include "stdgates.inc";
            qubit q1;
            qubit q1;
            """,
            "Re-declaration of quantum register with name 'q1'",
            5,
            12,
            "qubit[1] q1;",
        ),
        (
            """
            OPENQASM 3.0;
            include "stdgates.inc";
            qubit pi;
            """,
            "Can not declare quantum register with keyword name 'pi'",
            4,
            12,
            "qubit[1] pi;",
        ),
        (
            """
            OPENQASM 3.0;
            include "stdgates.inc";
            bit c1;
            bit[4] c1;
            """,
            r"Re-declaration of variable 'c1'",
            5,
            12,
            "bit[4] c1;",
        ),
        (
            """
            OPENQASM 3.0;
            include "stdgates.inc";
            int[32] N = 10;
            qubit[N] q;
            """,
            r"Invalid size 'N' for quantum register 'q'",
            5,
            12,
            "qubit[N] q;",
        ),
        (
            """
            OPENQASM 3.0;
            include "stdgates.inc";
            int[32] size = 10;
            bit[size] c;
            """,
            r"Invalid base size for variable 'c'",
            5,
            15,
            "bit[size] c;",
        ),
    ],
)
# pylint: disable-next=too-many-arguments
def test_quantum_declarations_errors(qasm_code, error_message, line_num, col_num, err_line, caplog):
    """Test various error cases with qubit and bit declarations"""
    with pytest.raises(ValidationError, match=error_message):
        with caplog.at_level("ERROR"):
            loads(qasm_code).validate()

    assert f"Error at line {line_num}, column {col_num}" in caplog.text
    assert err_line in caplog.text
