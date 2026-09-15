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

"""Tests for terminating an OpenQASM 3 program with ``end``."""

import pytest

from pyqasm.entrypoint import dumps, loads
from tests.utils import check_unrolled_qasm


def test_end_stops_global_unrolling_and_bookkeeping():
    """Statements after a global ``end`` are unreachable."""
    module = loads("""
        OPENQASM 3.0;
        include "stdgates.inc";
        qubit q;
        h q;
        end;
        x q;
        qubit[2] unreachable;
        """)

    module.validate()
    module.unroll()

    expected = """
        OPENQASM 3.0;
        include "stdgates.inc";
        qubit[1] q;
        h q[0];
        end;
        """
    check_unrolled_qasm(dumps(module), expected)
    assert module.num_qubits == 1
    assert module.depth() == 1

    round_tripped = loads(dumps(module))
    round_tripped.unroll()
    check_unrolled_qasm(dumps(round_tripped), expected)


@pytest.mark.parametrize(
    "control_flow",
    [
        "if (true) { h q; end; x q; }",
        "if (false) { x q; } else { h q; end; x q; }",
        "for int i in [0:2] { h q; end; x q; }",
        "int i = 1; switch (i) { case 1 { h q; end; x q; } default { x q; } }",
    ],
)
def test_end_propagates_from_static_control_flow(control_flow):
    """A reachable ``end`` in static control flow terminates the program."""
    module = loads(f"""
        OPENQASM 3.0;
        include "stdgates.inc";
        qubit q;
        {control_flow}
        x q;
        """)

    module.unroll()
    output = dumps(module)

    assert output.count("h q[0];") == 1
    assert output.count("end;") == 1
    assert "x q[0];" not in output
    assert output.rstrip().endswith("end;")


def test_end_stops_while_loop_and_program():
    """A terminating while-loop body is not expanded again."""
    module = loads("""
        OPENQASM 3.0;
        include "stdgates.inc";
        qubit q;
        int i = 0;
        while (i < 2) {
            h q;
            end;
            i += 1;
        }
        x q;
        """)

    module.unroll(max_loop_iters=2)
    output = dumps(module)

    assert output.count("h q[0];") == 1
    assert output.count("end;") == 1
    assert "x q[0];" not in output


def test_end_propagates_from_inlined_subroutine():
    """An ``end`` reached in an inlined subroutine terminates its caller."""
    module = loads("""
        OPENQASM 3.0;
        include "stdgates.inc";
        def stop(qubit q) {
            h q;
            end;
            x q;
        }
        qubit q;
        stop(q);
        x q;
        """)

    module.unroll()
    output = dumps(module)

    assert output.count("h q[0];") == 1
    assert output.count("end;") == 1
    assert "x q[0];" not in output


def test_end_propagates_from_box():
    """A box preserves its ``end`` and terminates the surrounding block."""
    module = loads("""
        OPENQASM 3.0;
        include "stdgates.inc";
        qubit q;
        box {
            h q;
            end;
            x q;
        }
        x q;
        """)

    module.unroll()

    expected = """
        OPENQASM 3.0;
        include "stdgates.inc";
        qubit[1] q;
        box {
          h q[0];
          end;
        }
        """
    check_unrolled_qasm(dumps(module), expected)


def test_runtime_conditional_end_remains_conditional():
    """A runtime-dependent ``end`` does not truncate the surrounding block."""
    module = loads("""
        OPENQASM 3.0;
        include "stdgates.inc";
        qubit q;
        bit[1] c;
        if (c[0]) {
            end;
            x q;
        }
        h q;
        """)

    module.unroll()

    expected = """
        OPENQASM 3.0;
        include "stdgates.inc";
        qubit[1] q;
        bit[1] c;
        if (c[0] == true) {
          end;
        }
        h q[0];
        """
    check_unrolled_qasm(dumps(module), expected)


def test_end_in_both_runtime_branches_terminates_program():
    """Later statements are unreachable when every runtime branch terminates."""
    module = loads("""
        OPENQASM 3.0;
        include "stdgates.inc";
        bit[1] c;
        qubit q;
        if (c[0]) {
            h q;
            end;
        } else {
            z q;
            end;
        }
        x q;
        qubit unreachable;
        """)

    module.unroll()
    output = dumps(module)

    assert "h q[0];" in output
    assert "z q[0];" in output
    assert output.count("end;") == 2
    assert "x q[0];" not in output
    assert "unreachable" not in output
    assert module.num_qubits == 1
