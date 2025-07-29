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


def test_correct_include_processing():
    """Test that simple custom include statements are processed correctly."""
    file_path = os.path.join(QASM_RESOURCES_DIR, "include_custom_gates.qasm")
    module = load(file_path)
    ref_file_path = os.path.join(os.path.dirname(QASM_RESOURCES_DIR), "custom_gate_complex.qasm")
    ref_module = load(ref_file_path)
    check_unrolled_qasm(dumps(module), dumps(ref_module))


def test_correct_include_processing_complex():
    """Test that complex custom include statements are processed correctly."""
    file_path = os.path.join(QASM_RESOURCES_DIR, "include_vars.qasm")
    module = load(file_path)
    ref_file_path = os.path.join(QASM_RESOURCES_DIR, "include_vars_ref.qasm")
    ref_module = load(ref_file_path)
    check_unrolled_qasm(dumps(module), dumps(ref_module))


def test_include_custom_subroutine():
    """Test that inclusion of custom subroutines is processed correctly."""
    file_path = os.path.join(QASM_RESOURCES_DIR, "include_sub.qasm")
    module = load(file_path)
    ref_file_path = os.path.join(QASM_RESOURCES_DIR, "include_sub_ref.qasm")
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


def test_multiple_includes():
    """Test that multiple include statements in a file are processed correctly."""
    file_path = os.path.join(QASM_RESOURCES_DIR, "multi_include.qasm")
    module = load(file_path)
    ref_file_path = os.path.join(QASM_RESOURCES_DIR, "multi_include_ref.qasm")
    ref_module = load(ref_file_path)
    check_unrolled_qasm(dumps(module), dumps(ref_module))


def test_include_sandwiched():
    """Test that include statements sandwiched between other statements are processed correctly."""
    file_path = os.path.join(QASM_RESOURCES_DIR, "include_sandwiched.qasm")
    module = load(file_path)
    ref_file_path = os.path.join(QASM_RESOURCES_DIR, "include_sandwiched_ref.qasm")
    ref_module = load(ref_file_path)
    check_unrolled_qasm(dumps(module), dumps(ref_module))


def test_nested_include_processing():
    """Test that nested include statements are recursively processed correctly."""
    file_path = os.path.join(QASM_RESOURCES_DIR, "include_nested.qasm")
    module = load(file_path)
    ref_file_path = os.path.join(QASM_RESOURCES_DIR, "include_nested_ref.qasm")
    ref_module = load(ref_file_path)
    check_unrolled_qasm(dumps(module), dumps(ref_module))
