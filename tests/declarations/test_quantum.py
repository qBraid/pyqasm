# Copyright (C) 2024 qBraid
#
# This file is part of the pyqasm
#
# The pyqasm is free software released under the GNU General Public License v3
# or later. You can redistribute and/or modify it under the terms of the GPL v3.
# See the LICENSE file in the project root or <https://www.gnu.org/licenses/gpl-3.0.html>.
#
# THERE IS NO WARRANTY for the pyqasm, as per Section 15 of the GPL v3.
import pytest

from pyqasm.exceptions import ValidationError
from pyqasm.unroller import unroll
from pyqasm.validate import validate
from tests.utils import check_unrolled_qasm


# 1. Test qubit declarations in different ways
def test_qubit_declarations():
    """Test qubit declarations in different ways"""
    qasm3_string = """
    OPENQASM 3;
    include "stdgates.inc";
    qubit q1;
    qubit[2] q2;
    qreg q3[3];
    qubit[1] q4;
    """

    expected_qasm = """OPENQASM 3;
    include "stdgates.inc";
    qubit[1] q1;
    qubit[2] q2;
    qubit[3] q3;
    qubit[1] q4;
    """

    unrolled_qasm = unroll(qasm3_string).unrolled_qasm
    check_unrolled_qasm(unrolled_qasm, expected_qasm)


# 2. Test clbit declarations in different ways
def test_clbit_declarations():
    """Test clbit declarations in different ways"""
    qasm3_string = """
    OPENQASM 3;
    include "stdgates.inc";
    bit c1;
    bit[2] c2;
    creg c3[3];
    bit[1] c4;
    """

    expected_qasm = """OPENQASM 3;
    include "stdgates.inc";
    bit[1] c1;
    bit[2] c2;
    bit[3] c3;
    bit[1] c4;
    """

    unrolled_qasm = unroll(qasm3_string).unrolled_qasm
    check_unrolled_qasm(unrolled_qasm, expected_qasm)


# 3. Test qubit and clbit declarations in different ways
def test_qubit_clbit_declarations():
    """Test qubit and clbit declarations in different ways"""
    qasm3_string = """
    OPENQASM 3;
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

    expected_qasm = """OPENQASM 3;
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

    unrolled_qasm = unroll(qasm3_string).unrolled_qasm
    check_unrolled_qasm(unrolled_qasm, expected_qasm)


def test_qubit_redeclaration_error():
    """Test redeclaration of qubit"""
    with pytest.raises(ValidationError, match="Invalid declaration of register with name 'q1'"):
        qasm3_string = """
        OPENQASM 3;
        include "stdgates.inc";
        qubit q1;
        qubit q1;
        """
        validate(qasm3_string)


def test_clbit_redeclaration_error():
    """Test redeclaration of clbit"""
    with pytest.raises(ValidationError, match="Invalid declaration of register with name 'c1'"):
        qasm3_string = """
        OPENQASM 3;
        include "stdgates.inc";
        bit c1;
        bit[4] c1;
        """
        validate(qasm3_string)
