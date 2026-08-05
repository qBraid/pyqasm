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
    """Test that a barrier reached only through a nested conditional is also rejected,
    exercising the recursive descent rather than just the outer body"""
    module = loads(QASM2_PREAMBLE + "if(m==1) if(m==0) barrier q;\n")
    with pytest.raises(ValidationError, match="barrier"):
        module.validate()


@pytest.mark.parametrize(
    "operation, keyword",
    [
        ("delay[10ns] q;", "'delay'"),
        ("box {x q[0];}", "'box'"),
    ],
)
def test_conditional_non_qop_rejected(operation, keyword):
    """Test that any statement which is not a <qop> is rejected as a conditional body,
    not just barrier. These parse but have no QASM 2 syntax at all, and the error names
    the keyword the user wrote rather than the AST class it parsed into."""
    module = loads(QASM2_PREAMBLE + f"if(m==1) {operation}\n")
    with pytest.raises(ValidationError, match=f"{keyword} is not supported as the body of an 'if'"):
        module.validate()


def test_conditional_global_phase_reports_global_phase():
    """Test that the QuantumPhase unrolling introduces for rzz/rxx is reported as global
    phase rather than as an AST class name. Reachable only by re-filtering an already
    unrolled body, which remove_idle_qubits/reverse_qubit_order do (issue #351)."""
    module = loads(QASM2_PREAMBLE + "if(m==1) rzz(0.3) q[0], q[1];\n")
    module.unroll()
    module.reverse_qubit_order()
    with pytest.raises(ValidationError, match="Global phase is not representable in QASM 2.0"):
        module.remove_idle_qubits()


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
