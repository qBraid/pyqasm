# Copyright (C) 2024 qBraid
#
# This file is part of pyqasm
#
# Pyqasm is free software released under the GNU General Public License v3
# or later. You can redistribute and/or modify it under the terms of the GPL v3.
# See the LICENSE file in the project root or <https://www.gnu.org/licenses/gpl-3.0.html>.
#
# THERE IS NO WARRANTY for pyqasm, as per Section 15 of the GPL v3.

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
    ),
    "const_keyword_redeclaration": (
        """
        OPENQASM 3.0;
        include "stdgates.inc";
        const int pi = 3;
        """,
        "Can not declare variable with keyword name pi",
    ),
    "variable_redeclaration": (
        """
        OPENQASM 3.0;
        include "stdgates.inc";
        int x;
        float y = 3.4;
        uint x;
        """,
        "Re-declaration of variable x",
    ),
    "variable_redeclaration_with_qubits_1": (
        """
        OPENQASM 3.0;
        include "stdgates.inc";
        int x;
        qubit x;
        """,
        "Re-declaration of quantum register with name 'x'",
    ),
    "variable_redeclaration_with_qubits_2": (
        """
        OPENQASM 3.0;
        include "stdgates.inc";
        qubit x;
        int x;
        """,
        "Re-declaration of variable x",
    ),
    "const_variable_redeclaration": (
        """
        OPENQASM 3.0;
        include "stdgates.inc";
        const int x = 3;
        const float x = 3.4;
        """,
        "Re-declaration of variable x",
    ),
    "invalid_int_size": (
        """
        OPENQASM 3.0;
        include "stdgates.inc";
        int[32.1] x;
        """,
        "Invalid base size 32.1 for variable x",
    ),
    "invalid_const_int_size": (
        """
        OPENQASM 3.0;
        include "stdgates.inc";
        const int[32.1] x = 3;
        """,
        "Invalid base size 32.1 for variable x",
    ),
    "const_declaration_with_non_const": (
        """
        OPENQASM 3.0;
        include "stdgates.inc";
        int[32] x = 5;
        const int[32] y = x + 5;
        """,
        "Variable 'x' is not a constant in given expression",
    ),
    "const_declaration_with_non_const_size": (
        """
        OPENQASM 3.0;
        include "stdgates.inc";
        int[32] x = 5;
        const int[x] y = 5;
        """,
        "Variable 'x' is not a constant in given expression",
    ),
    "invalid_float_size": (
        """
        OPENQASM 3.0;
        include "stdgates.inc";

        float[23] x;
        """,
        "Invalid base size 23 for float variable x",
    ),
    "unsupported_types": (
        """
        OPENQASM 3.0;
        include "stdgates.inc";

        angle x = 3.4;
        """,
        "Invalid type <class 'openqasm3.ast.AngleType'> for variable x",
    ),
    "imaginary_variable": (
        """
        OPENQASM 3.0;
        include "stdgates.inc";

        int x = 1 + 3im;
        """,
        "Unsupported expression type <class 'openqasm3.ast.ImaginaryLiteral'>",
    ),
    "invalid_array_dimensions": (
        """
        OPENQASM 3.0;
        include "stdgates.inc";

        array[int[32], 1, 2.1] x;
        """,
        "Invalid dimension size 2.1 in array declaration for x",
    ),
    "extra_array_dimensions": (
        """
        OPENQASM 3.0;
        include "stdgates.inc";

        array[int[32], 1, 2, 3, 4, 5, 6, 7, 8] x;
        """,
        "Invalid dimensions 8 for array declaration for x. Max allowed dimensions is 7",
    ),
    "dimension_mismatch_1": (
        """
        OPENQASM 3.0;
        include "stdgates.inc";

        array[int[32], 1, 2] x = {1,2,3};
        """,
        "Invalid dimensions for array assignment to variable x. Expected 1 but got 3",
    ),
    "dimension_mismatch_2": (
        """
        OPENQASM 3.0;
        include "stdgates.inc";

        array[int[32], 3, 1, 2] x = {1,2,3};
        """,
        "Invalid dimensions for array assignment to variable x. Expected 3 but got 1",
    ),
    "invalid_bit_type_array_1": (
        """
        OPENQASM 3.0;
        include "stdgates.inc";

        array[bit, 3] x;
        """,
        "Can not declare array x with type 'bit'",
    ),
    "invalid_bit_type_array_2": (
        """
        OPENQASM 3.0;
        include "stdgates.inc";

        array[bit[32], 3] x;
        """,
        "Can not declare array x with type 'bit'",
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
    ),
    "assignment_to_constant": (
        """
        OPENQASM 3.0;
        include "stdgates.inc";

        const int x = 3;
        x = 4;
        """,
        "Assignment to constant variable x not allowed",
    ),
    "invalid_assignment_type": (
        """
        OPENQASM 3.0;
        include "stdgates.inc";

        bit x = 3.3;
        """,
        (
            "Cannot cast <class 'float'> to <class 'openqasm3.ast.BitType'>. "
            "Invalid assignment of type <class 'float'> to variable x of type "
            "<class 'openqasm3.ast.BitType'>"
        ),
    ),
    "int_out_of_range": (
        """
        OPENQASM 3.0;
        include "stdgates.inc";

        int[32] x = 1<<64;
        """,
        f"Value {2**64} out of limits for variable x with base size 32",
    ),
    "float32_out_of_range": (
        """
        OPENQASM 3.0;
        include "stdgates.inc";

        float[32] x = 123456789123456789123456789123456789123456789.1;
        """,
        "Value .* out of limits for variable x with base size 32",
    ),
    "indexing_non_array": (
        """
        OPENQASM 3.0;
        include "stdgates.inc";

        int x = 3;
        x[0] = 4;
        """,
        "Indexing error. Variable x is not an array",
    ),
    "incorrect_num_dims": (
        """
        OPENQASM 3.0;
        include "stdgates.inc";

        array[int[32], 1, 2, 3] x;
        x[0] = 3;
        """,
        "Invalid number of indices for variable x. Expected 3 but got 1",
    ),
    "non_nnint_index": (
        """
        OPENQASM 3.0;
        include "stdgates.inc";

        array[int[32], 3] x;
        x[0.1] = 3;
        """,
        "Invalid value 0.1 with type <class 'openqasm3.ast.FloatLiteral'> for "
        "required type <class 'openqasm3.ast.IntType'>",
    ),
    "index_out_of_range": (
        """
        OPENQASM 3.0;
        include "stdgates.inc";

        array[int[32], 3] x;
        x[3] = 3;
        """,
        "Index 3 out of bounds for dimension 0 of variable x",
    ),
}
