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
Module containing unit tests for unrolling OpenQASM 3 programs
with alias statements.

"""

import re

import pytest

from pyqasm.entrypoint import loads
from pyqasm.exceptions import ValidationError
from tests.utils import (
    check_single_qubit_gate_op,
    check_three_qubit_gate_op,
    check_two_qubit_gate_op,
)

# from .test_if import compare_reference_ir, resources_file


def test_alias():
    """Test converting OpenQASM 3 program with openqasm3.ast.AliasStatement."""

    qasm3_alias_program = """
    OPENQASM 3.0;
    include "stdgates.inc";

    qubit[5] q;

    let myqreg0 = q;
    let myqreg1 = q[1];
    let myqreg2 = q[1:];
    let myqreg3 = q[:4];
    let myqreg4 = q[1:4];
    let myqreg5 = q[1:2:4];
    let myqreg6 = q[{0, 1}];

    x myqreg0[0];
    h myqreg1;
    cx myqreg2[0], myqreg2[1];
    cx myqreg3[2], myqreg3[3];
    ccx myqreg4;
    swap myqreg5[0], myqreg5[1];
    cz myqreg6;
    """
    result = loads(qasm3_alias_program)
    result.unroll()

    assert result.num_qubits == 5
    assert result.num_clbits == 0
    check_single_qubit_gate_op(result.unrolled_ast, 1, [0], "x")
    check_single_qubit_gate_op(result.unrolled_ast, 1, [1], "h")
    check_two_qubit_gate_op(result.unrolled_ast, 2, [[1, 2], [2, 3]], "cx")
    check_three_qubit_gate_op(result.unrolled_ast, 1, [[1, 2, 3]], "ccx")
    check_two_qubit_gate_op(result.unrolled_ast, 1, [[1, 3]], "swap")
    check_two_qubit_gate_op(result.unrolled_ast, 1, [[0, 1]], "cz")


def test_alias_update():
    """Test converting OpenQASM 3 program with alias update."""

    qasm3_alias_program = """
    OPENQASM 3.0;
    include "stdgates.inc";

    qubit[4] q;

    let alias = q[1:];
    let alias = q[2:];

    x alias[1];
    """
    result = loads(qasm3_alias_program)
    result.unroll()
    assert result.num_qubits == 4
    assert result.num_clbits == 0
    check_single_qubit_gate_op(result.unrolled_ast, 1, [3], "x")


def test_valid_alias_redefinition():
    """Test converting OpenQASM 3 program with redefined alias in scope."""

    qasm3_alias_program = """
    OPENQASM 3.0;
    include "stdgates.inc";

    qubit[5] q;
    bit[5] c;
    h q;
    measure q -> c;

    if (c[0] == 1) {
        float[32] alias = 4.3;
    }
    // valid alias
    let alias = q[2];
    x alias;
    """
    result = loads(qasm3_alias_program)
    result.unroll()
    assert result.num_qubits == 5
    assert result.num_clbits == 5

    check_single_qubit_gate_op(result.unrolled_ast, 1, [2], "x")


def test_alias_wrong_indexing(caplog):
    """Test converting OpenQASM 3 program with wrong alias indexing."""
    with pytest.raises(
        ValidationError,
        match=re.escape(
            r"An index set can be specified by a single integer (signed or unsigned), "
            "a comma-separated list of integers contained in braces {a,b,c,…}, or a range"
        ),
    ):
        with caplog.at_level("ERROR"):
            qasm3_alias_program = """
            OPENQASM 3.0;
            include "stdgates.inc";

            qubit[5] q;

            let myqreg = q[1,2];

            x myqreg[0];
            """
            loads(qasm3_alias_program).validate()

    assert "Error at line 7, column 12" in caplog.text
    assert "let myqreg = q[1, 2];" in caplog.text


def test_alias_invalid_discrete_indexing(caplog):
    """Test converting OpenQASM 3 program with invalid alias discrete indexing."""
    with pytest.raises(
        ValidationError,
        match=r"Unsupported value .*",
    ):
        with caplog.at_level("ERROR"):
            qasm3_alias_program = """
            OPENQASM 3.0;
            include "stdgates.inc";

            qubit[5] q;

            let myqreg = q[{0.1}];

            x myqreg[0];
            """
            loads(qasm3_alias_program).validate()

    assert "Error at line 7, column 12" in caplog.text
    assert "let myqreg = q[{0.1}];" in caplog.text


def test_invalid_alias_redefinition(caplog):
    """Test converting OpenQASM 3 program with redefined alias."""
    with pytest.raises(
        ValidationError,
        match=re.escape(r"Re-declaration of variable 'alias'"),
    ):
        with caplog.at_level("ERROR"):
            qasm3_alias_program = """
            OPENQASM 3.0;
            include "stdgates.inc";

            qubit[5] q;
            float[32] alias = 4.2;

            let alias = q[2];

            x alias;
            """
            loads(qasm3_alias_program).validate()

    assert "Error at line 8, column 12" in caplog.text
    assert "let alias = q[2];" in caplog.text


def test_alias_defined_before(caplog):
    """Test converting OpenQASM 3 program with alias defined before the qubit register."""
    with pytest.raises(
        ValidationError,
        match=re.escape(r"Qubit register q2 not found for aliasing"),
    ):
        with caplog.at_level("ERROR"):
            qasm3_alias_program = """
            OPENQASM 3.0;
            include "stdgates.inc";

            qubit[5] q1;

            let myqreg = q2[1];
            """
            loads(qasm3_alias_program).validate()

    assert "Error at line 7, column 12" in caplog.text
    assert "let myqreg = q2[1];" in caplog.text


def test_unsupported_alias(caplog):
    """Test converting OpenQASM 3 program with unsupported alias."""
    with pytest.raises(
        ValidationError,
        match=r"Unsupported aliasing .*",
    ):
        with caplog.at_level("ERROR"):
            qasm3_alias_program = """
            OPENQASM 3.0;
            include "stdgates.inc";

            qubit[5] q;

            let myqreg = q[0] ++ q[1];
            """
            loads(qasm3_alias_program).validate()

    assert "Error at line 7, column 12" in caplog.text
    assert "let myqreg = q[0] ++ q[1];" in caplog.text


# def test_alias_in_scope_1():
#     """Test converting OpenQASM 3 program with alias in scope."""
#     qasm = """
#     OPENQASM 3;
#     include "stdgates.inc";
#     qubit[4] q;
#     bit[4] c;

