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
Module containing unit tests for linalg.py functions.

"""

import openqasm3
import pytest

from pyqasm import ValidationError, dumps, load, loads
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


# --- include_dir: resolving includes for a program held as a string (issue #368) ---

MYGATES_INC = "gate mygate q {\n    h q;\n}\n"

PROGRAM_WITH_CUSTOM_INCLUDE = """
OPENQASM 2.0;
include "qelib1.inc";
include "mygates.inc";
qreg q[2];
mygate q[0];
"""


@pytest.fixture(name="include_dir")
def include_dir_fixture(tmp_path):
    """A directory holding mygates.inc, which defines `mygate` as an `h`."""
    (tmp_path / "mygates.inc").write_text(MYGATES_INC, encoding="utf-8")
    return str(tmp_path)


def test_loads_resolves_include_from_include_dir(include_dir):
    """A string has no directory of its own, so the caller names one. Without this the
    gate call failed with 'Unsupported / undeclared QASM operation: mygate'."""
    expected_qasm_str = """
    OPENQASM 2.0;
    include "qelib1.inc";
    qreg q[2];
    h q[0];
    """
    module = loads(PROGRAM_WITH_CUSTOM_INCLUDE, include_dir=include_dir)
    module.unroll()
    check_unrolled_qasm(dumps(module), expected_qasm_str)


def test_loads_and_load_agree_on_the_same_program(tmp_path, include_dir):
    """The two entrypoints are documented as equivalent, so one program must give the
    same result whether it arrives as a file or as a string."""
    path = tmp_path / "prog.qasm"
    path.write_text(PROGRAM_WITH_CUSTOM_INCLUDE, encoding="utf-8")

    from_file = load(str(path))
    from_string = loads(PROGRAM_WITH_CUSTOM_INCLUDE, include_dir=include_dir)
    from_file.unroll()
    from_string.unroll()
    assert dumps(from_file) == dumps(from_string)


def test_nested_include_resolves_beside_the_file_that_named_it(tmp_path):
    """A resolved include has a path of its own, so its own includes resolve beside it."""
    (tmp_path / "outer.inc").write_text(
        'include "inner.inc";\ngate outer q { inner q; }\n', encoding="utf-8"
    )
    (tmp_path / "inner.inc").write_text("gate inner q {\n    x q;\n}\n", encoding="utf-8")
    qasm_str = """
    OPENQASM 2.0;
    include "qelib1.inc";
    include "outer.inc";
    qreg q[1];
    outer q[0];
    """
    module = loads(qasm_str, include_dir=str(tmp_path))
    module.unroll()
    assert "x q[0];" in dumps(module)


def test_loads_reports_the_unresolved_include_by_name(tmp_path):
    """The reported symptom was a downstream 'undeclared operation' error that sent you
    looking at the gate table. The error now names the include and the directory."""
    with pytest.raises(ValidationError, match="'mygates.inc' not found in include_dir"):
        loads(PROGRAM_WITH_CUSTOM_INCLUDE, include_dir=str(tmp_path))


def test_loads_without_include_dir_still_passes_includes_through():
    """Resolution is opt-in: without the kwarg loads() reads no files at all, and an
    unresolved custom include reaches the output exactly as before."""
    module = loads(PROGRAM_WITH_CUSTOM_INCLUDE)
    assert 'include "mygates.inc";' in dumps(module)


def test_include_dir_wins_over_the_directory_of_the_file(tmp_path, include_dir):
    """For load(), include_dir is tried first, so a caller can override an include that
    sits next to the program."""
    (tmp_path / "beside").mkdir()
    (tmp_path / "beside" / "mygates.inc").write_text("gate mygate q { x q; }\n", encoding="utf-8")
    path = tmp_path / "beside" / "prog.qasm"
    path.write_text(PROGRAM_WITH_CUSTOM_INCLUDE, encoding="utf-8")

    module = load(str(path), include_dir=include_dir)
    module.unroll()
    assert "h q[0];" in dumps(module)
    assert "x q[0];" not in dumps(module)


def test_include_dir_rejected_for_a_parsed_program(include_dir):
    """An already-parsed Program has no include statements left to resolve, so the kwarg
    cannot do anything and must not be silently ignored."""
    program = openqasm3.parse("OPENQASM 3.0;\nqubit[1] q;\n")
    with pytest.raises(ValueError, match="include_dir"):
        loads(program, include_dir=include_dir)


@pytest.mark.parametrize("value", [3, ["dir"], {"a": "b"}])
def test_include_dir_rejects_a_non_path(value):
    """The kwarg must fail at the call site, in the shape the other loads() kwargs use."""
    with pytest.raises(TypeError, match="include_dir"):
        loads(PROGRAM_WITH_CUSTOM_INCLUDE, include_dir=value)
