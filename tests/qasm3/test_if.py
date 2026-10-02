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
Module containing unit tests for the if statements.

"""

import openqasm3.ast as qasm3_ast
import pytest

from pyqasm.entrypoint import dumps, loads
from pyqasm.exceptions import ValidationError
from tests.utils import check_unrolled_qasm


def test_simple_if():
    qasm = """OPENQASM 3.0;
    include "stdgates.inc";
    qubit[4] q;
    bit[4] c;
    h q;
    measure q -> c;
    if(c[0]){
        x q[0];
        cx q[0], q[1];
    }
    if(c[1] == 1){
        cx q[1], q[2];
    }
    if(c[2] == 1) { 
        // allow empty if block
    }
    """
    expected_qasm = """OPENQASM 3.0;
    include "stdgates.inc";
    qubit[4] q;
    bit[4] c;
    h q[0];
    h q[1];
    h q[2];
    h q[3];
    c[0] = measure q[0];
    c[1] = measure q[1];
    c[2] = measure q[2];
    c[3] = measure q[3];
    if (c[0] == true) {
    x q[0];
    cx q[0], q[1];
    }
    if (c[1] == true) {
    cx q[1], q[2];
    }
    if (c[2] == true) {
    }
    """

    result = loads(qasm)
    result.unroll()
    print(result)
    assert result.num_clbits == 4
    assert result.num_qubits == 4
    check_unrolled_qasm(dumps(result), expected_qasm)


def test_complex_if():
    qasm = """OPENQASM 3.0;
    include "stdgates.inc";
    gate custom a, b{
        cx a, b;
        h a;
    }
    qubit[4] q;
    bit[4] c;
    bit[4] c0;
    h q;
    measure q -> c0;
    if(c0[0]){
        x q[0];
        cx q[0], q[1];
        if (c0[1]){
            cx q[1], q[2];
        }
    }
    if (c[0]){
        custom q[2], q[3];
    }

    // this block will be removed and only statements 
    // will be present
    array[int[32], 8] arr;
    arr[0] = 1;
    if(arr[0] >= 1){
        h q[0];
        h q[1];
    }
    """
    expected_qasm = """OPENQASM 3.0;
    include "stdgates.inc";
    qubit[4] q;
    bit[4] c;
    bit[4] c0;
    h q[0];
    h q[1];
    h q[2];
    h q[3];
    c0[0] = measure q[0];
    c0[1] = measure q[1];
    c0[2] = measure q[2];
    c0[3] = measure q[3];
    if (c0[0] == true) {
    x q[0];
    cx q[0], q[1];
    if (c0[1] == true) {
        cx q[1], q[2];
    }
    }
    if (c[0] == true) {
        cx q[2], q[3];
        h q[2];
    }
    h q[0];
    h q[1];
    """
    result = loads(qasm)
    result.unroll()
    assert result.num_clbits == 8
    assert result.num_qubits == 4
    check_unrolled_qasm(dumps(result), expected_qasm)


def test_multi_bit_if():
    qasm = """OPENQASM 3.0;
    include "stdgates.inc";
    qubit[1] q;
    bit[4] c;
    if(c == 3){
        h q[0];
    }
    if(c >= 3){
        h q[0];
    } else {
        x q[0];
    }
    if(c <= 3){
        h q[0];
    } else {
        x q[0];
    }
    if(c < 4){
        h q[0];
    } else {
        x q[0];
    }
    """
    expected_qasm = """OPENQASM 3.0;
    include "stdgates.inc";
    qubit[1] q;
    bit[4] c;
    if (c[3] == false) {
        if (c[2] == false) {
            if (c[1] == true) {
                if (c[0] == true) {
                    h q[0];
                }
            }
        }
    }
    if (c[3] == false) {
        if (c[2] == false) {
            if (c[1] == true) {
                if (c[0] == true) {
                    h q[0];
                } else {
                    x q[0];
                }
            } else {
                x q[0];
            }
        } else {
            h q[0];
        }
    } else {
        h q[0];
    }
    if (c[3] == false) {
        if (c[2] == false) {
            h q[0];
        } else {
            x q[0];
        }
    } else {
        x q[0];
    }
    if (c[3] == false) {
        if (c[2] == false) {
            h q[0];
        } else {
            x q[0];
        }
    } else {
        x q[0];
    }
    """

    result = loads(qasm)
    result.unroll()
    assert result.num_clbits == 4
    assert result.num_qubits == 1
    check_unrolled_qasm(dumps(result), expected_qasm)


def test_register_condition_bit_order():
    """c[0] is the least significant bit, so c == 2 means c[1] = 1 and c[0] = 0."""
    qasm = """OPENQASM 3.0;
    include "stdgates.inc";
    qubit[1] q;
    bit[2] c;
    if (c == 2) {
        x q[0];
    }
    """
    expected_qasm = """OPENQASM 3.0;
    include "stdgates.inc";
    qubit[1] q;
    bit[2] c;
    if (c[1] == true) {
        if (c[0] == false) {
            x q[0];
        }
    }
    """
    result = loads(qasm)
    result.unroll()
    check_unrolled_qasm(dumps(result), expected_qasm)


def _branch_bits(statements):
    """Collect ``{bit index: value}`` from an unrolled chain of single-bit branches."""
    bits = {}
    while len(statements) == 1 and isinstance(statements[0], qasm3_ast.BranchingStatement):
        condition = statements[0].condition
        bits[condition.lhs.index[0].value] = condition.rhs.value
        statements = statements[0].if_block
    return bits


@pytest.mark.parametrize(
    "width,value",
    [(1, 0), (1, 1), (2, 1), (2, 2), (3, 1), (3, 4), (3, 6), (5, 1), (5, 19)],
)
def test_register_equality_bits(width, value):
    qasm = f"""OPENQASM 3.0;
    include "stdgates.inc";
    qubit[1] q;
    bit[{width}] c;
    if (c == {value}) {{
        x q[0];
    }}
    """
    result = loads(qasm)
    result.unroll()
    branch = [s for s in result.unrolled_ast.statements if isinstance(s, qasm3_ast.Statement)]
    assert _branch_bits(branch[-1:]) == {i: bool(value >> i & 1) for i in range(width)}


def _runs_body(statements, register_value):
    """Whether ``x q[0]`` executes when the 1-qubit program's register holds ``register_value``."""
    for statement in statements:
        if isinstance(statement, qasm3_ast.QuantumGate):
            return True
        if isinstance(statement, qasm3_ast.BranchingStatement):
            condition = statement.condition
            bit = register_value >> condition.lhs.index[0].value & 1
            taken = statement.if_block if bit == condition.rhs.value else statement.else_block
            if _runs_body(taken, register_value):
                return True
    return False


