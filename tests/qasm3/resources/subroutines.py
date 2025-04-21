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
Module defining subroutine tests.

"""
SUBROUTINE_INCORRECT_TESTS = {
    "undeclared_call": (
        """
        OPENQASM 3;
        include "stdgates.inc";
        qubit q;
        my_function(1);
        """,
        "Undefined subroutine 'my_function' was called",
        5,  # Line number
        8,  # Column number
        "my_function(1)",  # Complete line
    ),
    "redefinition_raises_error": (
        """
        OPENQASM 3;
        include "stdgates.inc";

        def my_function(qubit q) -> int[32] {
            h q;
            return;
        }
        def my_function(qubit q) -> float[32] {
            x q;
            return;
        }
        qubit q;
        """,
        "Redefinition of subroutine 'my_function'",
        9,
        8,
        "def my_function(qubit q) -> float[32]",
    ),
    "redefinition_raises_error_2": (
        """
        OPENQASM 3;
        include "stdgates.inc";
        def my_function(qubit q) {
            int[32] q = 1;
            return;
        }
        qubit q;
        my_function(q);
        """,
        "Re-declaration of variable 'q'",
        5,
        12,
        "int[32] q = 1;",
    ),
    "incorrect_param_count_1": (
        """
        OPENQASM 3;
        include "stdgates.inc";

        def my_function(qubit q, qubit r) {
            h q;
            return;
        }
        qubit q;
        my_function(q);
        """,
        "Parameter count mismatch for subroutine 'my_function'. Expected 2 but got 1 in call",
        10,
        8,
        "my_function(q)",
    ),
    "incorrect_param_count_2": (
        """
        OPENQASM 3;
        include "stdgates.inc";

        def my_function(int[32] q) {
            h q;
            return;
        }
        qubit q;
        my_function(q, q);
        """,
        "Parameter count mismatch for subroutine 'my_function'. Expected 1 but got 2 in call",
        10,
        8,
        "my_function(q, q)",
    ),
    "return_value_mismatch": (
        """
        OPENQASM 3;
        include "stdgates.inc";

        def my_function(qubit q) {
            h q;
            int[32] a = 1;
            return a;
        }
        qubit q;
        my_function(q);
        """,
        "Return type mismatch for subroutine 'my_function'.",
        8,
        12,
        "return a;",
    ),
    "return_value_mismatch_2": (
        """
        OPENQASM 3;
        include "stdgates.inc";

        def my_function(qubit q) -> int[32] {
            h q;
            int[32] a = 1;
            return ;
        }
        qubit q;
        my_function(q);
        """,
        "Return type mismatch for subroutine 'my_function'.",
        8,
        12,
        "return;",
    ),
    "subroutine_keyword_naming": (
        """
        OPENQASM 3;
        include "stdgates.inc";

        def pi(qubit q) {
            h q;
            return;
        }
        qubit q;
        pi(q);
        """,
        "Subroutine name 'pi' is a reserved keyword",
        5,
        8,
        "def pi(qubit q) {",
    ),
    "qubit_size_arg_mismatch": (
        """
        OPENQASM 3;
        include "stdgates.inc";

        def my_function(qubit[3] q) {
            h q;
            return;
        }
        qubit[2] q;
        my_function(q);
        """,
        "Qubit register size mismatch for function 'my_function'.",
        10,
        8,
        "my_function(q)",
    ),
    "subroutine_var_name_conflict": (
        """
        OPENQASM 3;
        include "stdgates.inc";
        const int a = 4;
        def a(qubit q) {
            h q;
            return;
        }
        qubit q;
        a(q);
        """,
        r"Can not declare subroutine with name 'a' .*",
        5,
        8,
        "def a(qubit q) {",
    ),
    "undeclared_register_usage": (
        """
        OPENQASM 3;
        include "stdgates.inc";

        def my_function(qubit q) {
            h q;
            return;
        }
        qubit q;
        int b;
        my_function(b);
        """,
        "Expecting qubit argument for 'q'. Qubit register 'b' not found for function 'my_function'",
        11,
        8,
        "my_function(b)",
    ),
    "test_invalid_qubit_size": (
        """
        OPENQASM 3;
        include "stdgates.inc";

        def my_function(qubit[-3] q) {
            h q;
            return;
        }
        qubit[4] q;
        my_function(q);
        """,
        "Invalid qubit size '-3' for variable 'q' in function 'my_function'",
        5,
        24,
        "qubit[-3] q",
    ),
    "test_type_mismatch_for_function": (
        """
        OPENQASM 3;
        include "stdgates.inc";

        def my_function(int[32] a, qubit q) {
            h q;
            return;
        }
        qubit q;
        int[32] b = 4;
        my_function(q, b);
        """,
        "Expecting classical argument for 'a'. Qubit register 'q' found for function 'my_function'",
        11,
        8,
        "my_function(q, b)",
    ),
    "test_duplicate_qubit_args": (
        """
        OPENQASM 3;
        include "stdgates.inc";

        def my_function(qubit[3] p, qubit[1] q) {
            h q;
            return;
        }
        qubit[4] q;
        my_function(q[0:3], q[2]);
        """,
        r"Duplicate qubit argument for register 'q' in function call for 'my_function'",
        10,
        8,
        "my_function(q[0:3], q[2])",
    ),
    "undefined_variable_in_actual_arg_1": (
        """
        OPENQASM 3;
        include "stdgates.inc";

        def my_function(int [32] a) {
            h q;
            return;
        }
        qubit q;
        my_function(b);
        """,
        "Undefined variable 'b' used for function call 'my_function'",
        10,
        8,
        "my_function(b)",
    ),
    "undefined_array_arg_in_function_call": (
        """
        OPENQASM 3;
        include "stdgates.inc";

        def my_function(readonly array[int[32], 1, 2] a) {
            return;
        }
        my_function(b);
        """,
        "Undefined variable 'b' used for function call 'my_function'",
        8,
        8,
        "my_function(b)",
    ),
}

SUBROUTINE_INCORRECT_TESTS_WITH_ARRAYS = {
    "non_array_raises_error": (
        """
        OPENQASM 3.0;
        include "stdgates.inc";

        def my_function(qubit a, readonly array[int[8], 2, 2] my_arr) {
            return;
        }
        qubit q;
        int[8] arr;
        my_function(q, arr);
        """,
        r"Expecting type 'array\[int\[8\],...\]' for 'my_arr' in function 'my_function'."
        r" Variable 'arr' has type 'int\[8\]'",
        10,
        8,
        "my_function(q, arr)",
    ),
    "literal_raises_error": (
        """
        OPENQASM 3.0;
        include "stdgates.inc";

        def my_function(qubit a, readonly array[int[8], 2, 2] my_arr) {
            return;
        }
        qubit q;
        my_function(q, 5);
        """,
        r"Expecting type 'array\[int\[8\],...\]' for 'my_arr' in function 'my_function'."
        r" Literal '5' found in function call",
        9,
        8,
        "my_function(q, 5)",
    ),
    "type_mismatch_in_array": (
        """
        OPENQASM 3.0;
        include "stdgates.inc";

        def my_function(qubit a, readonly array[int[8], 2, 2] my_arr) {
            return;
        }
        qubit q;
        array[uint[32], 2, 2] arr;
        my_function(q, arr);
        """,
        r"Expecting type 'array\[int\[8\],...\]' for 'my_arr' in function 'my_function'."
        r" Variable 'arr' has type 'array\[uint\[32\], 2, 2\]'",
        10,
        8,
        "my_function(q, arr)",
    ),
    "dimension_count_mismatch_1": (
        """
        OPENQASM 3.0;
        include "stdgates.inc";

        def my_function(qubit a, readonly array[int[8], 2, 2] my_arr) {
            return;
        }
        qubit q;
        array[int[8], 2] arr;
        my_function(q, arr);
        """,
        r"Dimension mismatch. Expected 2 dimensions but variable 'arr'"
        r" has 1 for 'my_arr' in function 'my_function'",
        10,
        8,
        "my_function(q, arr)",
    ),
    "dimension_count_mismatch_2": (
        """
        OPENQASM 3.0;
        include "stdgates.inc";

        def my_function(qubit a, readonly array[int[8], #dim = 4] my_arr) {
            return;
        }
        qubit q;
        array[int[8], 2, 2] arr;
        my_function(q, arr);
        """,
        r"Dimension mismatch. Expected 4 dimensions but variable 'arr'"
        r" has 2 for 'my_arr' in function 'my_function'",
        10,
        8,
        "my_function(q, arr)",
    ),
    "qubit_passed_as_array": (
        """
        OPENQASM 3.0;
        include "stdgates.inc";

        def my_function(mutable array[int[8], 2, 2] my_arr) {
            return;
        }
        qubit[2] q;
        my_function(q);
        """,
        r"Expecting type 'array\[int\[8\],...\]' for 'my_arr' in function 'my_function'."
        r" Qubit register 'q' found for function call",
        9,
        8,
        "my_function(q)",
    ),
    "invalid_dimension_number": (
        """
        OPENQASM 3.0;
        include "stdgates.inc";

        def my_function(qubit a, readonly array[int[8], #dim = -3] my_arr) {
            return;
        }
        qubit q;
        array[int[8], 2, 2, 2] arr;
        my_function(q, arr);
        """,
        r"Invalid number of dimensions -3 for 'my_arr' in function 'my_function'",
        10,
        8,
        "my_function(q, arr)",
    ),
    "invalid_non_int_dimensions_1": (
        """
        OPENQASM 3.0;
        include "stdgates.inc";

        def my_function(qubit a, mutable array[int[8], #dim = 2.5] my_arr) {
            return;
        }
        qubit q;
        array[int[8], 2, 2] arr;
        my_function(q, arr);
        """,
        r"Invalid dimension size 2.5 for 'my_arr' in function 'my_function'",
        10,
        8,
        "my_function(q, arr)",
    ),
    "invalid_non_int_dimensions_2": (
        """
        OPENQASM 3.0;
        include "stdgates.inc";

        def my_function(qubit a, readonly array[int[8], 2.5, 2] my_arr) {
            return;
        }
        qubit q;
        array[int[8], 2, 2] arr;
        my_function(q, arr);
        """,
        r"Invalid dimension size 2.5 for 'my_arr' in function 'my_function'",
        10,
        8,
        "my_function(q, arr)",
    ),
    "extra_dimensions_for_array": (
        """
        OPENQASM 3.0;
        include "stdgates.inc";

        def my_function(qubit a, mutable array[int[8], 4, 2] my_arr) {
            return;
        }
        qubit q;
        array[int[8], 2, 2] arr;
        my_function(q, arr);
        """,
        r"Invalid dimension size 4 for 'my_arr' in function 'my_function'",
        10,
        8,
        "my_function(q, arr)",
    ),
    "invalid_array_dimensions_formal_arg": (
        """
        OPENQASM 3;
        include "stdgates.inc";

        def my_function(readonly array[int[32], -1, 2] a) {
            return;
        }
        array[int[32], 1, 2] b;
        my_function(b);
        """,
        r"Invalid dimension size -1 for 'a' in function 'my_function'",
        9,
        8,
        "my_function(b)",
    ),
    "invalid_array_mutation_for_readonly_arg": (
        """
        OPENQASM 3;
        include "stdgates.inc";

        def my_function(readonly array[int[32], 1, 2] a) {
            a[1][0] = 5;
            return;
        }
        array[int[32], 1, 2] b;
        my_function(b);
        """,
        r"Assignment to readonly variable 'a' not allowed in function call",
        6,
        12,
        "a[1][0] = 5",
    ),
}
