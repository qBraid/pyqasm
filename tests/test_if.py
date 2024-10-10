# Copyright (C) 2024 qBraid
#
# This file is part of the pyqasm
#
# The pyqasm is free software released under the GNU General Public License v3
# or later. You can redistribute and/or modify it under the terms of the GPL v3.
# See the LICENSE file in the project root or <https://www.gnu.org/licenses/gpl-3.0.html>.
#
# THERE IS NO WARRANTY for the pyqasm, as per Section 15 of the GPL v3.
"""
Module containing unit tests for the if statements.

"""

# import os
# from pathlib import Path

# import pyqir
# import pytest
# from qbraid_qir.qasm3 import Qasm3ConversionError, qasm3_to_qir

# from tests.qir_utils import check_attributes, get_entry_point_body

# RESOURCES_DIR = os.path.join(
#     os.path.dirname(__file__).removesuffix("converter"), "fixtures/resources"
# )


# def resources_file(filename: str) -> str:
#     return str(os.path.join(RESOURCES_DIR, f"{filename}"))


# def compare_reference_ir(generated_bitcode: bytes, file_path: str) -> None:
#     module = pyqir.Module.from_bitcode(pyqir.Context(), generated_bitcode, f"{file_path}")
#     ir = str(module)
#     pyqir_ir_body = get_entry_point_body(ir.splitlines())

#     expected = Path(file_path).read_text(encoding="utf-8")
#     expected_ir_body = get_entry_point_body(expected.splitlines())
#     assert pyqir_ir_body == expected_ir_body


# def test_simple_if():
#     qasm = """
#     OPENQASM 3;
#     include "stdgates.inc";
#     qubit[4] q;
#     bit[4] c;
#     h q;
#     measure q -> c;
#     if(c[0]){
#         x q[0];
#         cx q[0], q[1];
#     }

#     if(c[1] == 1){
#         cx q[1], q[2];
#     }

#     if(!c[2]){
#         h q[2];
#     }
#     """
#     result = qasm3_to_qir(qasm)
#     generated_qir = str(result).splitlines()

#     check_attributes(generated_qir, 4, 4)
#     simple_file = resources_file("simple_if.ll")
#     compare_reference_ir(result.bitcode, simple_file)


# def test_complex_if():
#     qasm = """
#     OPENQASM 3;
#     include "stdgates.inc";
#     gate custom a, b{
#         cx a, b;
#         h a;
#     }
#     qubit[4] q;
#     bit[4] c;
#     bit[4] c0;

#     h q;
#     measure q -> c0;
#     if(c0[0]){
#         x q[0];
#         cx q[0], q[1];
#         if (c0[1]){
#             cx q[1], q[2];
#         }
#     }
#     if (c[0]){
#         custom q[2], q[3];
#     }
#     """
#     result = qasm3_to_qir(qasm)
#     generated_qir = str(result).splitlines()

#     check_attributes(generated_qir, 4, 8)
#     complex_if = resources_file("complex_if.ll")
#     compare_reference_ir(result.bitcode, complex_if)


# def test_incorrect_if():
#     with pytest.raises(Qasm3ConversionError, match=r"Unsupported expression type .*"):
#         _ = qasm3_to_qir(
#             """
#            OPENQASM 3;
#            include "stdgates.inc";
#            qubit[2] q;
#            bit[2] c;

#            h q;
#            measure q->c;

#            if(c == 4){
#                 cx q;
#            }
#            """
#         )

#     with pytest.raises(Qasm3ConversionError, match=r"Missing if block"):
#         _ = qasm3_to_qir(
#             """
#             OPENQASM 3;
#            include "stdgates.inc";
#            qubit[2] q;
#            bit[2] c;

#            h q;
#            measure q->c;

#            if(c[0]){
#            }
#            """
#         )

#     with pytest.raises(Qasm3ConversionError, match=r"Missing register declaration for c2 .*"):
#         _ = qasm3_to_qir(
#             """
#             OPENQASM 3;
#            include "stdgates.inc";
#            qubit[2] q;
#            bit[2] c;

#            h q;
#            measure q->c;

#            if(c2[0]){
#             cx q;
#            }
#            """
#         )

#     with pytest.raises(Qasm3ConversionError, match=r"Unsupported unary expression .*"):
#         _ = qasm3_to_qir(
#             """
#             OPENQASM 3;
#            include "stdgates.inc";
#            qubit[2] q;
#            bit[2] c;

#            h q;
#            measure q->c;

#            if(~c[0]){
#             cx q;
#            }
#            """
#         )
#     with pytest.raises(Qasm3ConversionError, match=r"Unsupported binary expression .*"):
#         _ = qasm3_to_qir(
#             """
#             OPENQASM 3;
#            include "stdgates.inc";
#            qubit[2] q;
#            bit[2] c;

#            h q;
#            measure q->c;

#            if(c[0] >= 1){
#             cx q;
#            }
#            """
#         )
#     with pytest.raises(
#         Qasm3ConversionError,
#         match=r"Unsupported expression type .* in if condition. Can only be a simple comparison",
#     ):
#         _ = qasm3_to_qir(
#             """
#             OPENQASM 3;
#            include "stdgates.inc";
#            qubit[2] q;
#            bit[2] c;

#            h q;
#            measure q->c;

#            if(c){
#             cx q;
#            }
#            """
#         )
#     with pytest.raises(
#         Qasm3ConversionError,
#         match=r"RangeDefinition not supported in branching condition",
#     ):
#         _ = qasm3_to_qir(
#             """
#             OPENQASM 3;
#            include "stdgates.inc";
#            qubit[2] q;
#            bit[2] c;

#            h q;
#            measure q->c;

#            if(c[0:1]){
#             cx q;
#            }
#            """
#         )

#     with pytest.raises(
#         Qasm3ConversionError,
#         match=r"DiscreteSet not supported in branching condition",
#     ):
#         _ = qasm3_to_qir(
#             """
#             OPENQASM 3;
#            include "stdgates.inc";
#            qubit[2] q;
#            bit[2] c;

#            h q;
#            measure q->c;

#            if(c[{0,1}]){
#             cx q;
#            }
#            """
#         )
