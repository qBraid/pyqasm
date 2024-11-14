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
Module containing unit tests for program formatting

"""

from pyqasm.entrypoint import dumps, loads
from tests.utils import check_unrolled_qasm


def test_comments_removed_from_qasm():
    qasm2_string = """
    OPENQASM 2.0;
    include "qelib1.inc";
    // This is a comment
    qreg q[1];
    // This is another comment
    h q[0];
    """
    expected_qasm2_string = """
    OPENQASM 2.0;
    include "qelib1.inc";
    qreg q[1];
    h q[0];
    """

    result = loads(qasm2_string)
    actual_qasm2_string = dumps(result)

    check_unrolled_qasm(actual_qasm2_string, expected_qasm2_string)


def test_empty_lines_removed_from_qasm():
    qasm2_string = """
    OPENQASM 2.0;


    include "qelib1.inc";



    qreg q[1];
    h q[0];



    
    """
    expected_qasm2_string = """
    OPENQASM 2.0;
    include "qelib1.inc";
    qreg q[1];
    h q[0];
    """

    result = loads(qasm2_string)
    actual_qasm2_string = dumps(result)

    check_unrolled_qasm(actual_qasm2_string, expected_qasm2_string)
