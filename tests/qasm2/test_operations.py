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
    barrier q[0], q[1];
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


def test_rzz_unrolls_without_gphase():
    """Test that the global phase from the rzz decomposition is dropped for a QASM 2
    target, which has no global-phase syntax (issue #351)"""
    qasm2_string = """
    OPENQASM 2.0;
    include 'qelib1.inc';
    qreg q[2];
    rzz(0.3) q[0], q[1];
    """

    expected_qasm = """
    OPENQASM 2.0;
    include 'qelib1.inc';
    qreg q[2];
    cx q[0], q[1];
    rz(0.3) q[1];
    rx(1.5707963267948966) q[1];
    rz(3.141592653589793) q[1];
    rx(1.5707963267948966) q[1];
    rz(3.141592653589793) q[1];
    cx q[0], q[1];
    """

    result = loads(qasm2_string)
    result.unroll()
    check_unrolled_qasm(dumps(result), expected_qasm)


def test_rxx_unrolls_without_gphase():
    """Test that the global phase from the rxx decomposition is dropped for a QASM 2
    target (issue #351)"""
    qasm2_string = """
    OPENQASM 2.0;
    include 'qelib1.inc';
    qreg q[2];
    rxx(0.3) q[0], q[1];
    """

    expected_qasm = """
    OPENQASM 2.0;
    include 'qelib1.inc';
    qreg q[2];
    h q[0];
    h q[1];
    cx q[0], q[1];
    rz(0.3) q[1];
    cx q[0], q[1];
    h q[1];
    h q[0];
    """

    result = loads(qasm2_string)
    result.unroll()
    check_unrolled_qasm(dumps(result), expected_qasm)


def test_conditional_rzz_unrolls_without_gphase():
    """Test that a conditional rzz body carries no gphase statement either (issue #351)"""
    qasm2_string = """
    OPENQASM 2.0;
    include 'qelib1.inc';
    qreg q[2];
    creg m[1];
    measure q[0] -> m[0];
    if(m==1) rzz(0.3) q[0], q[1];
    """

    result = loads(qasm2_string)
    result.unroll()
    unrolled = dumps(result)
    assert "gphase" not in unrolled

    # the unrolled output must be a loadable QASM 2 program
    loads(unrolled).validate()


def test_unrolled_qasm2_round_trips():
    """Test that unrolled rzz output loads and re-unrolls cleanly: no gphase means the
    second filtering pass has nothing to reject (issue #351)"""
    qasm2_string = """
    OPENQASM 2.0;
    include 'qelib1.inc';
    qreg q[2];
    rzz(0.3) q[0], q[1];
    """

    result = loads(qasm2_string)
    result.unroll()
    round_tripped = loads(dumps(result))
    round_tripped.unroll()
    check_unrolled_qasm(dumps(round_tripped), dumps(result))


def test_user_written_gphase_rejected():
    """Test that a gphase statement written in QASM 2 source is still rejected --
    OpenQASM 2 has no global-phase syntax, so only unroller-introduced phases are dropped"""
    qasm2_string = """
    OPENQASM 2.0;
    include 'qelib1.inc';
    qreg q[2];
    gphase(0.3);
    """

    with pytest.raises(ValidationError):
        loads(qasm2_string).validate()


def test_subroutine_blacklist():

    # subroutines
    with pytest.raises(ValidationError):
        loads("""
            OPENQASM 2.0;
            include 'qelib1.inc';
            qreg q[2];
            creg c[2];

            def my_func(int[32] a) -> int[32] {
                return a;
            }
            """).validate()


def test_switch_blacklist():
    # switch statements
    with pytest.raises(ValidationError):
        loads("""
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
            """).validate()


def test_for_blacklist():
    # for loops
    with pytest.raises(ValidationError):
        loads("""
            OPENQASM 2.0;
            include 'qelib1.inc';
            qreg q[2];
            creg c[2];

            for (int i = 0; i < 2; i++) {
                h q[i];
            }
            """).validate()


def test_while_blacklist():
    # while loops
    with pytest.raises(ValidationError):
        loads("""
            OPENQASM 2.0;
            include 'qelib1.inc';
            qreg q[2];
            creg c[2];

            while (1) {
                h q[0];
            }
            """).validate()


# TODO : extend to more constructs
