# Copyright 2026 qBraid
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

"""Tests for the standard controlled-S gates."""

import numpy as np
import pytest

from pyqasm.entrypoint import dumps, loads
from tests.utils import assert_unitary_equal, unitary_from_unrolled_ast


@pytest.mark.parametrize("gate,phase", [("cs", 1j), ("csdg", -1j)])
def test_controlled_s_gates_decompose(gate: str, phase: complex):
    """Controlled S and its inverse retain their phase after unrolling.

    Args:
        gate (str): The standard controlled-S gate name.
        phase (complex): The expected phase on the two-qubit |11> state.
    """
    module = loads(
        f'OPENQASM 3.0; include "stdgates.inc"; '
        f"qubit[2] q; bit[2] c; {gate} q[0], q[1]; c = measure q;"
    )
    module.unroll()

    loads(dumps(module)).validate()
    assert_unitary_equal(
        unitary_from_unrolled_ast(module.unrolled_ast, 2),
        np.diag([1, 1, 1, phase]),
    )
