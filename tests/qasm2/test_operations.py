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


# 1. Test the whitelisted operations in qasm2
def test_whitelisted_ops():
    """Test qubit declarations in different ways"""
    qasm2_string = """
    OPENQASM 2.0;
    include 'qelib1.inc';
    gate custom_gate a, b {
        cx a, b;
    }

    qreg q[2];
    creg c[2];

    barrier q;
    reset q;
    measure q -> c;
    h q;
    cx q[0], q[1];
    custom_gate q[0], q[1];
    """

    expected_qasm = """
    OPENQASM 2.0;
    include 'qelib1.inc';
    qreg q[2];
    creg c[2];
    barrier q[0];
    barrier q[1];
    reset q[0];
    reset q[1];
    measure q[0] -> c[0];
    measure q[1] -> c[1];
    h q[0];
    h q[1];
    cx q[0], q[1];
    cx q[0], q[1];
    """

    result = loads(qasm2_string)
    result.unroll()
    check_unrolled_qasm(dumps(result), expected_qasm)


def test_subroutine_blacklist():

    # subroutines
    with pytest.raises(ValidationError):
        loads(
            """
            OPENQASM 2.0;
            include 'qelib1.inc';
            qreg q[2];
            creg c[2];

            def my_func(int[32] a) -> int[32] {
                return a;
            }
            """
        ).validate()


def test_switch_blacklist():
    # switch statements
    with pytest.raises(ValidationError):
        loads(
            """
            OPENQASM 2.0;
            include 'qelib1.inc';
            qreg q[2];
            creg c[2];

            switch (1) {
                case 1: 
                    cx q[0], q[1];
                default:
                    h q[0];
            }
            """
        ).validate()


def test_for_blacklist():
    # for loops
    with pytest.raises(ValidationError):
        loads(
            """
            OPENQASM 2.0;
            include 'qelib1.inc';
            qreg q[2];
            creg c[2];

            for (int i = 0; i < 2; i++) {
                h q[i];
            }
            """
        ).validate()


def test_while_blacklist():
    # while loops
    with pytest.raises(ValidationError):
        loads(
            """
            OPENQASM 2.0;
            include 'qelib1.inc';
            qreg q[2];
            creg c[2];

            while (1) {
                h q[0];
            }
            """
        ).validate()


# TODO : extend to more constructs
