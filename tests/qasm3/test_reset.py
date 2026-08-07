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


def test_reset_physical_qubit_preserves_identifier():
    """Reset on a physical qubit keeps the "$n" spelling.

    Gate and measurement operands already keep physical qubits as-is; reset used to
    rewrite them to the internal pulse register ("__PYQASM_QUBITS__[2]"), which names
    a register the program never declares and does not round-trip through dumps().
    """
    qasm3_string = """
    OPENQASM 3.0;
    include "stdgates.inc";
    bit[1] c;
    h $2;
    reset $2;
    c[0] = measure $2;
    """
    module = loads(qasm3_string)
    module.unroll()

    expected = """OPENQASM 3.0;
include "stdgates.inc";
bit[1] c;
h $2;
reset $2;
c[0] = measure $2;
"""
    check_unrolled_qasm(dumps(module), expected)


def test_reset_physical_qubit_is_counted():
    """A physical qubit touched only by reset is still registered, so num_qubits
    reflects it (the early return used to skip registration entirely)."""
    qasm3_string = """
    OPENQASM 3.0;
    include "stdgates.inc";
    reset $3;
    """
    module = loads(qasm3_string)
    module.unroll()

    assert module.num_qubits == 4  # "$3" is hardware qubit 3, so 4 qubits are addressed


def test_reset_physical_qubit_unrolled_output_is_reloadable():
    """The unrolled program must itself be valid OpenQASM 3 that pyqasm can reload."""
    module = loads('OPENQASM 3.0;\ninclude "stdgates.inc";\nreset $0;\n')
    module.unroll()

    reloaded = loads(dumps(module))
    reloaded.validate()


def test_reset_on_register_named_like_the_internal_one_is_unrolled():
    """A user register whose name merely starts with the reserved internal register
    name is a normal register and must be unrolled.

    The internal register is matched on its exact name, or on the name followed by an
    index or slice. Matching the bare prefix instead also swallowed registers like
    "__PYQASM_QUBITS__foo", short-circuiting them out of unrolling so that
    "reset __PYQASM_QUBITS__foo;" silently reset nothing.
    """
    qasm3_string = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[2] __PYQASM_QUBITS__foo;
    reset __PYQASM_QUBITS__foo;
    """
    module = loads(qasm3_string)
    module.unroll()

    expected = """OPENQASM 3.0;
include "stdgates.inc";
qubit[2] __PYQASM_QUBITS__foo;
reset __PYQASM_QUBITS__foo[0];
reset __PYQASM_QUBITS__foo[1];
"""
    check_unrolled_qasm(dumps(module), expected)
