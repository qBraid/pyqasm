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
Module containing unit tests for parsing and unrolling programs that contain subroutines.

"""

import pytest

from pyqasm.entrypoint import dumps, loads
from pyqasm.exceptions import ValidationError
from tests.qasm3.resources.subroutines import SUBROUTINE_INCORRECT_TESTS
from tests.utils import (
    check_single_qubit_gate_op,
    check_single_qubit_rotation_op,
    check_unrolled_qasm,
)


def test_function_declaration():
    """Test that a function declaration is correctly parsed."""
    qasm_str = """OPENQASM 3.0;
    include "stdgates.inc";
    def my_function(qubit q) {
        h q;
        return;
    }
    qubit q;
    my_function(q);
    """

    result = loads(qasm_str)
    result.unroll()
    assert result.num_clbits == 0
    assert result.num_qubits == 1

    check_single_qubit_gate_op(result.unrolled_ast, 1, [0], "h")


def test_simple_function_call():
    """Test that a simple function call is correctly parsed."""
    qasm_str = """OPENQASM 3.0;
    include "stdgates.inc";

    def my_function(qubit a, float[32] b) {
        rx(b) a;
        float[64] c = 2*b;
        rx(c) a;
        return;
    }
    qubit q;
    float[32] r = 3.14;
    my_function(q, r);
    """

    result = loads(qasm_str)
    result.unroll()
    assert result.num_clbits == 0
    assert result.num_qubits == 1

    check_single_qubit_rotation_op(result.unrolled_ast, 2, [0, 0], [3.14, 6.28], "rx")


def test_const_visible_in_function_call():
    """Test that a constant is visible in a function call."""
    qasm_str = """OPENQASM 3.0;
    include "stdgates.inc";
    const float[32] pi2 = 3.14;

    def my_function(qubit q) {
        rx(pi2) q;
        return;
    }
    qubit q;
    my_function(q);
    """

    result = loads(qasm_str)
    result.unroll()
    assert result.num_clbits == 0
    assert result.num_qubits == 1

    check_single_qubit_rotation_op(result.unrolled_ast, 1, [0], [3.14], "rx")


def test_update_variable_in_function():
    """Test that variable update works correctly in a function."""
    qasm_str = """OPENQASM 3.0;
    include "stdgates.inc";

    def my_function(qubit q) {
        float[32] a = 3.14;
        a = 2*a;
        rx(a) q;
        return;
    }
    qubit q;
    my_function(q);
    """

    result = loads(qasm_str)
    result.unroll()
    assert result.num_clbits == 0
    assert result.num_qubits == 1

    check_single_qubit_rotation_op(result.unrolled_ast, 1, [0], [6.28], "rx")


def test_function_call_in_expression():
    """Test that a function call in an expression is correctly parsed."""
    qasm_str = """OPENQASM 3.0;
    include "stdgates.inc";

    def my_function(qubit[4] q) -> bool{
        h q;
        return true;
    }
    qubit[4] q;
    
    // this is to be explained
    bool b = my_function(q);
    """

    result = loads(qasm_str)
    result.unroll()
    assert result.num_clbits == 0
    assert result.num_qubits == 4

    check_single_qubit_gate_op(result.unrolled_ast, 4, list(range(4)), "h")


def test_classical_quantum_function():
    """Test that a function with classical and quantum instructions is correctly unrolled"""
    qasm_str = """
    OPENQASM 3.0;
    include "stdgates.inc";
    def my_function(qubit qin, int[32] iter) -> int[32]{
        h qin;
        if(iter>2)
            x qin;
        if (iter>3)
            y qin;
        return iter + 1;
    }
    qubit[4] q;
    int[32] new_var ;
    for int i in [0:3]
    { 
        new_var = my_function(q[i] , i);
    }

    if(new_var>2)
        h q[0];
    """
    result = loads(qasm_str)
    result.unroll()
    assert result.num_clbits == 0
    assert result.num_qubits == 4

    check_single_qubit_gate_op(result.unrolled_ast, 5, list(range(4)) + [0], "h")
    check_single_qubit_gate_op(result.unrolled_ast, 1, [3], "x")


def test_multiple_function_calls():
    """Test that multiple function calls are correctly parsed."""
    qasm_str = """OPENQASM 3.0;
    include "stdgates.inc";

    def my_function(int[32] a, qubit q_arg) {
        h q_arg;
        rx (a) q_arg;
        return;
    }
    qubit[3] q;
    my_function(2, q[2]);
    my_function(1, q[1]);
    my_function(0, q[0]);
    """

    result = loads(qasm_str)
    result.unroll()
    assert result.num_clbits == 0
    assert result.num_qubits == 3

    check_single_qubit_gate_op(result.unrolled_ast, 3, [2, 1, 0], "h")
    check_single_qubit_rotation_op(result.unrolled_ast, 3, [2, 1, 0], [2, 1, 0], "rx")


def test_alias_arg_from_loop_validates():
    """Alias of a dynamic indexed qubit used as function argument should validate."""
    qasm_str = """
    OPENQASM 3.0;
    include "stdgates.inc";

    qubit[4] q;

    def dummy(qubit[1] q_arg) -> bool { 
        h q_arg;
        return true;
    }

    for int i in [0:2]
    {
       let new_q = q[i];
       dummy(new_q);
    }
    for int i in [0:2]
    {
       let new_q = q[i+1];
       dummy(new_q);
    }
    """

    result = loads(qasm_str)
    # Should not raise ValidationError
    result.unroll()


def test_function_call_with_return():
    """Test that a function call with a return value is correctly parsed."""
    qasm_str = """OPENQASM 3.0;
    include "stdgates.inc";

    def my_function(qubit q) -> float[32] {
        h q;
        return 3.14;
    }
    qubit q;
    float[32] r = my_function(q);
    """

    result = loads(qasm_str)
    result.unroll()
    assert result.num_clbits == 0
    assert result.num_qubits == 1

    check_single_qubit_gate_op(result.unrolled_ast, 1, [0], "h")


def test_return_values_from_function():
    """Test that the values returned from a function are used correctly in other function."""
    qasm_str = """OPENQASM 3.0;
    include "stdgates.inc";
    def my_function(qubit qin) -> float[32] {
        h qin;
        return 3.14;
    }
    def my_function_2(qubit qin, float[32] r) {
        rx(r) qin;
        return;
    }
    qubit[2] q;
    float[32] r1 = my_function(q[0]);
    my_function_2(q[0], r1);

    array[float[32], 1, 1] r2 = {{3.14}};
    my_function_2(q[1], r2[0,0]);

    """

    result = loads(qasm_str)
    result.unroll()
    assert result.num_clbits == 0
    assert result.num_qubits == 2

    check_single_qubit_gate_op(result.unrolled_ast, 1, [0], "h")
    check_single_qubit_rotation_op(result.unrolled_ast, 2, [0, 1], [3.14, 3.14], "rx")


def test_function_call_with_custom_gate():
    """Test that a function call with a custom gate is correctly parsed."""
    qasm_str = """OPENQASM 3.0;
    include "stdgates.inc";

    gate my_gate(a) q2 { 
        rx(a) q2; 
    }

    def my_function(qubit a, float[32] b) {
        float[64] c = 2*b;
        my_gate(b) a;
        my_gate(c) a;
        return;
    }
    qubit q;
    float[32] r = 3.14;
    my_function(q, r);
    """

    result = loads(qasm_str)
    result.unroll()
    assert result.num_clbits == 0
    assert result.num_qubits == 1

    check_single_qubit_rotation_op(result.unrolled_ast, 2, [0, 0], [3.14, 6.28], "rx")


def test_function_call_from_within_fn():
    """Test that a function call from within another function is correctly converted."""
    qasm_str = """OPENQASM 3.0;
    include "stdgates.inc";
    def my_function(qubit q1, float[32] a) {
        h q1;
        rx(a) q1;
        return;
    }

    def my_function_2(qubit[2] q2, float[32] param) {
        my_function(q2[1], param);
        return;
    }

    def my_function_3(qubit[2] q3) {
        float[32] a = 3.14;
        my_function_2(q3, a);
        my_function(q3[1], a);
        return;
    }

    qubit[2] q;
    float[32] r = 3.14;
    my_function_2(q, r);
    my_function_3(q);
    """

    result = loads(qasm_str)
    result.unroll()
    assert result.num_clbits == 0
    assert result.num_qubits == 2

    check_single_qubit_gate_op(result.unrolled_ast, 3, [1, 1, 1], "h")
    check_single_qubit_rotation_op(result.unrolled_ast, 3, [1] * 3, [3.14] * 3, "rx")


@pytest.mark.skip(reason="Bug: qubit in function scope conflicts with global scope")
def test_qubit_renaming_in_formal_params():
    """Test that the values returned from a function are used correctly in other function."""
    qasm_str = """OPENQASM 3.0;
    include "stdgates.inc";
    def my_function(qubit q) -> float[32] {
        h q;
        return 3.14;
    }
    def my_function_2(qubit q, float[32] r) {
        rx(r) q;
        return;
    }
    qubit[2] q;
    float[32] r1 = my_function(q[0]);
    my_function_2(q[0], r1);

    array[float[32], 1, 1] r2 = {{3.14}};
    my_function_2(q[1], r2[0,0]);

    """

    result = loads(qasm_str)
    result.unroll()
    assert result.num_clbits == 0
    assert result.num_qubits == 2

    check_single_qubit_gate_op(result.unrolled_ast, 1, [0], "h")
    check_single_qubit_rotation_op(result.unrolled_ast, 2, [0, 1], [3.14, 3.14], "rx")


@pytest.mark.parametrize("data_type", ["int[32] a = 1;", "float[32] a = 1.0;", "bit a = 0;"])
def test_return_value_mismatch(data_type, caplog):
    """Test that returning a value of incorrect type raises error."""
    qasm_str = (
        """OPENQASM 3.0;
    include "stdgates.inc";

    def my_function(qubit q) {
        h q;
    """
        + data_type
        + """
        return a;
    }
    qubit q;
    my_function(q);
    """
    )

    with pytest.raises(
        ValidationError, match=r"Return type mismatch for subroutine 'my_function'.*"
    ):
        with caplog.at_level("ERROR"):
            loads(qasm_str).validate()

    assert "Error at line 7, column 8" in caplog.text
    assert "return a" in caplog.text


@pytest.mark.parametrize("keyword", ["pi", "euler", "tau"])
def test_subroutine_keyword_naming(keyword, caplog):
    """Test that using a keyword as a subroutine name raises error."""
    qasm_str = f"""OPENQASM 3.0;
    include "stdgates.inc";

    def {keyword}(qubit q) {{
        h q;
        return;
    }}
    qubit q;
    {keyword}(q);
    """

    with pytest.raises(ValidationError, match=f"Subroutine name '{keyword}' is a reserved keyword"):
        with caplog.at_level("ERROR"):
            loads(qasm_str).validate()

    assert "Error at line 4, column 4" in caplog.text
    assert f"def {keyword}" in caplog.text


@pytest.mark.parametrize("qubit_params", ["q", "q[:2]", "q[{0, 1}]"])
def test_qubit_size_arg_mismatch(qubit_params, caplog):
    """Test that passing a qubit of different size raises error."""
    qasm_str = (
        """OPENQASM 3.0;
    include "stdgates.inc";

    def my_function(qubit[3] q) {
        h q;
        return;
    }
    qubit[2] q;
    my_function("""
        + qubit_params
        + """);
    """
    )

    with pytest.raises(
        ValidationError,
        match="Qubit register size mismatch for function 'my_function'. "
        "Expected 3 qubits in variable 'q' but got 2",
    ):
        with caplog.at_level("ERROR"):
            loads(qasm_str).validate()

    assert "Error at line 9, column 4" in caplog.text
    assert f"my_function({qubit_params})" in caplog.text


@pytest.mark.parametrize("test_name", SUBROUTINE_INCORRECT_TESTS.keys())
def test_incorrect_custom_ops(test_name, caplog):
    qasm_str, error_message, line_num, col_num, err_line = SUBROUTINE_INCORRECT_TESTS[test_name]
    with pytest.raises(ValidationError, match=error_message):
        with caplog.at_level("ERROR"):
            loads(qasm_str).validate()

    assert f"Error at line {line_num}, column {col_num}" in caplog.text
    assert err_line in caplog.text


def test_extern_function_call():
    """Test extern function call"""
    qasm3_string = """
    OPENQASM 3.0;
    include "stdgates.inc";
    float a = 1.0;
    int b = 2;
    extern func1(float, int) -> bit;
    bit c = 2 * func1(a, b);
    bit fc = -func1(a, b);

    bit[2] b1 = true;
    angle ang1 = pi/2;
    extern func2(bit[2], angle) -> complex;
    const complex d = func2(b1, ang1);
    const complex e = func2(b1, ang1) + 2.0;
    const complex f = -func2(b1, ang1);
    
    duration t1 = 100ns;
    bool b2 = true;
    extern func3(duration, bool) -> int;
    int dd;
    dd = func3(t1, b2);
    int ee;
    ee = func3(t1, b2) + 2;
    int ff;
    ff = -func3(t1, b2);
    int gg;
    gg = func3(t1, b2) * func3(t1, b2);

    float[32] fa = 3.14;
    float[32] fb = 2.71;
    extern func4(float[32], float[32]) -> float[32];
    float[32] fc1 = func4(fa, fb);

    complex[float[64]] ca = 1.0 + 2.0im;
    complex[float[64]] cb = 3.0 - 4.0im;
    extern func5(complex[float[64]], complex[float[64]]) -> complex[float[64]];
    complex[float[64]] cc1 = func5(ca, cb);

    bit[4] bd = "0101";
    extern func6(bit[4]) -> bit[4];
    bit[4] be1 = func6(bd);

    angle[8] an = pi/4;
    extern func7(angle[8]) -> angle[8];
    angle[8] af1 = func7(an);

    bool bl = false;
    extern func8(bool) -> bool;
    bool bf1 = func8(bl);

    int[24] ix = 42;
    extern func9(int[24]) -> int[24];
    int[24] ig1 = func9(ix);

    float[64] fx = 2.718;
    extern func10(float[64]) -> float[64];
    float[64] fg1 = func10(fx);
    """

    expected_qasm = """OPENQASM 3.0;
    include "stdgates.inc";
    extern func1(float, int) -> bit;
    bit[1] c = 2 * func1(1.0, 2);
    bit[1] fc = -func1(1.0, 2);
    bit[2] b1 = true;
    extern func2(bit[2], angle) -> complex;
    const complex d = func2(True, 1.5707963267948966);
    const complex e = func2(True, 1.5707963267948966) + 2.0; 
    const complex f = -func2(True, 1.5707963267948966);
    extern func3(duration, bool) -> int;
    dd = func3(100.0ns, True);
    ee = func3(100.0ns, True) + 2;
    ff = -func3(100.0ns, True);
    gg = func3(100.0ns, True) * func3(100.0ns, True);
    extern func4(float[32], float[32]) -> float[32];
    float[32] fc1 = func4(3.14, 2.71);
    extern func5(complex[float[64]], complex[float[64]]) -> complex[float[64]];
    complex[float[64]] cc1 = func5(1.0 + 2.0im, 3.0 - 4.0im);
    bit[4] bd = "0101";
    extern func6(bit[4]) -> bit[4];
    bit[4] be1 = func6("0101");
    extern func7(angle[8]) -> angle[8];
    angle[8] af1 = func7(0.7853981633974483);
    extern func8(bool) -> bool;
    bool bf1 = func8(False);
    extern func9(int[24]) -> int[24];
    int[24] ig1 = func9(42);
    extern func10(float[64]) -> float[64];
    float[64] fg1 = func10(2.718);
    """

    extern_functions = {
        "func1": (["float", "int"], "bit"),
        "func2": (["bit[2]", "angle"], "complex"),
        "func3": (["duration", "bool"], "int"),
        "func4": (["float[32]", "float[32]"], "float[32]"),
        "func5": (["complex[float[64]]", "complex[float[64]]"], "complex[float[64]]"),
        "func6": (["bit[4]"], "bit[4]"),
        "func7": (["angle[8]"], "angle[8]"),
        "func8": (["bool"], "bool"),
        "func9": (["int[24]"], "int[24]"),
        "func10": (["float[64]"], "float[64]"),
    }

    result = loads(qasm3_string, extern_functions=extern_functions)
    result.validate()
    result.unroll()
    unrolled_qasm = dumps(result)

    check_unrolled_qasm(unrolled_qasm, expected_qasm)


@pytest.mark.parametrize(
    "qasm_code,error_message,error_span",
    [
        (
            """
            OPENQASM 3.0;
            include "stdgates.inc";
            bit[4] bd = true;
            float[64] fx = 2.718;
            extern func6(bit[4]) -> bit[4];
            extern func10(float[64]) -> float[64];
            bit[4] be1 = func6(bd) * func10(fx);
            """,
            r"extern function return type mismatch in binary expression: BitType and FloatType",
            r"Error at line 8, column 25",
        ),
        (
            """
            OPENQASM 3.0;
            include "stdgates.inc";
            bit bd = true;
            extern func6(bit[4]) -> bit[4];
            bit[4] be1 = func6(bd);
            """,
            r"Argument type mismatch in function 'func6', expected BitType[4] but got BitType[1]",
            r"Error at line 6, column 25",
        ),
        (
            """
            OPENQASM 3.0;
            include "stdgates.inc";
            bit bd = true;
            extern func6(bit[4]) -> bit[4];
            bit[4] be1 = func6(fd);
            """,
            r"Undefined variable 'fd' used for function call 'func6'",
            r"Error at line 6, column 25",
        ),
    ],
)  # pylint: disable-next= too-many-arguments
def test_extern_function_call_error(qasm_code, error_message, error_span, caplog):
    with pytest.raises(ValidationError) as excinfo:
        with caplog.at_level("ERROR"):
            loads(
                qasm_code,
            ).validate()
    first = excinfo.value.__cause__ or excinfo.value.__context__
    assert first is not None, "Expected a chained ValidationError"
    msg = str(first)
    assert error_message in msg
    assert error_span in caplog.text


@pytest.mark.parametrize(
    "qasm_code,error_message,error_span",
    [
        (
            """
            OPENQASM 3.0;
            include "stdgates.inc";
            float fx = 2.718;
            int ix = 42;
            extern func1(float) -> bit;
            bit be1 = func1(fx);
            """,
            r"Parameter count mismatch for 'extern' subroutine 'func1'. Expected 2 but got 1",
            r"Error at line 6, column 12",
        ),
        (
            """
            OPENQASM 3.0;
            include "stdgates.inc";
            float fx = 2.718;
            int ix = 42;
            extern func1(float[64], int[64]) -> bit;
            bit be1 = func1(fx);
            """,
            r"Parameter type mismatch for 'extern' subroutine 'func1'."
            r" Expected float but got float[64]",
            r"Error at line 6, column 12",
        ),
        (
            """
            OPENQASM 3.0;
            include "stdgates.inc";
            float fx = 2.718;
            int ix = 42;
            extern func1(float, int) -> bit[2];
            bit[2] be1 = func1(fx);
            """,
            r"Return type mismatch for 'extern' subroutine 'func1'. Expected bit but got bit[2]",
            r"Error at line 6, column 12",
        ),
    ],
)  # pylint: disable-next= too-many-arguments
def test_extern_function_dict_call_error(qasm_code, error_message, error_span, caplog):
    with pytest.raises(ValidationError) as excinfo:
        with caplog.at_level("ERROR"):
            extern_functions = {
                "func1": (["float", "int"], "bit"),
                "func2": (["bit[2]", "angle"], "complex"),
                "func3": (["uint"], "int"),
            }
            loads(qasm_code, extern_functions=extern_functions).validate()
    msg = str(excinfo.value)
    assert error_message in msg
    assert error_span in caplog.text


@pytest.mark.parametrize(
    "qasm_code,error_message,error_span",
    [
        (
            """
            OPENQASM 3.0;
            include "stdgates.inc";
            extern func1(float) -> bit;
            bit be1 = func1(2);
            """,
            r"Invalid argument value for 'func1', expected 'FloatType' but got value = 2.",
            r"Error at line 5, column 12",
        ),
        (
            """
            OPENQASM 3.0;
            include "stdgates.inc";
            extern func2(uint) -> complex;
            complex ce1 = func2(-22);
            """,
            r"Invalid argument value for 'func2', expected 'UintType' but got value = -22.",
            r"Error at line 5, column 12",
        ),
        (
            """
            OPENQASM 3.0;
            include "stdgates.inc";
            extern func3(duration) -> int;
            int ie1 = func3(true);
            """,
            r"Invalid argument value for 'func3', expected 'DurationType' but got value = True.",
            r"Error at line 5, column 12",
        ),
        (
            """
            OPENQASM 3.0;
            include "stdgates.inc";
            extern func4(bit[4]) -> float[64];
            float[64] fe1 = func4(3.14);
            """,
            r"Invalid argument value for 'func4', expected 'BitType' but got value = 3.14.",
            r"Error at line 5, column 28",
        ),
        (
            """
            OPENQASM 3.0;
            include "stdgates.inc";
            extern func5(complex[float[64]]) -> complex[float[64]];
            complex[float[64]] ce1 = func5(42);
            """,
            r"Invalid argument value for 'func5', expected 'ComplexType' but got value = 42.",
            r"Error at line 5, column 37",
        ),
        (
            """
            OPENQASM 3.0;
            include "stdgates.inc";
            extern func6(angle[8]) -> angle[8];
            angle[8] ae1 = func6(100ns);
            """,
            r"Invalid argument value for 'func6', expected 'AngleType' but got value = 100.0.",
            r"Error at line 5, column 27",
        ),
        (
            """
            OPENQASM 3.0;
            include "stdgates.inc";
            extern func7(bool) -> bool;
            bool be1 = func7(3.14);
            """,
            r"Invalid argument value for 'func7', expected 'BoolType' but got value = 3.14.",
            r"Error at line 5, column 23",
        ),
        (
            """
            OPENQASM 3.0;
            include "stdgates.inc";
            extern func8(int[24]) -> int[24];
            int[24] ie1 = func8(2.0);
            """,
            r"Invalid argument value for 'func8', expected 'IntType' but got value = 2.0.",
            r"Error at line 5, column 12",
        ),
    ],
)  # pylint: disable-next= too-many-arguments
def test_extern_function_value_error(qasm_code, error_message, error_span, caplog):
    with pytest.raises(ValidationError) as excinfo:
        with caplog.at_level("ERROR"):
            extern_functions = {
                "func1": (["float"], "bit"),
                "func2": (["uint"], "complex"),
                "func3": (["duration"], "int"),
                "func4": (["bit[4]"], "float[64]"),
                "func5": (["complex[float[64]]"], "complex[float[64]]"),
                "func6": (["angle[8]"], "angle[8]"),
                "func7": (["bool"], "bool"),
                "func8": (["int[24]"], "int[24]"),
            }
            loads(qasm_code, extern_functions=extern_functions).validate()
    first = excinfo.value.__cause__ or excinfo.value.__context__
    assert first is not None, "Expected a chained ValidationError"
    msg = str(first)
    assert error_message in msg
    assert error_span in caplog.text
