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
Module containing unit tests for bit-typed subroutine return values.

Reference: https://openqasm.com/versions/3.1/language/subroutines.html

"""

import pytest

from pyqasm.entrypoint import dumps, loads
from pyqasm.exceptions import ValidationError
from tests.utils import check_measure_op, check_single_qubit_gate_op, check_unrolled_qasm


def test_bit_return():
    """Test that a subroutine returning 'bit' initialises a caller's bit variable."""
    qasm_str = """OPENQASM 3.0;
    include "stdgates.inc";
    def my_function(qubit q) -> bit {
        h q;
        bit b = "1";
        return b;
    }
    qubit q;
    bit x = my_function(q);
    """

    result = loads(qasm_str)
    result.unroll()

    check_single_qubit_gate_op(result.unrolled_ast, 1, [0], "h")
    check_unrolled_qasm(
        dumps(result),
        """OPENQASM 3.0;
        include "stdgates.inc";
        qubit[1] q;
        h q[0];
        bit[1] b = "1";
        bit[1] x = "1";
        """,
    )


def test_bit_register_return():
    """Test that a subroutine returning 'bit[n]' initialises a caller's bit[n] variable."""
    qasm_str = """OPENQASM 3.0;
    include "stdgates.inc";
    def my_function(qubit q) -> bit[2] {
        h q;
        bit[2] b = "10";
        return b;
    }
    qubit q;
    bit[2] x = my_function(q);
    """

    result = loads(qasm_str)
    result.unroll()

    check_unrolled_qasm(
        dumps(result),
        """OPENQASM 3.0;
        include "stdgates.inc";
        qubit[1] q;
        h q[0];
        bit[2] b = "10";
        bit[2] x = "10";
        """,
    )


def test_return_measure():
    """Test that 'return measure q;' measures the caller's qubit and binds the result."""
    qasm_str = """OPENQASM 3.0;
    include "stdgates.inc";
    def my_function(qubit qin) -> bit {
        h qin;
        return measure qin;
    }
    qubit[2] q;
    bit x = my_function(q[1]);
    """

    result = loads(qasm_str)
    result.unroll()
    assert result.num_qubits == 2

    check_single_qubit_gate_op(result.unrolled_ast, 1, [1], "h")
    check_measure_op(result.unrolled_ast, 1, [(("q", 1), ("__my_function_return_0", 0))])
    check_unrolled_qasm(
        dumps(result),
        """OPENQASM 3.0;
        include "stdgates.inc";
        qubit[2] q;
        h q[1];
        bit[1] __my_function_return_0;
        __my_function_return_0[0] = measure q[1];
        bit[1] x = __my_function_return_0;
        """,
    )


def test_return_measure_register():
    """Test that a multi-qubit 'return measure q;' unrolls to one measurement per qubit."""
    qasm_str = """OPENQASM 3.0;
    include "stdgates.inc";
    def my_function(qubit[2] q) -> bit[2] {
        h q[0];
        return measure q;
    }
    qubit[2] q;
    bit[2] x = my_function(q);
    """

    result = loads(qasm_str)
    result.unroll()

    check_measure_op(
        result.unrolled_ast,
        2,
        [
            (("q", 0), ("__my_function_return_0", 0)),
            (("q", 1), ("__my_function_return_0", 1)),
        ],
    )


def test_assign_then_return_measure():
    """Test that measuring into a local bit and returning it binds the caller's variable."""
    qasm_str = """OPENQASM 3.0;
    include "stdgates.inc";
    def my_function(qubit q) -> bit {
        bit c;
        h q;
        c = measure q;
        return c;
    }
    qubit q;
    bit x = my_function(q);
    """

    result = loads(qasm_str)
    result.unroll()

    check_measure_op(result.unrolled_ast, 1, [(("q", 0), ("c", 0))])
    check_unrolled_qasm(
        dumps(result),
        """OPENQASM 3.0;
        include "stdgates.inc";
        qubit[1] q;
        bit[1] c;
        h q[0];
        c[0] = measure q[0];
        bit[1] x = c;
        """,
    )


def test_bit_return_in_caller_assignment():
    """Test that a bit return can be assigned to an already declared caller variable."""
    qasm_str = """OPENQASM 3.0;
    include "stdgates.inc";
    def my_function(qubit q) -> bit {
        return measure q;
    }
    qubit q;
    bit x;
    x = my_function(q);
    """

    result = loads(qasm_str)
    result.unroll()

    check_unrolled_qasm(
        dumps(result),
        """OPENQASM 3.0;
        include "stdgates.inc";
        qubit[1] q;
        bit[1] x;
        bit[1] __my_function_return_0;
        __my_function_return_0[0] = measure q[0];
        x = __my_function_return_0;
        """,
    )