#     h q;
#     measure q -> c;
#     if(c[0]){
#         let alias = q[0:2];
#         x alias[0];
#         cx alias[0], alias[1];
#     }

#     if(c[1] == 1){
#         cx q[1], q[2];
#     }

#     if(!c[2]){
#         h q[2];
#     }
#     """
#     result = validate(qasm)
#     result.unrolled_ast = str(result).splitlines()

#     check_attributes(result.unrolled_ast, 4, 4)
#     simple_file = resources_file("simple_if.ll")
#     compare_reference_ir(result.bitcode, simple_file)


# def test_alias_in_scope_2():
#     """Test converting OpenQASM 3 program with alias in scope."""
#     qasm = """
#     OPENQASM 3;
#     include "stdgates.inc";
#     qubit[4] q;
#     bit[4] c;

#     let alias = q[0:2];

#     h q;
#     measure q -> c;
#     if(c[0]){
#         x alias[0];
#         cx alias[0], alias[1];
#     }

#     if(c[1] == 1){
#         cx alias[1], q[2];
#     }

#     if(!c[2]){
#         h q[2];
#     }
#     """
#     result = validate(qasm)
#     result.unrolled_ast = str(result).splitlines()

#     check_attributes(result.unrolled_ast, 4, 4)
#     simple_file = resources_file("simple_if.ll")
#     compare_reference_ir(result.bitcode, simple_file)


def test_alias_out_of_scope(caplog):
    """Test converting OpenQASM 3 program with alias out of scope."""
    with pytest.raises(
        ValidationError,
        match="Missing qubit register declaration for 'alias'",
    ):
        with caplog.at_level("ERROR"):
            qasm3_alias_program = """
            OPENQASM 3;
            include "stdgates.inc";
            qubit[4] q;
            bit[4] c;

            h q;
            measure q -> c;
            if(c[0]){
                let alias = q[0:2];
                x alias[0];
                cx alias[0], alias[1];
            }

            if(c[1] == 1){
                cx alias[1], q[2];
            }

            if(!c[2]){
                h q[2];
            }
            """
            loads(qasm3_alias_program).validate()

    assert "Error at line 16, column 16" in caplog.text
    assert "cx alias[1], q[2];" in caplog.text
