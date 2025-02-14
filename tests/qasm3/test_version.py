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


@pytest.mark.parametrize(
    "qasm_input, expected_version",
    [
        (
            """
        OPENQASM 3.0;
        qubit q;
        """,
            3.0,
        ),
        (
            """
        OPENQASM 2;
        qubit q;
        """,
            2.0,
        ),
        (
            """
        // Single-line comment
        OPENQASM 1.5; // Inline comment
        qubit q;
        """,
            1.5,
        ),
        (
            """
        /*
          Block comment before the version string
          describing the program.
        */
        OPENQASM 3.2;
        qubit q;
        """,
            3.2,
        ),
    ],
)
def test_extract_qasm_version_valid(qasm_input, expected_version):
    """Test valid OpenQASM version extraction with various inputs."""
    assert Qasm3Analyzer.extract_qasm_version(qasm_input) == expected_version


@pytest.mark.parametrize(
    "qasm_input",
    [
        """
        random string
        """,
        """
        OPENQASM three.point.zero;
        qubit q;
        """,
        """
        OPENQASM 2.0
        qubit q;
        """,
        "",
        "   \n   \t   ",
    ],
)
def test_extract_qasm_version_invalid(qasm_input):
    """Test invalid OpenQASM inputs that should raise QasmParsingError."""
    with pytest.raises(QasmParsingError):
        Qasm3Analyzer.extract_qasm_version(qasm_input)
