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
Module containing unit tests for parsing and unrolling programs that contain quantum
declarations.

"""
import pytest

from pyqasm.entrypoint import dumps, loads
from pyqasm.exceptions import ValidationError
from tests.utils import check_unrolled_qasm


# 1. Test qubit declarations in different ways
def test_qubit_declarations():
    """Test qubit declarations in different ways"""
    qasm3_string = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit q1;
    qubit[2] q2;
    qreg q3[3];
    qubit[1] q4;

    const int[32] N = 10;
    qubit[N] q5;
    """

    expected_qasm = """OPENQASM 3.0;
    include "stdgates.inc";
    qubit[1] q1;
    qubit[2] q2;
    qubit[3] q3;
    qubit[1] q4;
    qubit[10] q5;
    """

    result = loads(qasm3_string)
    result.unroll()
    unrolled_qasm = dumps(result)

    check_unrolled_qasm(unrolled_qasm, expected_qasm)


# 2. Test clbit declarations in different ways
def test_clbit_declarations():
    """Test clbit declarations in different ways"""
    qasm3_string = """
    OPENQASM 3.0;
    include "stdgates.inc";
    bit c1;
    bit[2] c2;
    creg c3[3];
    bit[1] c4;

    const int[32] size = 10;
    bit[size] c5;
    """

    expected_qasm = """OPENQASM 3.0;
    include "stdgates.inc";
    bit[1] c1;
    bit[2] c2;
    bit[3] c3;
    bit[1] c4;
    bit[10] c5;
    """

    result = loads(qasm3_string)
    result.unroll()
    unrolled_qasm = dumps(result)

    check_unrolled_qasm(unrolled_qasm, expected_qasm)


# 3. Test qubit and clbit declarations in different ways
def test_qubit_clbit_declarations():
    """Test qubit and clbit declarations in different ways"""
    qasm3_string = """
    OPENQASM 3.0;
    include "stdgates.inc";

    // qubit declarations
    qubit q1;
    qubit[2] q2;
    qreg q3[3];
    qubit[1] q4;

    // clbit declarations
    bit c1;
    bit[2] c2;
    creg c3[3];
    bit[1] c4;
    """

    expected_qasm = """OPENQASM 3.0;
    include "stdgates.inc";
    qubit[1] q1;
    qubit[2] q2;
    qubit[3] q3;
    qubit[1] q4;
    bit[1] c1;
    bit[2] c2;
    bit[3] c3;
    bit[1] c4;
    """

    result = loads(qasm3_string)
    result.unroll()
    unrolled_qasm = dumps(result)

    check_unrolled_qasm(unrolled_qasm, expected_qasm)


def test_qubit_redeclaration_error():
    """Test redeclaration of qubit"""
    with pytest.raises(ValidationError, match="Re-declaration of quantum register with name 'q1'"):
        qasm3_string = """
        OPENQASM 3.0;
        include "stdgates.inc";
        qubit q1;
        qubit q1;
        """
        loads(qasm3_string).validate()


def test_invalid_qubit_name():
    """Test that qubit name can not be one of constants"""
    with pytest.raises(
        ValidationError, match="Can not declare quantum register with keyword name 'pi'"
    ):
        qasm3_string = """
        OPENQASM 3.0;
        include "stdgates.inc";
        qubit pi;
        """
        loads(qasm3_string).validate()


def test_clbit_redeclaration_error():
    """Test redeclaration of clbit"""
    with pytest.raises(ValidationError, match=r"Re-declaration of variable c1"):
        qasm3_string = """
        OPENQASM 3.0;
        include "stdgates.inc";
        bit c1;
        bit[4] c1;
        """
        loads(qasm3_string).validate()


def test_non_constant_size():
    """Test non-constant size in qubit and clbit declarations"""
    with pytest.raises(
        ValidationError, match=r"Variable 'N' is not a constant in given expression"
    ):
        qasm3_string = """
        OPENQASM 3.0;
        include "stdgates.inc";
        int[32] N = 10;
        qubit[N] q;
        """
        loads(qasm3_string).validate()

    with pytest.raises(
        ValidationError, match=r"Variable 'size' is not a constant in given expression"
    ):
        qasm3_string = """
        OPENQASM 3.0;
        include "stdgates.inc";
        int[32] size = 10;
        bit[size] c;
        """
        loads(qasm3_string).validate()
