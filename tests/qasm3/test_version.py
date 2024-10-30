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
Module containing unit tests for version extraction

"""

import pytest

from pyqasm.analyzer import Qasm3Analyzer
from pyqasm.exceptions import QasmParsingError


def test_extract_version():
    """Test converting OpenQASM 3 program with openqasm3.ast.SwitchStatement."""

    qasm3_program = """
    OPENQASM 3.0;
    qubit q;
    """
    assert Qasm3Analyzer.extract_qasm_version(qasm3_program) == 3


def test_invalid_raises_raises_err():
    """Test converting OpenQASM 3 program with openqasm3.ast.SwitchStatement."""

    qasm3_program = """
    random string
    """
    with pytest.raises(QasmParsingError):
        Qasm3Analyzer.extract_qasm_version(qasm3_program)
