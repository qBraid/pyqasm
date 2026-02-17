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
Module containing unit tests for Delay Instruction.
"""

import pytest

from pyqasm.entrypoint import dumps, loads
from pyqasm.exceptions import ValidationError
from tests.utils import check_unrolled_qasm


def test_delay_instruction_():
    qasm_str = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[5] q;
    qubit[2] q2;
    duration t1 = 300dt;
    delay[t1 * 2] q[0], q[1];
    delay[t1];
    """
    expected_qasm = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[5] q;
    qubit[2] q2;
    delay[600.0ns] q[0], q[1];
    delay[300.0ns] q[0], q[1], q[2], q[3], q[4], q2[0], q2[1];
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
            delay[d] q[0];
            """,
            r"DelayInstruction' variable 'd' is not defined",
            r"Error at line 5, column 12",
        ),
        (
            """
            OPENQASM 3.0;
            include "stdgates.inc";
            qubit[5] q;
            int a = 1;
            delay[a] q[0];
            """,
            r"DelayInstruction variable must be of type 'stretch' or 'duration'",
            r"Error at line 6, column 12",
        ),
        (
            """
            OPENQASM 3.0;
            include "stdgates.inc";
            qubit[5] q;
            delay[2*2] q[0];
            """,
            r"Both lhs and rhs of delay values cannot be 'IntegerLiteral' and 'IntegerLiteral'",
            r"Error at line 5, column 17",
        ),
        (
            """
            OPENQASM 3.0;
            include "stdgates.inc";
            qubit[5] q;
            int a = 1;
            delay[2*a] q[0];
            """,
            r"'DelayInstruction' variable must be of type 'stretch' or 'duration'",
            r"Error at line 6, column 17",
        ),
        (
            """
            OPENQASM 3.0;
            include "stdgates.inc";
            qubit[5] q;
            delay[2*a] q[0];
            """,
            r"'DelayInstruction' variable 'a' is not defined",
            r"Error at line 5, column 17",
        ),
        (
            """
            OPENQASM 3.0;
            include "stdgates.inc";
            qubit[5] q;
            delay[2] q[0];
            """,
            r"'DelayInstruction' value must be a 'DurationLiteral'.",
            r"Error at line 5, column 12",
        ),
        (
            """
            OPENQASM 3.0;
            include "stdgates.inc";
            qubit[5] q;
            delay[20ns] q[0], q[0];
            """,
            r"Duplicate qubit 'q[0]' arg in DelayInstruction",
            r"Error at line 5, column 12",
        ),
        (
            """
            OPENQASM 3.0;
            include "stdgates.inc";
            qubit[5] q;
            delay[-22ns] q[0], q[0];
            """,
            r"'DelayInstruction' cannot have duration value 'less than or equal to 0'",
            r"Error at line 5, column 12",
        ),
        (
            """
            OPENQASM 3.0;
            include "stdgates.inc";
            qubit[5] q;
            duration d = -22ns;
            delay[d] q[0], q[0];
            """,
            r"variable 'd = -22.0' in 'DelayInstruction', must be 'greater than 0'",
            r"Error at line 6, column 12",
        ),
    ],
)  # pylint: disable-next= too-many-arguments
def test_delay_instruction_error(qasm_code, error_message, error_span, caplog):
    with pytest.raises(ValidationError) as err:
        with caplog.at_level("ERROR"):
            loads(qasm_code).unroll()
    assert error_message in str(err.value)
    assert error_span in caplog.text
