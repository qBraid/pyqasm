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
Module containing unit tests for OpenQASM 2 `opaque` declarations (issue #370).

An opaque gate is a hardware primitive: it is declared with a name and an arity and has
no decomposition. pyqasm parses the declaration and emits a call to it as written.

"""

import pytest

from pyqasm.elements import BasisSet
from pyqasm.entrypoint import dumps, load, loads
from pyqasm.exceptions import RebaseError, ValidationError
from tests.utils import check_unrolled_qasm

# The six opaque primitives Quantinuum's hqslib1.inc opens with, plus the two gates it
# defines in terms of them. Written out here rather than vendored, so the test does not
# depend on pytket being installed.
HQSLIB1_LIKE_INC = """
opaque Rz(lam) q;
opaque U1q(theta, phi) q;
opaque ZZ() q1,q2;
opaque RZZ(theta) q1,q2;
opaque Rxxyyzz(alpha, beta, gamma) q1,q2;
opaque Rxxyyzz_zphase(alpha, beta, gamma, z0, z1) q1,q2;

gate U(a,b,c) q { U1q(a, b) q; Rz(c) q; }
gate CX c,t { ZZ c,t; }
"""

OPAQUE_PROGRAM = """
OPENQASM 2.0;
include "qelib1.inc";
opaque ZZ() q1,q2;
opaque Rz(lam) q;
qreg q[3];
"""


def test_opaque_declaration_parses():
    """The reported failure was at parse time: every program carrying an opaque
    declaration raised `Failed to parse OpenQASM string` (issue #370)."""
    qasm_str = """
    OPENQASM 2.0;
    include "qelib1.inc";
    qreg q[2];
    opaque custom_gate(a,b,c) p,q,r;
    """
    module = loads(qasm_str)
    module.validate()
    assert module._opaque_gates == {"custom_gate"}


@pytest.mark.parametrize(
    "declaration, name",
    [
        ("opaque Rz(lam) q;", "Rz"),
        ("opaque ZZ() q1,q2;", "ZZ"),
        ("opaque zz q1,q2;", "zz"),
        ("opaque Rxxyyzz(alpha, beta, gamma) q1,q2;", "Rxxyyzz"),
    ],
)
def test_opaque_declaration_forms(declaration, name):
    """All three qasm2 spellings parse: parameters, empty parentheses, and no
    parentheses at all."""
    module = loads(f'OPENQASM 2.0;\ninclude "qelib1.inc";\n{declaration}\nqreg q[2];\n')
    module.validate()
    assert module._opaque_gates == {name}


@pytest.mark.parametrize(
    "commented",
    [
        "// opaque hidden q;",
        "  //opaque hidden q;",
        "/* opaque hidden q; */",
        "/*\nopaque hidden q;\n*/",
    ],
)
def test_commented_out_opaque_is_not_declared(commented):
    """The rewrite runs on source text, so it must see code only. A declaration inside a
    `//` or `/* */` comment is neither rewritten nor recorded -- recording it would make
    a real gate of that name be emitted as written instead of unrolled."""
    module = loads(f'OPENQASM 2.0;\ninclude "qelib1.inc";\n{commented}\nqreg q[1];\nh q[0];\n')
    module.unroll()
    assert not module._opaque_gates
    assert "h q[0];" in dumps(module)


@pytest.mark.parametrize("path", ["dir//lib.inc", "dir/*x*/lib.inc"])
def test_comment_markers_inside_a_string_are_not_blanked(path):
    """Blanking runs over source text, so a `//` or `/*` inside an include path must be
    recognised as a string and left alone -- blanking it would truncate the statement."""
    module = loads(f'OPENQASM 2.0;\ninclude "{path}";\nqreg q[1];\nh q[0];\n')
    module.unroll()
    assert f'include "{path}";' in dumps(module)


def test_opaque_declaration_with_a_trailing_comment():
    """Blanking comments must not disturb the declaration they sit beside."""
    module = loads(
        'OPENQASM 2.0;\ninclude "qelib1.inc";\n'
        "opaque ZZ() a,b; // the native two-qubit gate\nqreg q[2];\nZZ q[0],q[1];\n"
    )
    module.unroll()
    assert module._opaque_gates == {"ZZ"}
    assert "ZZ q[0], q[1];" in dumps(module)


def test_opaque_gate_is_emitted_as_written():
    """An opaque gate has no decomposition, so unrolling emits the call unchanged."""
    expected_qasm_str = """
    OPENQASM 2.0;
    include "qelib1.inc";
    qreg q[3];
    ZZ q[0], q[1];
    Rz(0.5) q[2];
    """
    module = loads(OPAQUE_PROGRAM + "ZZ q[0],q[1];\nRz(0.5) q[2];\n")
    module.unroll()
    check_unrolled_qasm(dumps(module), expected_qasm_str)


def test_opaque_gate_arity_is_validated():
    """The declared arity is the whole of what an opaque declaration carries, so a call
    that does not match it must be rejected."""
    module = loads(OPAQUE_PROGRAM + "ZZ q[0];\n")
    with pytest.raises(ValidationError, match="Qubit count mismatch for gate 'ZZ'"):
        module.validate()


@pytest.mark.parametrize("external_gates", [None, [], ["h"], ["ZZ"]])
def test_opaque_gate_is_never_flushed_by_unroll(external_gates):
    """`unroll()` resets `external_gates` on every call, so opaque gates are tracked
    separately: an opaque gate has no decomposition to fall back on, and must survive
    an unroll that names other gates, or none."""
    module = loads(OPAQUE_PROGRAM + "ZZ q[0],q[1];\n")
    module.unroll(external_gates=external_gates)
    assert "ZZ q[0], q[1];" in dumps(module)


def test_opaque_gate_counts_as_one_towards_depth():
    """One emitted statement is one layer, the same contract an external gate has."""
    module = loads(OPAQUE_PROGRAM + "h q[0];\nZZ q[0],q[1];\n")
    module.unroll()
    assert module.depth() == 2


def test_opaque_gate_inside_a_custom_gate_body():
    """A custom gate that calls an opaque primitive unrolls down to the primitive and
    stops there, rather than failing on an undeclared operation."""
    expected_qasm_str = """
    OPENQASM 2.0;
    include "qelib1.inc";
    qreg q[3];
    ZZ q[0], q[1];
    Rz(0.5) q[0];
    """
    module = loads(OPAQUE_PROGRAM + "gate wrap a,b { ZZ a,b; Rz(0.5) a; }\nwrap q[0],q[1];\n")
    module.unroll()
    check_unrolled_qasm(dumps(module), expected_qasm_str)


@pytest.mark.parametrize(
    "transform, expected",
    [
        ("remove_idle_qubits", "ZZ q[0], q[1];"),
        ("reverse_qubit_order", "ZZ q[2], q[0];"),
    ],
)
def test_opaque_gate_survives_qubit_transformations(transform, expected):
    """An opaque call is an ordinary gate statement, so the passes that renumber qubits
    must rewrite its operands like any other."""
    module = loads(OPAQUE_PROGRAM + "ZZ q[0],q[2];\n")
    module.unroll()
    getattr(module, transform)()
    assert expected in dumps(module)


def test_opaque_gate_survives_qubit_consolidation():
    """Consolidation rewrites the operands onto the internal register."""
    module = loads(OPAQUE_PROGRAM + "ZZ q[0],q[1];\n")
    module.unroll(consolidate_qubits=True)
    assert "ZZ __PYQASM_QUBITS__[0], __PYQASM_QUBITS__[1];" in dumps(module)


def test_opaque_is_not_qasm3_syntax():
    """`opaque` was removed in OpenQASM 3, so a qasm3 program carrying one must keep
    failing to parse. The rewrite is gated on the OPENQASM 2 header."""
    qasm_str = """
    OPENQASM 3.0;
    include "stdgates.inc";
    opaque foo q;
    qubit[1] q;
    """
    with pytest.raises(ValidationError, match="Failed to parse OpenQASM string"):
        loads(qasm_str)


def test_quantinuum_style_program_loads_from_a_string(tmp_path):
    """The driver for the issue: a bell state compiled for H-series hardware, whose
    include file declares its primitives opaque. It could not be loaded at all. The
    program is a string, so `include_dir` locates the include (issue #368) -- both
    changes are needed to load a compiled program."""
    (tmp_path / "hqslib1.inc").write_text(HQSLIB1_LIKE_INC, encoding="utf-8")
    program = """
    OPENQASM 2.0;
    include "hqslib1.inc";

    qreg q[2];
    creg c[2];
    rz(1.0*pi) q[0];
    rz(3.5*pi) q[1];
    U1q(0.5*pi,0.5*pi) q[0];
    U1q(2.5*pi,0.0*pi) q[1];
    rz(0.5*pi) q[0];
    RZZ(0.5*pi) q[0],q[1];
    measure q[0] -> c[0];
    U1q(3.5*pi,0.5*pi) q[1];
    measure q[1] -> c[1];
    """
    module = loads(program, include_dir=str(tmp_path))
    module.unroll()

    assert module.num_qubits == 2
    assert module.num_clbits == 2
    assert module.has_measurements()
    unrolled = dumps(module)
    # the three opaque primitives the program calls survive as written
    assert "U1q(1.5707963267948966, 1.5707963267948966) q[0];" in unrolled
    assert "RZZ(1.5707963267948966) q[0], q[1];" in unrolled
    assert unrolled.count("measure") == 2


def test_load_resolves_opaque_declarations_from_a_file(tmp_path):
    """The rewrite runs after include inlining, so an opaque declaration inside an
    included file is reached by load() too."""
    (tmp_path / "hqslib1.inc").write_text(HQSLIB1_LIKE_INC, encoding="utf-8")
    path = tmp_path / "prog.qasm"
    path.write_text(
        'OPENQASM 2.0;\ninclude "hqslib1.inc";\nqreg q[2];\nRZZ(0.5) q[0],q[1];\n',
        encoding="utf-8",
    )

    module = load(str(path))
    module.unroll()
    assert "RZZ(0.5) q[0], q[1];" in dumps(module)


@pytest.mark.parametrize("basis_set", [BasisSet.ROTATIONAL_CX, BasisSet.CLIFFORD_T])
def test_rebase_reports_an_opaque_gate_by_name(basis_set):
    """An opaque primitive has no decomposition, so it cannot be rebased onto a standard
    basis set. It reaches the existing unsupported-gate path and is named there, rather
    than crashing inside the decomposer."""
    module = loads(OPAQUE_PROGRAM + "ZZ q[0],q[1];\n")
    module.unroll()
    with pytest.raises(RebaseError, match="Gate 'ZZ' is not supported"):
        module.rebase(basis_set)


@pytest.mark.parametrize("as_str", [True, False])
def test_to_qasm3_refuses_a_program_with_opaque_gates(as_str):
    """OpenQASM 3 removed `opaque` and has no equivalent. pyqasm carries an opaque gate
    as a body-less gate definition, and OpenQASM 3 reads a body-less gate as the
    identity, so converting would silently turn each hardware primitive into a no-op.
    Refusing is loud; the alternative is not."""
    module = loads(OPAQUE_PROGRAM + "ZZ q[0],q[1];\n")
    with pytest.raises(ValidationError, match="OpenQASM 3 removed 'opaque'"):
        module.to_qasm3(as_str=as_str)


def test_to_qasm3_still_works_without_opaque_gates():
    """The guard must be scoped to programs that actually declare an opaque gate."""
    module = loads('OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[2];\nh q[0];\n')
    assert "OPENQASM 3.0" in module.to_qasm3(as_str=True)


def test_opaque_declaration_is_dropped_from_the_unrolled_output():
    """Documented limitation: like an external gate's definition, the declaration is not
    re-emitted, so the unrolled output does not load back into pyqasm on its own. Pinned
    so the day it changes is a deliberate one."""
    module = loads(OPAQUE_PROGRAM + "ZZ q[0],q[1];\n")
    module.unroll()
    assert "opaque" not in dumps(module)
