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
Module containing unit tests for preprocess functions.

"""

import os

import pytest

from pyqasm.entrypoint import dumps, load
from pyqasm.exceptions import ValidationError
from tests.utils import check_unrolled_qasm

QASM_RESOURCES_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "resources", "qasm", "custom_include"
)


@pytest.mark.parametrize(
    "test_file, ref_file",
    [
        # Include basic custom gate
        ("include_custom_gates.qasm", "../custom_gate_complex.qasm"),
        # Include variable definitions
        ("include_vars.qasm", "include_vars_ref.qasm"),
        # Include subroutines
        ("include_sub.qasm", "include_sub_ref.qasm"),
        # Multiple includes in single file
        ("multi_include.qasm", "multi_include_ref.qasm"),
        # Include 'sandwiched' between other code
        ("include_sandwiched.qasm", "include_sandwiched_ref.qasm"),
        # Recursive inclusions (include files within included files)
        ("include_nested.qasm", "include_nested_ref.qasm"),
        # Include QASM2 file in QASM2 file
        ("include_qasm2.qasm", "include_qasm2_ref.qasm"),
        # Backward compatibility: Include QASM2 file in QASM3 file
        ("include_qasm2_backward.qasm", "include_qasm2_backward_ref.qasm"),
    ],
)
def test_valid_include_processing(test_file, ref_file):
    """Test that valid include statements are processed correctly."""
    file_path = os.path.join(QASM_RESOURCES_DIR, test_file)
    module = load(file_path)
    ref_file_path = os.path.join(QASM_RESOURCES_DIR, ref_file)
    ref_module = load(ref_file_path)
    check_unrolled_qasm(dumps(module), dumps(ref_module))


def test_include_file_not_found():
    """Test that missing include files raise FileNotFoundError."""
    file_path = os.path.join(QASM_RESOURCES_DIR, "inc_not_found.qasm")
    with pytest.raises(
        FileNotFoundError, match="Include file 'nonexistent.inc' not found at line 3, column 1"
    ):
        load(file_path)


def test_circular_import():
    """Test that circular imports raise ValidationError."""
    file_path = os.path.join(QASM_RESOURCES_DIR, "include_circular_import.qasm")
    with pytest.raises(
        ValidationError,
        match="Circular include detected for file 'circular_import.qasm' at line 3, column 10",
    ):
        load(file_path)
