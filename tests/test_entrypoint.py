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
Module containing unit tests for the loads() kwargs (issue #356).

"""

import pytest

from pyqasm.entrypoint import load, loads

QASM = """
OPENQASM 3.0;
include "stdgates.inc";
qubit[2] q;
h q[0];
"""


@pytest.mark.parametrize(
    "kwarg, attr, value",
    [
        ("device_qubits", "_device_qubits", 5),
        ("device_cycle_time", "_device_cycle_time", 1e-9),
        ("compiler_angle_type_size", "_compiler_angle_type_size", 32),
        ("extern_functions", "_extern_functions", {"f": (["int"], "int")}),
        ("frame_in_def_cal", "_frame_in_def_cal", False),
        ("frame_limit_per_port", "_frame_limit_per_port", 2),
        ("play_in_cal_block", "_play_in_cal", False),
    ],
)
def test_loads_kwargs_are_stored(kwarg, attr, value):
    """Every documented kwarg must be stored on the module, falsy values included."""
    module = loads(QASM, **{kwarg: value})
    assert getattr(module, attr) == value


def test_loads_kwarg_none_means_not_passed():
    """An explicit None leaves the attribute at its default."""
    assert loads(QASM, device_qubits=None)._device_qubits is None
    # defaults that are not None must survive an explicit None
    extern_functions = loads(QASM, extern_functions=None)._extern_functions
    assert isinstance(extern_functions, dict) and not extern_functions
    assert loads(QASM, frame_in_def_cal=None)._frame_in_def_cal is True


def test_loads_empty_extern_functions_is_stored():
    """A falsy dict is a caller value, not an omission."""
    extern_functions = loads(QASM, extern_functions={})._extern_functions
    assert isinstance(extern_functions, dict) and not extern_functions


@pytest.mark.parametrize(
    "kwarg, value",
    [
        ("device_qubits", 0),
        ("device_qubits", -5),
        ("device_cycle_time", 0.0),
        ("compiler_angle_type_size", 0),
        ("frame_limit_per_port", -1),
    ],
)
def test_loads_rejects_non_positive_values(kwarg, value):
    """Zero or negative values are rejected at the call site instead of surfacing
    later as a confusing validation message (issue #356)."""
    with pytest.raises(ValueError, match=kwarg):
        loads(QASM, **{kwarg: value})


@pytest.mark.parametrize(
    "kwarg, value",
    [
        ("device_qubits", "5"),
        ("device_qubits", []),
        ("device_qubits", complex(1)),
        ("device_cycle_time", {}),
        ("frame_limit_per_port", "2"),
    ],
)
def test_loads_rejects_non_numeric_values(kwarg, value):
    """A non-numeric value must name the kwarg rather than surfacing as a bare
    comparison error from inside the validator (issue #356)."""
    with pytest.raises(TypeError, match=kwarg):
        loads(QASM, **{kwarg: value})


@pytest.mark.parametrize("kwarg", ["device_qubits", "compiler_angle_type_size"])
@pytest.mark.parametrize("value", [True, False])
def test_loads_rejects_bool_for_numeric_kwargs(kwarg, value):
    """bool is a subclass of int, so True would otherwise pass positivity and be
    stored as a count of 1, while False would report 'must be positive'."""
    with pytest.raises(TypeError, match=kwarg):
        loads(QASM, **{kwarg: value})


def test_loads_rejects_unknown_kwargs():
    """A typo in a kwarg name must fail where it is made, not silently do nothing."""
    with pytest.raises(TypeError, match="devise_qubits"):
        loads(QASM, devise_qubits=5)


def test_load_errors_name_load_not_loads(tmp_path):
    """load() forwards **kwargs, so its errors must name the function the caller
    actually invoked."""
    path = tmp_path / "prog.qasm"
    path.write_text(QASM, encoding="utf-8")

    with pytest.raises(TypeError, match=r"load\(\) got unexpected keyword argument"):
        load(str(path), devise_qubits=5)
    with pytest.raises(ValueError, match=r"load\(\) kwarg 'device_qubits'"):
        load(str(path), device_qubits=0)
