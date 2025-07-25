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
Module containing unit tests for Box Statement.
"""
import pytest

from pyqasm.entrypoint import dumps, loads
from pyqasm.exceptions import ValidationError
from tests.utils import check_unrolled_qasm


def test_box_statement():
    qasm_str = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[5] q;
    qubit[2] q2;
    const duration d = 22ns;
    stretch s1;
    const stretch s2 = 20ns;
    box [30ns] {
        delay [d] q;
        x q[1];
        measure q;
    }
    box [d+d] {
        delay [d] q;
        cx q[0], q2[1];
        delay [d] q2;
    }
    box {
        duration d2 =  20ns;
        delay [d2] q;
        delay [s2] q;
        x q[1];
        nop q[2];
    }
    """
    expected_qasm = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[5] q;
    qubit[2] q2;
    stretch s1;
    box[30.0ns] {
      delay[22.0ns] q[0], q[1], q[2], q[3], q[4];
      x q[1];
      measure q[0];
      measure q[1];
      measure q[2];
      measure q[3];
      measure q[4];
    }
    box[44.0ns] {
      delay[22.0ns] q[0], q[1], q[2], q[3], q[4];
      cx q[0], q2[1];
      delay[22.0ns] q2[0], q2[1];
    }
    box {
      delay[20.0ns] q[0], q[1], q[2], q[3], q[4];
      delay[20.0ns] q[0], q[1], q[2], q[3], q[4];
      x q[1];
      nop q[2];
    }
    """
    module = loads(qasm_str)
    module.validate()
    module.unroll()
    check_unrolled_qasm(dumps(module), expected_qasm)


def test_delay_instruction_device_time():
    qasm_str = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[5] q;
    duration t1 = 300dt;
    delay[t1 * 2] q[0], q[1];
    """
    expected_qasm = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[5] q;
    delay[6.000000000000001e-07dt] q[0], q[1];
    """
    module = loads(qasm_str, device_cycle_time=1e-9)
    module.unroll()
    check_unrolled_qasm(dumps(module), expected_qasm)


@pytest.mark.parametrize(
    "qasm_code,error_message,error_span",
    [
        (
            """
            OPENQASM 3.0;
            include "stdgates.inc";
            qubit[5] q;
            qubit[2] q2;
            box[-30.0ns] {
              delay[22.0ns];
              x q[1];
              measure q;
            }
            """,
            r"'Box' cannot have duration value 'less than or equal to 0'",
            r"Error at line 6, column 12",
        ),
        (
            """
            OPENQASM 3.0;
            include "stdgates.inc";
            qubit[5] q;
            qubit[2] q2;
            duration d = -20ns;
            box[d] {
              delay[2.0ns];
              x q[1];
              measure q;
            }
            """,
            r"variable 'd = -20.0' in 'Box', must be 'greater than 0'",
            r"Error at line 7, column 12",
        ),
        (
            """
            OPENQASM 3.0;
            include "stdgates.inc";
            qubit[5] q;
            qubit[2] q2;
            duration d = -20ns;
            box[2] {
              delay[2.0ns];
              x q[1];
              measure q;
            }
            """,
            r"'Box' value must be a 'DurationLiteral'.",
            r"Error at line 7, column 12",
        ),
        (
            """
            OPENQASM 3.0;
            include "stdgates.inc";
            qubit[5] q;
            qubit[2] q2;
            duration d = -20ns;
            box[1 * 2] {
              delay[2.0ns];
              x q[1];
              measure q;
            }
            """,
            r"Both lhs and rhs of delay values cannot be 'IntegerLiteral' and 'IntegerLiteral'",
            r"Error at line 7, column 15",
        ),
        (
            """
            OPENQASM 3.0;
            include "stdgates.inc";
            qubit[5] q;
            qubit[2] q2;
            int d = 1;
            box[d] {
              delay[2.0ns];
              x q[1];
              measure q;
            }
            """,
            r"Box variable must be of type 'stretch' or 'duration'",
            r"Error at line 7, column 12",
        ),
        (
            """
            OPENQASM 3.0;
            include "stdgates.inc";
            qubit[5] q;
            qubit[2] q2;
            box[10ns] {
              delay[20ns];
              x q[1];
              measure q;
            }
            """,
            r"Total delay duration value '20.0ns' should be less than 'box[10.0ns]' duration.",
            r"Error at line 6, column 12",
        ),
        (
            """
            OPENQASM 3.0;
            include "stdgates.inc";
            qubit[5] q;
            qubit[2] q2;
            box[10ns] {
            }
            """,
            r"Box statement must have atleast one Quantum Statement.",
            r"Error at line 6, column 12",
        ),
        (
            """
            OPENQASM 3.0;
            include "stdgates.inc";
            qubit q;
            duration d2 = 20ns;
            box [d2] {
               delay[d2] q;
            }
            """,
            r"Global variable 'd2' must be a constant to use it in a local scope.",
            r"Error at line 7, column 20",
        ),
    ],
)  # pylint: disable-next= too-many-arguments
def test_box_statement_error(qasm_code, error_message, error_span, caplog):
    with pytest.raises(ValidationError) as err:
        with caplog.at_level("ERROR"):
            loads(qasm_code).unroll()
    assert error_message in str(err.value)
    assert error_span in caplog.text
