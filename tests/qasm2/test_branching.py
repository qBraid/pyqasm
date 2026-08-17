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
Module containing unit tests for serializing classical conditionals as OpenQASM 2.0

"""

import pytest

from pyqasm.entrypoint import dumps, loads
from pyqasm.exceptions import ValidationError
from tests.utils import check_unrolled_qasm


def test_branch_emits_qasm2_syntax():
    """Test that a conditional round-trips as QASM 2 syntax rather than a braced
    QASM 3 block (issue #337)"""
    qasm2_string = """OPENQASM 2.0;
    include "qelib1.inc";
    qreg q[2];
    creg m[1];
    creg c[2];
    h q[0];
    measure q[0] -> m[0];
    if(m==1) x q[1];
    measure q -> c;
    """
    expected_qasm2_string = """OPENQASM 2.0;
    include "qelib1.inc";
    qreg q[2];
    creg m[1];
    creg c[2];
    h q[0];
    measure q[0] -> m[0];
    if (m == 1) x q[1];
    measure q -> c;
    """
    unrolled = dumps(loads(qasm2_string))
    assert "{" not in unrolled and "}" not in unrolled
    check_unrolled_qasm(unrolled, expected_qasm2_string)


def test_branch_body_expands_to_one_conditional_per_statement():
    """Test that a body which unrolls into several statements becomes one guarded
    statement each, since QASM 2 has no braced blocks"""
    qasm2_string = """OPENQASM 2.0;
    include "qelib1.inc";
    qreg q[2];
    creg m[1];
    measure q[0] -> m[0];
    if(m==1) h q;
    """
    expected_qasm2_string = """OPENQASM 2.0;
    include "qelib1.inc";
    qreg q[2];
    creg m[1];
    measure q[0] -> m[0];
    if (m == 1) h q[0];
    if (m == 1) h q[1];
    """
    module = loads(qasm2_string)
    module.unroll()
    unrolled = dumps(module)
    assert "{" not in unrolled and "}" not in unrolled
    check_unrolled_qasm(unrolled, expected_qasm2_string)


@pytest.mark.parametrize("value", [0, 1, 2, 3])
def test_multibit_branch_survives_unrolling(value):
    """Test that the per-bit conditionals unrolling produces for a multi-bit register
    collapse back into the whole-register comparison QASM 2 requires"""
    qasm2_string = f"""OPENQASM 2.0;
    include "qelib1.inc";
    qreg q[3];
    creg m[2];
    measure q[0] -> m[0];
    measure q[1] -> m[1];
    if(m=={value}) x q[2];
    """
    expected_qasm2_string = f"""OPENQASM 2.0;
    include "qelib1.inc";
    qreg q[3];
    creg m[2];
    measure q[0] -> m[0];
    measure q[1] -> m[1];
    if (m == {value}) x q[2];
    """
    module = loads(qasm2_string)
    module.unroll()
    unrolled = dumps(module)
    assert "{" not in unrolled and "}" not in unrolled
    check_unrolled_qasm(unrolled, expected_qasm2_string)


@pytest.mark.parametrize(
    "operation, expected",
    [
        ("x q[1];", "if (m == 1) x q[1];"),
        ("reset q[1];", "if (m == 1) reset q[1];"),
        ("measure q[1] -> c[0];", "if (m == 1) measure q[1] -> c[0];"),
    ],
)
def test_branch_body_statement_types(operation, expected):
    """Test that every operation QASM 2 allows in a conditional body is emitted on the
    same line as the condition"""
    qasm2_string = f"""OPENQASM 2.0;
    include "qelib1.inc";
    qreg q[2];
    creg m[1];
    creg c[1];
    measure q[0] -> m[0];
    if(m==1) {operation}
    """
    module = loads(qasm2_string)
    module.unroll()
    unrolled = dumps(module)
    assert "{" not in unrolled and "}" not in unrolled
    assert expected in unrolled


def test_branch_on_register_level_measurement_round_trips():
    """Test that a branch guarding a whole-register measurement is emitted as written,
    whether or not unrolling expanded it into one statement per bit"""
    qasm2_string = """OPENQASM 2.0;
    include "qelib1.inc";
    qreg q[2];
    creg m[2];
    measure q[0] -> m[0];
    if(m==1) measure q -> m;
    """
    expected_qasm2_string = """OPENQASM 2.0;
    include "qelib1.inc";
    qreg q[2];
    creg m[2];
    measure q[0] -> m[0];
    if (m == 1) measure q -> m;
    """
    module = loads(qasm2_string)
    module.unroll()
    check_unrolled_qasm(dumps(module), expected_qasm2_string)
    # the non-unrolled path never expanded the measurement, so the two must agree
    check_unrolled_qasm(dumps(loads(qasm2_string)), expected_qasm2_string)


def test_branch_body_writing_tested_register_raises():
    """Test that a genuinely multi-statement body assigning to the register under test is
    rejected rather than emitted with the condition re-evaluated mid-body"""
    qasm2_string = """OPENQASM 2.0;
    include "qelib1.inc";
    qreg q[2];
    creg m[2];
    measure q[0] -> m[0];
    if(m==1) { x q[0]; measure q[0] -> m[0]; }
    """
    match = "writes to 'm' -- the register the branch tests"
    with pytest.raises(ValidationError, match=match):
        loads(qasm2_string).validate()
    with pytest.raises(ValidationError, match=match):
        dumps(loads(qasm2_string))


@pytest.mark.parametrize(
    "operation, match",
    [
        # two whole-register comparisons in a chain: the outer constraint has nowhere
        # to go in the single comparison QASM 2 allows
        ("if(m==1) if(m==0) x q[0];", "nests another whole-register comparison"),
        # the same bit constrained twice, ditto
        ("if(m[0]==1) if(m[0]==0) x q[0];", "tests bit 0 more than once"),
        # a bit compared against something that is not a bit value
        ("if(m[0]==2) x q[0];", "against 2"),
    ],
)
def test_conflicting_chain_constraints_raise(operation, match):
    """Test that a chain carrying constraints the collapse cannot represent is rejected
    rather than silently reduced to whichever constraint happens to be walked last"""
    qasm2_string = f"""OPENQASM 2.0;
    include "qelib1.inc";
    qreg q[2];
    creg m[1];
    measure q[0] -> m[0];
    {operation}
    """
    with pytest.raises(ValidationError, match=match):
        dumps(loads(qasm2_string))


@pytest.mark.parametrize(
    "operation, match",
    [
        ("if(m==1) x q[0]; else x q[1];", "'else' blocks are not supported"),
        ("if(m==1) if(c==1) x q[0];", "different registers"),
        ("if(m==1) if(m==0) x q[0];", "nests another whole-register comparison"),
        ("if(m[0]==1) x q[0];", "unconstrained"),
        # the operator has to be named: unrolling ravels '>=' into a chain of equality
        # tests, so by serialization time there is nothing left to name
        ("if(m>=1) x q[0];", "which uses '>='"),
        ("if(m<2) x q[0];", "which uses '<'"),
    ],
)
def test_inexpressible_branches_rejected_identically_by_validate_and_dumps(operation, match):
    """Test that each branch shape QASM 2 has no syntax for is rejected, by validate()
    rather than only by serialization, and with the same diagnostic either way.

    Both paths run ``_flatten_branch``, so a divergence here means validation and
    serialization have drifted back into two implementations of one rule -- which is
    how validate() came to reject per-bit chains the printer collapses correctly.
    """
    qasm2_string = f"""OPENQASM 2.0;
    include "qelib1.inc";
    qreg q[2];
    creg m[2];
    creg c[1];
    measure q[0] -> m[0];
    {operation}
    """
    with pytest.raises(ValidationError, match=match):
        loads(qasm2_string).validate()
    with pytest.raises(ValidationError, match=match):
        dumps(loads(qasm2_string))


VALID_CONDITIONAL_1BIT = """OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg m[1];
h q[0];
measure q[0] -> m[0];
if(m==1) x q[1];
"""

VALID_CONDITIONAL_2BIT = VALID_CONDITIONAL_1BIT.replace("creg m[1];", "creg m[2];").replace(
    "if(m==1)", "if(m==2)"
)


@pytest.mark.parametrize("qasm2_string", [VALID_CONDITIONAL_1BIT, VALID_CONDITIONAL_2BIT])
@pytest.mark.parametrize(
    "sequence",
    [
        lambda m: (m.remove_idle_qubits(), m.validate()),
        lambda m: (m.remove_idle_qubits(), m.remove_idle_qubits()),
        lambda m: (m.remove_idle_qubits(), m.reverse_qubit_order()),
        lambda m: (m.reverse_qubit_order(), m.remove_idle_qubits()),
        lambda m: (m.unroll(), m.remove_measurements(), m.unroll()),
        lambda m: (m.unroll(), m.remove_measurements(), m.validate()),
    ],
)
def test_valid_conditional_survives_transformation_pass_sequences(qasm2_string, sequence):
    """Test that re-filtering an already unrolled body accepts the per-bit chain
    unrolling produced (issue #337).

    remove_measurements, remove_barriers, remove_idle_qubits and reverse_qubit_order all
    reassign _statements to the unrolled AST, so any later validate() or unroll() filters
    unrolled statements rather than source. Validation used to reject that chain outright
    even though the printer collapses it back into 'if (m == n) <statement>'.
    """
    module = loads(qasm2_string)
    sequence(module)
    unrolled = dumps(module)
    assert "x q[" in unrolled
    assert "{" not in unrolled and "}" not in unrolled


def test_else_is_reported_before_a_problem_inside_it():
    """Test that a program with both an 'else' and an inexpressible statement inside it
    reports the 'else' -- the more fundamental of the two -- rather than costing the
    author two round trips to learn QASM 2 has no 'else' at all."""
    qasm2_string = """OPENQASM 2.0;
    include "qelib1.inc";
    qreg q[2];
    creg m[1];
    measure q[0] -> m[0];
    if(m==1) x q[0]; else barrier q;
    """
    with pytest.raises(ValidationError, match="'else' blocks are not supported"):
        loads(qasm2_string).validate()
