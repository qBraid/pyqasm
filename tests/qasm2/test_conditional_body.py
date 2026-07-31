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
Module containing unit tests for what OpenQASM 2.0 allows as a conditional body

"""

import pytest

from pyqasm.entrypoint import loads
from pyqasm.exceptions import ValidationError

QASM2_PREAMBLE = """OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg m[1];
creg c[1];
measure q[0] -> m[0];
"""


@pytest.mark.parametrize("operation", ["barrier q;", "barrier q[0];", "barrier q[0], q[1];"])
def test_conditional_barrier_rejected(operation):
    """Test that a barrier is rejected as the body of a conditional. The QASM 2 grammar
    admits only a <qop> there, and barrier is a separate production."""
    module = loads(QASM2_PREAMBLE + f"if(m==1) {operation}\n")
    with pytest.raises(ValidationError, match="barrier"):
        module.validate()


def test_conditional_barrier_rejected_when_nested():
    """Test that a barrier nested deeper inside a conditional body is also rejected"""
    qasm2_string = """OPENQASM 2.0;
    include "qelib1.inc";
    qreg q[2];
    creg m[2];
    measure q[0] -> m[0];
    if(m==1) barrier q;
    """
    module = loads(qasm2_string)
    with pytest.raises(ValidationError, match="barrier"):
        module.validate()


@pytest.mark.parametrize(
    "operation", ["x q[1];", "reset q[1];", "measure q[1] -> c[0];", "cx q[0], q[1];"]
)
def test_conditional_qop_accepted(operation):
    """Test that the operations QASM 2 does allow as a conditional body still validate"""
    module = loads(QASM2_PREAMBLE + f"if(m==1) {operation}\n")
    module.validate()


def test_unconditional_barrier_accepted():
    """Test that a barrier outside a conditional is unaffected"""
    module = loads(QASM2_PREAMBLE + "barrier q;\n")
    module.validate()
