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
    qasm3_string = """
    OPENQASM 3;
    include "stdgates.inc";
    // This is a comment
    qubit q;
    // This is another comment
    h q;
    """
    expected_qasm3_string = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit q;
    h q;
    """

    result = loads(qasm3_string)
    actual_qasm3_string = dumps(result)

    check_unrolled_qasm(actual_qasm3_string, expected_qasm3_string)


def test_empty_lines_removed_from_qasm():
    qasm3_string = """
    OPENQASM 3.0;


    include "stdgates.inc";



    qubit q;
    h q;



    
    """
    expected_qasm3_string = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit q;
    h q;
    """

    result = loads(qasm3_string)
    actual_qasm3_string = dumps(result)

    check_unrolled_qasm(actual_qasm3_string, expected_qasm3_string)
