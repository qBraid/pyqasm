# Copyright (C) 2024 qBraid
#
# This file is part of pyqasm
#
# Pyqasm is free software released under the GNU General Public License v3
# or later. You can redistribute and/or modify it under the terms of the GPL v3.
# See the LICENSE file in the project root or <https://www.gnu.org/licenses/gpl-3.0.html>.
#
# THERE IS NO WARRANTY for pyqasm, as per Section 15 of the GPL v3.

"""
Module containing unit tests for the if statements.

"""

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
    if(c == 5){
        x q[3];
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
    if (c == 5) {
    x q[3];
    }
    """

    result = loads(qasm)
    result.unroll()
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


def test_incorrect_if():

    with pytest.raises(ValidationError, match=r"Missing if block"):
        loads(
            """
            OPENQASM 3.0;
           include "stdgates.inc";
           qubit[2] q;
           bit[2] c;

           h q;
           measure q->c;

           if(c[0]){
           }
           """
        ).validate()

    with pytest.raises(ValidationError, match=r"Undefined identifier c2 in expression"):
        loads(
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
           """
        ).validate()

    with pytest.raises(ValidationError, match=r"Only '!' supported .*"):
        loads(
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
           """
        ).validate()
    with pytest.raises(ValidationError, match=r"Only '==' supported .*"):
        loads(
            """
            OPENQASM 3.0;
           include "stdgates.inc";
           qubit[2] q;
           bit[2] c;

           h q;
           measure q->c;

           if(c[0] >= 1){
            cx q;
           }
           """
        ).validate()
    with pytest.raises(
        ValidationError,
        match=r"Only simple comparison supported .*",
    ):
        loads(
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
           """
        ).validate()
    with pytest.raises(
        ValidationError,
        match=r"RangeDefinition not supported in branching condition",
    ):
        loads(
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
           """
        ).validate()

    with pytest.raises(
        ValidationError,
        match=r"DiscreteSet not supported in branching condition",
    ):
        loads(
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
           """
        ).validate()
