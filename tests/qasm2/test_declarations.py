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
    qasm2_string = """
    OPENQASM 2.0;
    qreg q3[3];
    qreg q;
    
    """

    expected_qasm = """
    OPENQASM 2.0;
    qreg q3[3];
    qreg q[1];
    """

    result = loads(qasm2_string)
    result.unroll()
    unrolled_qasm = dumps(result)

    check_unrolled_qasm(unrolled_qasm, expected_qasm)


# 2. Test clbit declarations in different ways
def test_clbit_declarations():
    """Test clbit declarations in different ways"""
    qasm2_string = """
    OPENQASM 2.0;
    include 'qelib1.inc';
    
    creg c3[3];
    creg c;
    """

    expected_qasm = """OPENQASM 2.0;
    include 'qelib1.inc';
    creg c3[3];
    creg c[1];
    """

    result = loads(qasm2_string)
    result.unroll()
    unrolled_qasm = dumps(result)

    check_unrolled_qasm(unrolled_qasm, expected_qasm)


# 3. Test qubit and clbit declarations in different ways
def test_qubit_clbit_declarations():
    """Test qubit and clbit declarations in different ways"""
    qasm2_string = """
    OPENQASM 2.0;
    include 'qelib1.inc';

    // qubit declarations
    qreg q1[1];
    qreg q2[2];

    // clbit declarations
    creg c1[1];
    creg c2[2];
    """

    expected_qasm = """
    OPENQASM 2.0;
    include 'qelib1.inc';
    qreg q1[1];
    qreg q2[2];
    creg c1[1];
    creg c2[2];
    """

    result = loads(qasm2_string)
    result.unroll()
    unrolled_qasm = dumps(result)

    check_unrolled_qasm(unrolled_qasm, expected_qasm)


@pytest.mark.skip(reason="Not implemented yet")
def test_invalid_qasm2_declarations():
    """Test that invalid qasm2 raises error"""
    invalid_qasm2 = """
    OPENQASM 2.0;
    include "qelib1.inc";
    qubit[2] q;
    qubit[4] q2;
    qubit q3;
    """
    with pytest.raises(ValidationError):
        loads(invalid_qasm2).validate()
