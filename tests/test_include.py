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
Module containing unit tests for linalg.py functions.

"""
import pytest

from pyqasm import ValidationError, dumps, loads
from tests.utils import check_unrolled_qasm


def test_no_include_added():
    qasm_str = """
    OPENQASM 3.0;
    include "random.qasm";
    """
    expected_qasm_str = """
    OPENQASM 3.0;
    include "random.qasm";
    """
    module = loads(qasm_str)
    module.unroll()
    check_unrolled_qasm(dumps(module), expected_qasm_str)


def test_includes_preserved():
    qasm_str = """
    OPENQASM 3.0;
    include "stdgates.inc";
    include "random.qasm";

    qubit[2] q;
    h q;
    """
    expected_qasm_str = """
    OPENQASM 3.0;
    include "stdgates.inc";
    include "random.qasm";
    qubit[2] q;
    h q[0];
    h q[1];
    """
    module = loads(qasm_str)
    module.unroll()
    check_unrolled_qasm(dumps(module), expected_qasm_str)


def test_repeated_include_raises_error():
    qasm_str = """
    OPENQASM 3.0;
    include "stdgates.inc";
    include "stdgates.inc";
    """
    with pytest.raises(ValidationError):
        module = loads(qasm_str)
        module.validate()


def test_remove_includes():
    qasm_str = """
    OPENQASM 3.0;
    include "stdgates.inc";
    include "random.qasm";

    qubit[2] q;
    h q;
    """
    expected_qasm_str = """
    OPENQASM 3.0;
    qubit[2] q;
    h q[0];
    h q[1];
    """
    module = loads(qasm_str)
    module.remove_includes()
    module.unroll()
    check_unrolled_qasm(dumps(module), expected_qasm_str)


def test_remove_includes_without_include():
    qasm_str = """
    OPENQASM 3.0;

    qubit[2] q;
    h q;
    """
    expected_qasm_str = """
    OPENQASM 3.0;
    qubit[2] q;
    h q[0];
    h q[1];
    """
    module = loads(qasm_str)
    module = module.remove_includes(in_place=False)
    module.unroll()
    check_unrolled_qasm(dumps(module), expected_qasm_str)
