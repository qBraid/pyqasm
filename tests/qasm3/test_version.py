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
