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
Module containing unit tests for QASM3 to QIR conversion functions.

"""
import pytest

from pyqasm.entrypoint import loads
from pyqasm.exceptions import ValidationError
from tests.qasm3.resources.variables import (
    ASSIGNMENT_TESTS,
    CASTING_TESTS,
    DECLARATION_TESTS,
    FAIL_CASTING_TESTS,
)
from tests.utils import check_single_qubit_rotation_op


# 1. Test scalar declarations in different ways
def test_scalar_declarations():
    """Test scalar declarations in different ways"""
    qasm3_string = """
    OPENQASM 3.0;
    include "stdgates.inc";
    int a;
    uint b;
    int[2] c;
    uint[3] d;
    float[32] f;
    float[64] g;
    bit h;
    bool i;
    duration j;
    stretch st;
    """

    loads(qasm3_string).validate()


# 2. Test const declarations in different ways
def test_const_declarations():
    """Test const declarations in different ways"""
    qasm3_string = """
    OPENQASM 3.0;
    include "stdgates.inc";
    const int a = 5;
    const uint b = 10;
    const int[2*9] c = 1;
    const uint[3-1] d = 2;
    const bool boolean_var = true;
    const float[32] f = 0.00000023;
    const float[64] g = 2345623454564564564564545456456546456456456.0;

    const int a1 = 5 + a;
    const uint b1 = 10 + b;
    const int[2*9] c1 = 1 + 2*c + a;
    const uint[6-1] d1 = 2 + d;
    const bool boolean_var1 = !boolean_var;
    const float[32] f1 = 0.00000023 + f;
    const duration t2 = 300ns;
    const duration t3 = 300us;
    const duration t8 = t2/t3;
    const stretch st = 300ns;
    const stretch st2 = t2/t3;
    """

    loads(qasm3_string).validate()


# 3. Test non-constant scalar assignments
def test_scalar_assignments():
    """Test scalar assignments in different ways"""
    qasm3_string = """
    OPENQASM 3.0;
    include "stdgates.inc";
    int a = 5;
    uint b;
    int[2*9] c = 1;
    uint[3-1] d = 2;
    float r;
    float[32] f = 0.00000023;
    float[64] g = 23456.023424983573645873465836483645876348564387;
    b = 12;
    r = 12.2;
    duration du = 200us;
    duration du2;
    du2 = 300s;
    """

    loads(qasm3_string).validate()


# 4. Scalar value assignment
def test_scalar_value_assignment():
    """Test assigning variable values from other variables"""
    qasm3_string = """
    OPENQASM 3.0;
    include "stdgates.inc";
    int a = 5;
    float[32] r;
    float[32] f = 0.5;
    int b = a;
    r = 0.23;
    qubit q;
    rx(b) q;
    rx(r + f*4) q;
    duration t2 = 300ns;
    duration t6 = 300dt;
    duration t7 = 300 us;
    duration t9 = t2 - t7;
    duration t10 = t2 + t7;
    duration t11 = t2 * t7;
    """

    b = 5.0
    r = 0.23
    f = 0.5
    result = loads(qasm3_string)
    result.unroll()

    assert result.num_clbits == 0
    assert result.num_qubits == 1

    check_single_qubit_rotation_op(result.unrolled_ast, 2, [0, 0], [b, r + f * 4], "rx")


def test_scalar_type_casts():
    """Test type casts on scalar variables"""
    qasm3_string = """
    OPENQASM 3.0;
    include "stdgates.inc";
    int[32] a = 5.1;
    float[32] r = 245;
    uint[4] b = -4; // -4 % 16 = 12
    bool f = 0;
    bool g = 1;
    bit h = 1;

    qubit q;
    rx(a) q;
    rx(r) q;
    rx(b) q;
    rx(f) q;
    rx(g) q;

    """
    a = 5
    r = 245
    b = 12
    f = 0
    g = 1

    result = loads(qasm3_string)
    result.unroll()

    assert result.num_clbits == 1
    assert result.num_qubits == 1

    check_single_qubit_rotation_op(result.unrolled_ast, 5, [0, 0, 0, 0, 0], [a, r, b, f, g], "rx")


def test_array_type_casts():
    """Test type casts on array variables"""
    qasm3_string = """
    OPENQASM 3.0;
    include "stdgates.inc";
    array[int[32], 3, 2] arr_int = { {1, 2}, {3, 4}, {5, 6.2} };
    array[uint[32], 3, 2] arr_uint = { {1, 2}, {3, 4}, {5, 6.2} };
    array[bool, 3, 2] arr_bool = { {true, false}, {true, false}, {true, 12} };
    array[float[32], 3, 2] arr_float32 = { {1.0, 2.0}, {3.0, 4.0}, {5.0, 6} };

    qubit q;
    rx(arr_int[2][1]) q; // should be 6
    rx(arr_uint[2][1]) q; // should be 6
    rx(arr_bool[2][1]) q; // should be 1 (true)
    rx(arr_float32[2][1]) q; // should be 6.0

    """
    arr_int_val = 6
    arr_uint_val = 6
    arr_bool_val = 1
    arr_float32_val = 6.0

    result = loads(qasm3_string)
    result.unroll()

    assert result.num_clbits == 0
    assert result.num_qubits == 1

    check_single_qubit_rotation_op(
        result.unrolled_ast,
        4,
        [0, 0, 0, 0],
        [arr_int_val, arr_uint_val, arr_bool_val, arr_float32_val],
        "rx",
    )


# 5. Array declarations
def test_array_declarations():
    """Test array declarations in different ways"""
    qasm3_string = """
    OPENQASM 3.0;
    include "stdgates.inc";
    array[int[32], 3, 2] arr_int;
    array[uint[32-9], 3, 2] arr_uint;
    array[float[32], 3, 2] arr_float32;
    array[float[64], 3, 2] arr_float64;
    array[bool, 3, 2] arr_bool;
    """
    loads(qasm3_string).validate()


# 6. Array assignments
def test_array_assignments():
    """Test array assignments"""

    qasm3_string = """
    OPENQASM 3.0;
    include "stdgates.inc";

    array[int[32], 3, 2] arr_int;
    array[uint[32], 3, 2] arr_uint;
    array[float[32], 3, 2] arr_float32;
    array[float[64], 3, 2] arr_float64;
    array[bool, 3, 2] arr_bool;

    int a = 2;
    uint b = 3;
    float[32] c = 4.5;
    float[64] d = 6.7;
    bool f = true;

    arr_int[0][1] = a*a;
    arr_int[0,1] = a*a;

    arr_uint[0][1] = b*b;
    arr_uint[0,1] = b*b;

    arr_float32[0][1] = c*c;
    arr_float32[0,1] = c*c;

    arr_float64[0][1] = d*d;
    arr_float64[0,1] = d*d;

    arr_bool[0][1] = f;
    arr_bool[0,1] = f;

    qubit q;
    rx(arr_int[0,1]) q;
    rx(arr_uint[0][1]) q;
    rx(arr_float32[0,1]) q;
    rx(arr_float64[0][1]) q;
    rx(arr_bool[0,1]) q;
    """

    a = 2
    b = 3
    c = 4.5
    d = 6.7
    f = True
    result = loads(qasm3_string)
    result.unroll()

    assert result.num_clbits == 0
    assert result.num_qubits == 1
    check_single_qubit_rotation_op(
        result.unrolled_ast, 5, [0, 0, 0, 0, 0], [a * a, b * b, c * c, d * d, f], "rx"
    )


# 7. Test expressions which involves arrays
def test_array_expressions():
    """Test array expressions"""
    qasm3_string = """
    OPENQASM 3.0;
    include "stdgates.inc";

    array[int[32], 3, 2] arr_int;
    array[uint[32], 3, 2] arr_uint;
    array[float[32], 3, 2] arr_float32;
    array[float[64], 3, 2] arr_float64;
    array[bool, 3, 2] arr_bool;

    int a = 2;
    uint b = 3;
    float[32] c = 4.5;
    float[64] d = 6.7;
    bool f = true;


    arr_int[0][1] = a*a;
    arr_int[1][0] = arr_int[0][1];
    arr_uint[0][1] = b*b;
    arr_float32[0][1] = c*c;
    arr_float64[0][1] = d*d;

    qubit q;
    rx(arr_int[{0,1}] + arr_uint[0][1]) q;
    rx(arr_float32[{0,1}] + arr_float64[0][1]) q;
    """

    a = 2
    b = 3
    c = 4.5
    d = 6.7
    result = loads(qasm3_string)
    result.unroll()

    assert result.num_clbits == 0
    assert result.num_qubits == 1
    check_single_qubit_rotation_op(
        result.unrolled_ast, 2, [0, 0], [a * a + b * b, c * c + d * d], "rx"
    )


def test_array_initializations():
    """Test array initializations"""

    qasm3_string = """
    OPENQASM 3.0;
    include "stdgates.inc";

    array[int[32], 3, 2] arr_int = { {1, 2}, {3, 4}, {5, 6} };
    array[uint[32], 3, 2] arr_uint = { {1, 2}, {3, 4}, {5, 6} };
    array[float[32], 3, 2] arr_float32 = { {1.0, 2.0}, {3.0, 4.0}, {5.0, 6.0} };
    array[float[64], 3, 2] arr_float64 = { {1.0, 2.0}, {3.0, 4.0}, {5.0, 6.0} };
    array[bool, 3, 2] arr_bool = { {true, false}, {true, false}, {true, false} };

    qubit q;
    rx(arr_int[0][1]) q;
    rx(arr_uint[0][1]) q;
    rx(arr_float32[0][1]) q;
    rx(arr_float64[0][1]) q;
    rx(arr_bool[0][1]) q;
    """

    result = loads(qasm3_string)
    result.unroll()

    assert result.num_clbits == 0
    assert result.num_qubits == 1

    check_single_qubit_rotation_op(
        result.unrolled_ast, 5, [0, 0, 0, 0, 0], [2, 2, 2.0, 2.0, 0], "rx"
    )


def test_array_range_assignment():
    """Test array range assignment"""

    qasm3_string = """
    OPENQASM 3.0;
    include "stdgates.inc";

    array[int[32], 3, 2] arr_int = { {1, 2}, {3, 4}, {5, 6} };
    array[uint[32], 3, 2] arr_uint = { {1, 2}, {3, 4}, {5, 6} };
    array[float[32], 3, 2] arr_float32 = { {1.0, 2.0}, {3.0, 4.0}, {5.0, 6.0} };

    arr_int[0, 0:1] = arr_int[1, 0:1];
    arr_uint[0:2, 1] = arr_uint[0:2, 0];
    arr_float32[0:2, 1] = arr_float32[0:2, 0];

    qubit q;
    rx(arr_int[0][1]) q;
    rx(arr_uint[0][1]) q;
    rx(arr_float32[1][1]) q;

    """

    result = loads(qasm3_string)
    result.unroll()

    assert result.num_clbits == 0
    assert result.num_qubits == 1

    check_single_qubit_rotation_op(result.unrolled_ast, 3, [0, 0, 0], [4, 1, 3.0], "rx")


@pytest.mark.parametrize("test_name", DECLARATION_TESTS.keys())
def test_incorrect_declarations(test_name, caplog):
    qasm_input, error_message, line_num, col_num, err_line = DECLARATION_TESTS[test_name]
    with pytest.raises(ValidationError, match=error_message):
        with caplog.at_level("ERROR"):
            loads(qasm_input).validate()

    assert f"Error at line {line_num}, column {col_num}" in caplog.text
    assert err_line in caplog.text


@pytest.mark.parametrize("test_name", ASSIGNMENT_TESTS.keys())
def test_incorrect_assignments(test_name, caplog):
    qasm_input, error_message, line_num, col_num, err_line = ASSIGNMENT_TESTS[test_name]
    with pytest.raises(ValidationError, match=error_message):
        with caplog.at_level("ERROR"):
            loads(qasm_input).validate()

    assert f"Error at line {line_num}, column {col_num}" in caplog.text
    assert err_line in caplog.text


@pytest.mark.parametrize("test_name", CASTING_TESTS.keys())
def test_explicit_casting(test_name):
    qasm_input = CASTING_TESTS[test_name]
    loads(qasm_input).validate()


@pytest.mark.parametrize("test_name", FAIL_CASTING_TESTS.keys())
def test_incorrect_casting(test_name, caplog):
    qasm_input, error_message, line_num, col_num, err_line = FAIL_CASTING_TESTS[test_name]
    with pytest.raises(ValidationError) as excinfo:
        loads(qasm_input).validate()

    first = excinfo.value.__cause__ or excinfo.value.__context__
    assert first is not None, "Expected a chained ValidationError"
    msg = str(first)
    assert error_message in msg
    assert f"Error at line {line_num}, column {col_num}" in caplog.text
    assert err_line in caplog.text


@pytest.mark.parametrize(
    "qasm_code,error_message,error_span",
    [
        (
            """
            OPENQASM 3.0;
            include "stdgates.inc";
            const stretch cd = stretch(200ns);
            """,
            r"constant variable with 'StretchType' doesn't support 'Casting'",
            r"Error at line 4, column 12",
        ),
        (
            """
            OPENQASM 3.0;
            include "stdgates.inc";
            const stretch d = 2;
            """,
            r"constant variable with 'StretchType' expects a value of type 'DurationLiteral'",
            r"Error at line 4, column 12",
        ),
        (
            """
            OPENQASM 3.0;
            include "stdgates.inc";
            const int a = 2;
            const stretch d = a;
            """,
            r"Assigned constant variable 'a' is not in 'DurationType' or 'StretchType'",
            r"Error at line 5, column 12",
        ),
        (
            """
            OPENQASM 3.0;
            include "stdgates.inc";
            const stretch s = -20ns;
            """,
            r"'StretchType'[-20.0] cannot have duration value 'less than or equal to 0'",
            r"Error at line 4, column 12",
        ),
        (
            """
            OPENQASM 3.0;
            include "stdgates.inc";
            stretch s = 20ns;
            """,
            r"Assignment to 'stretch' type variable 's' is not allowed,"
            r" must be initialized with a constant at declaration.",
            r"Error at line 4, column 12",
        ),
        (
            """
            OPENQASM 3.0;
            include "stdgates.inc";
            int a = 2;
            stretch d;
            d = a;
            """,
            r"Assignment to 'stretch' type variable 'd' is not allowed,"
            r" must be initialized with a constant at declaration.",
            r"Error at line 6, column 12",
        ),
    ],
)  # pylint: disable-next= too-many-arguments
def test_stretch_type_error(qasm_code, error_message, error_span, caplog):
    with pytest.raises(ValidationError) as err:
        with caplog.at_level("ERROR"):
            loads(qasm_code).validate()
    assert error_message in str(err.value)
    assert error_span in caplog.text


@pytest.mark.parametrize(
    "qasm_code,error_message,error_span",
    [
        (
            """
            OPENQASM 3.0;
            include "stdgates.inc";
            duration d1 = duration(200ns);
            """,
            r"variable with 'DurationType' doesn't support 'Casting'",
            r"Error at line 4, column 12",
        ),
        (
            """
            OPENQASM 3.0;
            include "stdgates.inc";
            const duration cd = duration(200ns);
            """,
            r"constant variable with 'DurationType' doesn't support 'Casting'",
            r"Error at line 4, column 12",
        ),
        (
            """
            OPENQASM 3.0;
            include "stdgates.inc";
            const duration d = 2;
            """,
            r"constant variable with 'DurationType' expects a value of type 'DurationLiteral'",
            r"Error at line 4, column 12",
        ),
        (
            """
            OPENQASM 3.0;
            include "stdgates.inc";
            const int a = 2;
            const duration d = a;
            """,
            r"Assigned constant variable 'a' is not in 'DurationType' or 'StretchType'",
            r"Error at line 5, column 12",
        ),
        (
            """
            OPENQASM 3.0;
            include "stdgates.inc";
            duration d = 2;
            """,
            r"variable with 'DurationType' expects a value of type 'DurationLiteral'",
            r"Error at line 4, column 12",
        ),
        (
            """
            OPENQASM 3.0;
            include "stdgates.inc";
            int a = 2;
            duration d = a;
            """,
            r"Assigned variable 'a' is not in 'DurationType' or 'StretchType'",
            r"Error at line 5, column 12",
        ),
        (
            """
            OPENQASM 3.0;
            include "stdgates.inc";
            duration d;
            d = 2;
            """,
            r"variable with 'DurationType' expects a value of type 'DurationLiteral'",
            r"Error at line 5, column 12",
        ),
        (
            """
            OPENQASM 3.0;
            include "stdgates.inc";
            int a = 2;
            duration d;
            d = a;
            """,
            r"Assigned variable 'a' is not in 'DurationType' or 'StretchType'",
            r"Error at line 6, column 12",
        ),
        (
            """
            OPENQASM 3.0;
            include "stdgates.inc";
            duration d = 0ns;
            """,
            r"'DurationType' cannot have duration value '0'",
            r"Error at line 4, column 12",
        ),
    ],
)  # pylint: disable-next= too-many-arguments
def test_duration_casting_error(qasm_code, error_message, error_span, caplog):
    with pytest.raises(ValidationError) as err:
        with caplog.at_level("ERROR"):
            loads(qasm_code, device_cycle_time=1e-9).validate()
    assert error_message in str(err.value)
    assert error_span in caplog.text


def test_device_time_duration_():
    """Test device cycle time duration"""
    qasm3_string = """
    OPENQASM 3.0;
    include "stdgates.inc";
    duration t1 = 300dt;
    duration t2 = 300ns;
    const duration t3 =300us;
    """
    loads(qasm3_string, device_cycle_time=1e-9).validate()
