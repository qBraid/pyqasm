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
Module containing unit tests for sizeof operation.

"""
import pytest

from pyqasm.entrypoint import loads
from pyqasm.exceptions import ValidationError
from tests.utils import check_single_qubit_rotation_op


def test_simple_sizeof():
    """Test sizeof over an array"""
    qasm3_string = """
    OPENQASM 3;
    include "stdgates.inc";

    array[int[32], 3, 2] my_ints;

    const uint[32] size0 = sizeof(my_ints); // this is 3 and valid

    int[32] size1 = sizeof(my_ints); // this is 3

    int[32] size2 = sizeof(my_ints, 1); // this is 2

    int[32] size3 = sizeof(my_ints, 0); // this is 3
    qubit[2] q;

    rx(size0) q[0];
    rx(size1) q[0];
    rx(size2) q[1];
    rx(size3) q[1];
    """

    result = loads(qasm3_string)
    result.unroll()

    assert result.num_qubits == 2

    check_single_qubit_rotation_op(result.unrolled_ast, 4, [0, 0, 1, 1], [3, 3, 2, 3], "rx")


def test_sizeof_multiple_types():
    """Test sizeof over an array of bit, int and float"""
    qasm3_string = """
    OPENQASM 3;
    include "stdgates.inc";

    array[int[32], 3, 2] my_ints;
    array[float[64], 3, 2] my_floats;

    int[32] size1 = sizeof(my_ints, 1); // this is 2

    int[32] size2 = sizeof(my_floats, 0); // this is 3 
    qubit[2] q;

    rx(size1) q[1];
    rx(size2) q[1];
    """

    result = loads(qasm3_string)
    result.unroll()

    assert result.num_qubits == 2
    check_single_qubit_rotation_op(result.unrolled_ast, 2, [1, 1], [2, 3], "rx")


def test_unsupported_target():
    """Test sizeof over index expressions"""
    with pytest.raises(ValidationError, match=r"Unsupported target type .*"):
        qasm3_string = """
        OPENQASM 3;
        include "stdgates.inc";

        array[int[32], 3, 2] my_ints;

        int[32] size1 = sizeof(my_ints[0]); // this is invalid
        """
        loads(qasm3_string).validate()


def test_sizeof_on_non_array():
    """Test sizeof on a non-array"""
    with pytest.raises(
        ValidationError, match="Invalid sizeof usage, variable my_int is not an array."
    ):
        qasm3_string = """
        OPENQASM 3;
        include "stdgates.inc";

        int[32] my_int = 3;

        int[32] size1 = sizeof(my_int); // this is invalid
        """
        loads(qasm3_string).validate()


def test_out_of_bounds_reference():
    """Test sizeof on an out of bounds reference"""
    with pytest.raises(
        ValidationError, match="Index 3 out of bounds for array my_ints with 2 dimensions"
    ):
        qasm3_string = """
        OPENQASM 3;
        include "stdgates.inc";

        array[int[32], 3, 2] my_ints;

        int[32] size1 = sizeof(my_ints, 3); // this is invalid
        """
        loads(qasm3_string).validate()
