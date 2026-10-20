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
Module containing unit tests for entrypoint functions.

"""

import os

import pytest
from openqasm3.parser import QASM3ParsingError

from pyqasm.entrypoint import _describe_parse_error, dump, dumps, load, loads
from pyqasm.exceptions import ValidationError
from tests.utils import check_unrolled_qasm

QASM_RESOURCES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources", "qasm")


def test_correct_file_read():
    file_path = os.path.join(QASM_RESOURCES_DIR, "custom_gate_complex.qasm")
    result = load(file_path)
    actual_qasm = dumps(result)
    with open(file_path, "r", encoding="utf-8") as file:
        check_unrolled_qasm(actual_qasm, file.read())


def test_correct_module_dump():
    file_path = os.path.join(QASM_RESOURCES_DIR, "test.qasm")
    qasm_str = 'OPENQASM 3.0;\n include "stdgates.inc";\n qubit q;'
    module = loads(qasm_str)
    dump(module, file_path)
    with open(file_path, "r", encoding="utf-8") as file:
        check_unrolled_qasm(file.read(), qasm_str)
    os.remove(file_path)


def test_incorrect_module_loading_file():
    with pytest.raises(TypeError, match="Input 'filename' must be of type 'str'."):
        load(1)


def test_incorrect_module_loading_program():
    with pytest.raises(
        TypeError, match="Input quantum program must be of type 'str' or 'openqasm3.ast.Program'."
    ):
        loads(1)


def test_incorrect_module_dump():
    with pytest.raises(
        TypeError, match="Input 'module' must be of type pyqasm.modules.base.QasmModule"
    ):
        dumps(1)


def test_incorrect_qasm_version():
    with pytest.raises(ValidationError, match=r"Unsupported OpenQASM version"):
        loads("OPENQASM 4.0;\n qubit q;")


def test_incorrect_module_unroll_raises_error():
    with pytest.raises(ValidationError):
        module = loads("OPENQASM 3.0;\n qubit q; h q[2]")
        module.unroll()


def test_loads_empty_string_raises_validation_error():
    """Empty / whitespace-only input must raise ValidationError, not AttributeError."""
    for program in ("", "   ", "\n\t"):
        with pytest.raises(ValidationError, match="Failed to parse OpenQASM string"):
            loads(program)


@pytest.mark.parametrize(
    "program, reason",
    [
        ("OPENQASM 3.0;\nqubit q;\nbox { x q; };\n", "syntax error near ';' at line 3, column 13"),
        (
            "OPENQASM 3.0;\nqubit q;\nh q",
            "syntax error: unexpected end of program at line 3, column 4",
        ),
        ("OPENQASM 3.0;\nqubit q;\n# comment\n", "L3:C0: token recognition error at: '# '"),
    ],
)
def test_loads_parse_error_names_location(program, reason):
    """A syntax error names the offending token and its position instead of an empty reason."""
    with pytest.raises(ValidationError) as excinfo:
        loads(program)
    assert str(excinfo.value) == f"Failed to parse OpenQASM string: {reason}"


def test_describe_parse_error_without_token():
    """An empty parse error with no ANTLR cause still gets a non-empty reason."""
    assert _describe_parse_error(QASM3ParsingError()) == "invalid OpenQASM syntax"


def test_loads_header_only_module_ok():
    """A header-only OpenQASM 3 program (no statements) remains valid."""
    module = loads("OPENQASM 3.0;\n")
    assert module.num_qubits == 0
    assert module.num_clbits == 0