@pytest.mark.parametrize("width", [1, 2, 3])
@pytest.mark.parametrize("op", ["==", ">=", "<=", ">", "<"])
def test_register_condition_matches_integer_comparison(width, op):
    """Every unrolled comparison, including out-of-range values, agrees with integer comparison."""
    for value in range(-1, 2**width + 1):
        qasm = f"""OPENQASM 3.0;
        include "stdgates.inc";
        qubit[1] q;
        bit[{width}] c;
        if (c {op} {value}) {{
            x q[0];
        }}
        """
        result = loads(qasm)
        result.unroll()
        for register_value in range(2**width):
            expected = eval(f"{register_value} {op} {value}")  # pylint: disable=eval-used
            assert (
                _runs_body(result.unrolled_ast.statements, register_value) == expected
            ), f"c {op} {value} with c = {register_value}"


@pytest.mark.parametrize(
    "condition,expected_body",
    [
        ("c[1] == 1", "if (c[1] == true) {\n    x q[0];\n    }"),
        ("c[1] < 1", "if (c[1] == false) {\n    x q[0];\n    }"),
        ("c[1] > 0", "if (c[1] == true) {\n    x q[0];\n    }"),
        ("c[1] >= 0", "x q[0];"),
        ("c[1] == 2", ""),
        ("!c[1]", "if (c[1] == false) {\n    x q[0];\n    }"),
    ],
)
def test_single_bit_condition(condition, expected_body):
    qasm = f"""OPENQASM 3.0;
    include "stdgates.inc";
    qubit[1] q;
    bit[2] c;
    if ({condition}) {{
        x q[0];
    }}
    """
    expected_qasm = f"""OPENQASM 3.0;
    include "stdgates.inc";
    qubit[1] q;
    bit[2] c;
    {expected_body}
    """
    result = loads(qasm)
    result.unroll()
    check_unrolled_qasm(dumps(result), expected_qasm)


@pytest.mark.parametrize(
    "qasm_code,error_message,line_num,col_num,err_line",
    [
        (
            """
            OPENQASM 3.0;
            include "stdgates.inc";
            qubit[2] q;
            bit[2] c;
            h q;
            measure q->c;
            if(c2[0]){
                cx q;
            }
            """,
            r"Undefined identifier 'c2' in expression",
            8,
            15,
            "c2[0]",
        ),
        (
            """
            OPENQASM 3.0;
            include "stdgates.inc";
            qubit[2] q;
            bit[2] c;
            h q;
            measure q->c;
            if(~c[0]){
                cx q;
            }
            """,
            r"Only '!' supported .*",
            8,
            15,
            "~c[0]",
        ),
        (
            """
            OPENQASM 3.0;
            include "stdgates.inc";
            qubit[2] q;
            bit[2] c;
            h q;
            measure q->c;
            if(c[0] >> 1){
                cx q;
            }
            """,
            r"Only {==, >=, <=, >, <} supported in branching condition with classical register",
            8,
            15,
            "c[0] >> 1",
        ),
        (
            """
            OPENQASM 3.0;
            include "stdgates.inc";
            qubit[2] q;
            bit[2] c;
            h q;
            measure q->c;
            if(c){
                cx q;
            }
            """,
            r"Only simple comparison supported .*",
            8,
            15,
            "c",
        ),
        (
            """
            OPENQASM 3.0;
            include "stdgates.inc";
            qubit[2] q;
            bit[2] c;
            h q;
            measure q->c;
            if(c[0:1]){
                cx q;
            }
            """,
            r"RangeDefinition not supported in branching condition",
            8,
            15,
            "c[0:1]",
        ),
        (
            """
            OPENQASM 3.0;
            include "stdgates.inc";
            qubit[2] q;
            bit[2] c;
            h q;
            measure q->c;
            if(c[{0,1}]){
                cx q;
            }
            """,
            r"DiscreteSet not supported in branching condition",
            8,
            15,
            "c[{0, 1}]",
        ),
    ],
)  # pylint: disable-next= too-many-arguments
def test_incorrect_if(qasm_code, error_message, line_num, col_num, err_line, caplog):
    with pytest.raises(ValidationError, match=error_message):
        with caplog.at_level("ERROR"):
            loads(qasm_code).validate()

    assert f"Error at line {line_num}, column {col_num}" in caplog.text
    assert err_line in caplog.text