def test_nested_subroutine_forwards_bit_return():
    """Test that an outer subroutine forwards an inner subroutine's measured bit return."""
    qasm_str = """OPENQASM 3.0;
    include "stdgates.inc";
    def inner(qubit q) -> bit {
        return measure q;
    }
    def outer(qubit q) -> bit {
        h q;
        return inner(q);
    }
    qubit q;
    bit x = outer(q);
    """

    result = loads(qasm_str)
    result.unroll()

    check_single_qubit_gate_op(result.unrolled_ast, 1, [0], "h")
    check_measure_op(result.unrolled_ast, 1, [(("q", 0), ("__inner_return_0", 0))])
    check_unrolled_qasm(
        dumps(result),
        """OPENQASM 3.0;
        include "stdgates.inc";
        qubit[1] q;
        h q[0];
        bit[1] __inner_return_0;
        __inner_return_0[0] = measure q[0];
        bit[1] x = __inner_return_0;
        """,
    )


def test_nested_subroutine_forwards_literal_bit_return():
    """Test that a forwarded, statically known bit return folds to a bitstring literal."""
    qasm_str = """OPENQASM 3.0;
    def inner() -> bit[3] {
        bit[3] b = "101";
        return b;
    }
    def outer() -> bit[3] {
        return inner();
    }
    bit[3] x = outer();
    """

    result = loads(qasm_str)
    result.unroll()

    check_unrolled_qasm(
        dumps(result),
        """OPENQASM 3.0;
        bit[3] b = "101";
        bit[3] x = "101";
        """,
    )


def test_repeated_calls_get_distinct_return_registers():
    """Test that each call to a measurement-returning subroutine gets its own temporary
    register. The return statement is shared between calls, so a qubit operand rewritten
    in place on the first call used to leak into the second."""
    qasm_str = """OPENQASM 3.0;
    include "stdgates.inc";
    def my_function(qubit qin) -> bit {
        return measure qin;
    }
    qubit[2] q;
    bit a = my_function(q[0]);
    bit b = my_function(q[1]);
    """

    result = loads(qasm_str)
    result.unroll()

    check_measure_op(
        result.unrolled_ast,
        2,
        [
            (("q", 0), ("__my_function_return_0", 0)),
            (("q", 1), ("__my_function_return_1", 0)),
        ],
    )


def test_module_can_be_unrolled_twice():
    """Test that unrolling twice reproduces the same program. Substituting the temporary
    register into the source declaration used to make the second pass fail with
    'Undefined identifier', which `depth()` hit because it re-unrolls a copy."""
    qasm_str = """OPENQASM 3.0;
    include "stdgates.inc";
    def my_function(qubit qin) -> bit {
        h qin;
        return measure qin;
    }
    qubit q;
    bit x = my_function(q);
    """

    result = loads(qasm_str)
    result.unroll()
    first_pass = dumps(result)

    assert result.depth() == 2
    result.unroll()
    check_unrolled_qasm(dumps(result), first_pass)


@pytest.mark.parametrize(
    "return_type, returned, expected",
    [
        ("bit[2]", "return 3.5;", "Expected bit\\[2\\] but got float"),
        ("bit", "return 2.5;", "Expected bit but got float"),
        ("int[8]", 'return "10";', "Expected int\\[8\\] but got str"),
    ],
)
def test_return_type_mismatch_names_both_types(return_type, returned, expected, caplog):
    """Test that a declared/returned type mismatch raises a ValidationError, not
    an AttributeError, and names both the declared and the returned type."""
    qasm_str = f"""OPENQASM 3.0;
    def my_function() -> {return_type} {{
        {returned}
    }}
    my_function();
    """

    with pytest.raises(
        ValidationError,
        match=rf"Return type mismatch for subroutine 'my_function'\. {expected}",
    ):
        with caplog.at_level("ERROR"):
            loads(qasm_str).validate()

    assert "Error at line 3, column 8" in caplog.text


def test_return_measure_from_void_subroutine(caplog):
    """Test that returning a measurement from a void subroutine names both types."""
    qasm_str = """OPENQASM 3.0;
    def my_function(qubit q) {
        return measure q;
    }
    qubit q;
    my_function(q);
    """

    with pytest.raises(
        ValidationError,
        match=r"Return type mismatch for subroutine 'my_function'\. "
        r"Expected void but got bit from a measurement",
    ):
        with caplog.at_level("ERROR"):
            loads(qasm_str).validate()

    assert "Error at line 3, column 8" in caplog.text
