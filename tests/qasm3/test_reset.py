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
Module containing unit tests for reset operation.

"""

import pytest

from pyqasm.entrypoint import dumps, loads
from pyqasm.exceptions import ValidationError
from tests.utils import check_unrolled_qasm


# Test reset operations in different ways
def test_reset_operations():
    """Test reset operations in different ways"""
    qasm3_string = """
    OPENQASM 3.0;
    include "stdgates.inc";

    // qubit declarations
    qubit q1;
    qubit[2] q2;
    qreg q3[3];

    // reset operations
    reset q1;
    reset q2[1];
    reset q3[2];
    reset q3[:2];
    """

    expected_qasm = """OPENQASM 3.0;
    include "stdgates.inc";
    qubit[1] q1;
    qubit[2] q2;
    qubit[3] q3;
    reset q1[0];
    reset q2[1];
    reset q3[2];
    reset q3[0];
    reset q3[1];
    """

    result = loads(qasm3_string)
    result.unroll()
    check_unrolled_qasm(dumps(result), expected_qasm)


def test_reset_inside_function():
    """Test that a qubit reset inside a function is correctly parsed."""
    qasm3_string = """OPENQASM 3.0;
    include "stdgates.inc";

    def my_function(qubit a) {
        reset a;
        return;
    }
    qubit[3] q;
    my_function(q[1]);
    """

    expected_qasm = """OPENQASM 3.0;
    include "stdgates.inc";
    qubit[3] q;
    reset q[1];
    """

    result = loads(qasm3_string)
    result.unroll()
    check_unrolled_qasm(dumps(result), expected_qasm)


def test_incorrect_resets(caplog):
    undeclared = """
    OPENQASM 3.0;
    include "stdgates.inc";

    qubit[3] q1;

    // undeclared register 
    reset q2[0];
    """
    with pytest.raises(ValidationError):
        with caplog.at_level("ERROR"):
            loads(undeclared).validate()

    assert "Error at line 8, column 4" in caplog.text
    assert "reset q2[0]" in caplog.text

    index_error = """
    OPENQASM 3.0;
    include "stdgates.inc";

    qubit[2] q1;

    // out of bounds 
    reset q1[4];
    """
    with pytest.raises(
        ValidationError, match=r"Index 4 out of range for register of size 2 in qubit"
    ):
        with caplog.at_level("ERROR"):
            loads(index_error).validate()

    assert "Error at line 8, column 4" in caplog.text
    assert "reset q1[4]" in caplog.text
