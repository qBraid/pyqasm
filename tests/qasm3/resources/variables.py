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
Module defining QASM3 incorrect variable tests.

"""
DECLARATION_TESTS = {
    "keyword_redeclaration": (
        """
        OPENQASM 3.0;
        include "stddgates.inc";
        int pi;
        """,
        "Can not declare variable with keyword name pi",
        4,  # Line number
        8,  # Column number
        "int pi;",  # Complete line
    ),
    "const_keyword_redeclaration": (
        """
        OPENQASM 3.0;
        include "stdgates.inc";
        const int pi = 3;
        """,
        "Can not declare variable with keyword name pi",
        4,
        8,
        "const int pi = 3;",
    ),
    "variable_redeclaration": (
        """
        OPENQASM 3.0;
        include "stdgates.inc";
        int x;
        float y = 3.4;
        uint x;
        """,
        "Re-declaration of variable 'x'",
        6,
        8,
        "uint x;",
    ),
    "variable_redeclaration_with_qubits_1": (
        """
        OPENQASM 3.0;
        include "stdgates.inc";
        int x;
        qubit x;
        """,
        "Re-declaration of quantum register with name 'x'",
        5,
        8,
        "qubit[1] x;",
    ),
    "variable_redeclaration_with_qubits_2": (
        """
        OPENQASM 3.0;
        include "stdgates.inc";
        qubit x;
        int x;
        """,
        "Re-declaration of variable 'x'",
        5,
        8,
        "int x;",
    ),
    "const_variable_redeclaration": (
        """
        OPENQASM 3.0;
        include "stdgates.inc";
        const int x = 3;
        const float x = 3.4;
        """,
        "Re-declaration of variable 'x'",
        5,
        8,
        "const float x = 3.4;",
    ),
    "invalid_int_size": (
        """
        OPENQASM 3.0;
        include "stdgates.inc";
        int[32.1] x;
        """,
        "Invalid base size '32.1' for variable 'x'",
        4,
        8,
        "int[32.1] x;",
    ),
    "invalid_const_int_size": (
        """
        OPENQASM 3.0;
        include "stdgates.inc";
        const int[32.1] x = 3;
        """,
        "Invalid base size '32.1' for constant 'x'",
        4,
        8,
        "const int[32.1] x = 3;",
    ),
    "const_declaration_with_non_const": (
        """
        OPENQASM 3.0;
        include "stdgates.inc";
        int[32] x = 5;
        const int[32] y = x + 5;
        """,
        "Invalid initialization value for constant 'y'",
        5,
        8,
        "const int[32] y = x + 5;",
    ),
    "const_declaration_with_non_const_size": (
        """
        OPENQASM 3.0;
        include "stdgates.inc";
        int[32] x = 5;
        const int[x] y = 5;
        """,
        "Invalid base size for constant 'y'",
        5,
        8,
        "const int[x] y = 5;",
    ),
    "invalid_float_size": (
        """
        OPENQASM 3.0;
        include "stdgates.inc";

        float[23] x;
        """,
        "Invalid base size 23 for float variable 'x'",
        5,
        8,
        "float[23] x;",
    ),
    "unsupported_types": (
        """
        OPENQASM 3.0;
        include "stdgates.inc";

        angle x = 3.4;
        """,
        "Invalid initialization value for variable 'x'",
        5,
        8,
        "angle x = 3.4;",
    ),
    "imaginary_variable": (
        """
        OPENQASM 3.0;
        include "stdgates.inc";

        int x = 1 + 3im;
        """,
        "Invalid initialization value for variable 'x'",
        5,
        8,
        "int x = 1 + 3.0im;",
    ),
    "invalid_array_dimensions": (
        """
        OPENQASM 3.0;
        include "stdgates.inc";

        array[int[32], 1, 2.1] x;
        """,
        "Invalid dimension size 2.1 in array declaration for 'x'",
        5,
        8,
        "array[int[32], 1, 2.1] x;",
    ),
    "extra_array_dimensions": (
        """
        OPENQASM 3.0;
        include "stdgates.inc";

        array[int[32], 1, 2, 3, 4, 5, 6, 7, 8] x;
        """,
        "Invalid dimensions 8 for array declaration for 'x'. Max allowed dimensions is 7",
        5,
        8,
        "array[int[32], 1, 2, 3, 4, 5, 6, 7, 8] x;",
    ),
    "dimension_mismatch_1": (
        """
        OPENQASM 3.0;
        include "stdgates.inc";

        array[int[32], 1, 2] x = {1,2,3};
        """,
        "Invalid initialization value for array 'x'",
        5,
        8,
        "array[int[32], 1, 2] x = {1, 2, 3};",
    ),
    "dimension_mismatch_2": (
        """
        OPENQASM 3.0;
        include "stdgates.inc";

        array[int[32], 3, 1, 2] x = {1,2,3};
        """,
        "Invalid initialization value for array 'x'",
        5,
        8,
        "array[int[32], 3, 1, 2] x = {1, 2, 3};",
    ),
    "invalid_bit_type_array_1": (
        """
        OPENQASM 3.0;
        include "stdgates.inc";

        array[bit, 3] x;
        """,
        "Can not declare array x with type 'bit'",
        5,
        8,
        "array[bit, 3] x;",
    ),
    "invalid_bit_type_array_2": (
        """
        OPENQASM 3.0;
        include "stdgates.inc";

        array[bit[32], 3] x;
        """,
        "Can not declare array x with type 'bit'",
        5,
        8,
        "array[bit[32], 3] x;",
    ),
}
ASSIGNMENT_TESTS = {
    "undefined_variable_assignment": (
        """
        OPENQASM 3.0;
        include "stdgates.inc";
        
        float k;

        x = 3; 

        """,
        "Undefined variable x in assignment",
        7,  # Line number
        8,  # Column number
        "x = 3;",  # Complete line
    ),
    "assignment_to_constant": (
        """
        OPENQASM 3.0;
        include "stdgates.inc";

        const int x = 3;
        x = 4;
        """,
        "Assignment to constant variable x not allowed",
        6,
        8,
        "x = 4;",
    ),
    "invalid_assignment_type": (
        """
        OPENQASM 3.0;
        include "stdgates.inc";

        bit x = 3.3;
        """,
        "Invalid initialization value for variable 'x'",
        5,
        8,
        "bit x = 3.3;",
    ),
    "int_out_of_range": (
        """
        OPENQASM 3.0;
        include "stdgates.inc";

        int[32] x = 1<<64;
        """,
        "Invalid initialization value for variable 'x'",
        5,
        8,
        "int[32] x = 1 << 64;",
    ),
    "float32_out_of_range": (
        """
        OPENQASM 3.0;
        include "stdgates.inc";

        float[32] x = 123456789123456789123456789123456789123456789.1;
        """,
        "Invalid initialization value for variable 'x'",
        5,
        8,
        "float[32] x = 1.2345678912345679e+44;",
    ),
    "indexing_non_array": (
        """
        OPENQASM 3.0;
        include "stdgates.inc";

        int x = 3;
        x[0] = 4;
        """,
        "Invalid index for variable 'x'",
        6,
        8,
        "x[0] = 4;",
    ),
    "incorrect_num_dims": (
        """
        OPENQASM 3.0;
        include "stdgates.inc";

        array[int[32], 1, 2, 3] x;
        x[0] = 3;
        """,
        "Invalid index for variable 'x'",
        6,
        8,
        "x[0] = 3;",
    ),
    "non_nnint_index": (
        """
        OPENQASM 3.0;
        include "stdgates.inc";

        array[int[32], 3] x;
        x[0.1] = 3;
        """,
        "Invalid index for variable 'x'",
        6,
        8,
        "x[0.1] = 3;",
    ),
    "index_out_of_range": (
        """
        OPENQASM 3.0;
        include "stdgates.inc";

        array[int[32], 3] x;
        x[3] = 3;
        """,
        "Invalid index for variable 'x'",
        6,
        8,
        "x[3] = 3;",
    ),
}

CASTING_TESTS = {
    "General_test": (
        """
        OPENQASM 3.0;
        include "stdgates.inc";
        const float[64] f1 = 2.5;
        uint[8] runtime_u = 7;
        int[32] i2 = 2 * int[32](float[64](int[16](f1)));
        const int[8] i1 = int[8](f1); 
        const uint u1 = 2 * uint(f1);
        int ccf1 = float(runtime_u) * int(f1);
        uint ul1 = uint(float[64](int[16](f1))) * 2;
        const int un = -int(u1);
        """
    ),
    "Bool_test": (
        """
        OPENQASM 3.0;
        include "stdgates.inc";
        
        bool b_false = false;
        bool b_true  = true;
        
        int i1 = int(b_false);
        uint[16] u1 = uint[16](b_true);
        float[32] f0 = float[32](b_false);
        
        bit  b;
        b = b_true;
        
        bit[4] bits_from_true  = bit[4](b_true);
        
        bool b_nested = bool(float[32](uint[8](int[8](bit[8](bool(true))))));
        """
    ),
    "Int_test": (
        """
        OPENQASM 3.0;
        include "stdgates.inc";
        
        int[4] x = -3;
        bool b = bool(x);
        uint[8] ux = uint[8](x);
        float[32] f = float[32](x);
        bit[4] bits = bit[4](x);
        """
    ),
    "Unsigned_Int_test": (
        """
        OPENQASM 3.0;
        include "stdgates.inc";
        
        uint[8] x = 3;
        bool b = bool(x);
        int[8] i = int[8](x);
        float[32] f = float[32](x);
        bit[4] bits = bit[4](x);
        """
    ),
    "Float_test": (
        """
        OPENQASM 3.0;
        include "stdgates.inc";

        const float[64] two_pi = 6.283185307179586;
        float[64] f = two_pi * (127. / 512.);
        bool b = bool(f);
        int i = int(f);
        uint u = uint(f);
        // angle[8] a = angle[8](f);
        """
    ),
    "Bit_test": (
        """
        OPENQASM 3.0;
        include "stdgates.inc";
        
        int v = 15;
        bit[4] x = v;
        bool b = bool(x);
        int[32] i = int[32](x);
        uint[32] u = uint[32](x);
        // angle[4] a = angle[4](x);
        """
    ),
}

FAIL_CASTING_TESTS = {
    "Float_to_Bit_test": (
        """
        OPENQASM 3.0;
        include "stdgates.inc";
        const float[64] f1 = 2.5;
        const bit[2] b1 = bit[2](f1);
        """,
        "Cannot cast <class 'float'> to <class 'openqasm3.ast.BitType'>. Invalid assignment "
        "of type <class 'float'> to variable f1 of type <class 'openqasm3.ast.BitType'>",
        5,
        8,
        "const bit[2] b1 = bit[2](f1);",
    ),
    "Const_to_non-Const_test": (
        """
        OPENQASM 3.0;
        include "stdgates.inc";
        uint[8] runtime_u = 7;
        const int[16] i2 = int[16](runtime_u);
        """,
        "Expected variable 'runtime_u' to be constant in given expression",
        5,
        35,
        "const int[16] i2 = int[16](runtime_u);",
    ),
    "Declaration_vs_Cast": (
        """
        OPENQASM 3.0;
        include "stdgates.inc";
        int v = 15;
        int[32] i = uint[32](v);
        """,
        "Declaration type: 'Int[32]' and Cast type: 'Uint[32]', should be same for 'i'",
        5,
        8,
        "int[32] i = uint[32](v);",
    ),
    "Incorrect_base_size_for_cast_variable": (
        """
        OPENQASM 3.0;
        include "stdgates.inc";
        const float[64] f1 = 2.5;
        const int[32] i1 = int[32.5](f1);
        """,
        "Invalid base size '32.5' for variable 'f1'",
        5,
        27,
        "int[32.5](f1);",
    ),
    "Incorrect_base_size_for_direct_value_in_cast": (
        """
        OPENQASM 3.0;
        include "stdgates.inc";
        const uint[32] iu = uint[12.2](24);
        """,
        "Invalid base size '12.2' for value '24'",
        4,
        28,
        "uint[12.2](24);",
    ),
}
