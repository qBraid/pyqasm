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
        "Invalid base size 32.1 for variable 'x'",
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
        "Invalid base size for constant 'x'",
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
        f"Invalid initialization value for variable 'x'",
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
