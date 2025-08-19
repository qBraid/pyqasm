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
Module containing unit tests for the general errors.

"""

import pytest

from pyqasm.entrypoint import loads
from pyqasm.exceptions import ValidationError


@pytest.mark.parametrize(
    "qasm_code,error_message,error_span",
    [
        (
            """
            OPENQASM 3.0;
            defcalgrammar "openpulse";
            cal {
                play(fr1, gaussian(1.0 + 2.0im, 100ns, 5.0ns));
            }
            """,
            r"Frame 'fr1' not declared",
            r"Error at line 2, column 16",
        ),
        (
            """
            OPENQASM 3.0;
            defcalgrammar "openpulse";
            cal {
                frame frame1 = newframe(d0, 5.0e9, 0.0);
            }
            """,
            r"Variable 'd0' is not declared",
            r"Error at line 2, column 31",
        ),
        (
            """
            OPENQASM 3.0;
            defcalgrammar "openpulse";
            cal {
                port d0;
                port d0;
            }
            """,
            r"Variable 'd0' is already declared",
            r"Error at line 7, column 16",
        ),
        (
            """
            OPENQASM 3.0;
            defcalgrammar "openpulse";
            cal {
                const waveform wf1 = gaussian(1.0 + 2.0im, 100ns, 5.0ns);
                waveform wf1 = gaussian(1.0 + 2.0im, 100ns, 5.0ns);
            }
            """,
            r"Waveform 'wf1' is constant, cannot be redeclared",
            r"Error at line 7, column 16",
        ),
        (
            """
            OPENQASM 3.0;
            defcalgrammar "openpulse";
            cal {
               port d0;
               frame frame1 = newframe(d0, 5.0e9, 1.0);
               angle ph1 = pi/2;
               float ph2 = 5.0e9;
               set_phase(frame1, ph1);
               shift_phase(frame1, ph1);
               set_phase(frame1, 1.0);
               set_phase(frame1, ph2);
            }
            """,
            r"Phase argument 'ph2' must be a AngleType with same size in frame 'frame1'",
            r"Error at line 9, column 15",
        ),
        (
            """
            OPENQASM 3.0;
            defcalgrammar "openpulse";
            cal {
               port d0;
               frame frame1 = newframe(d0, 5.0e9, 1.0);
               angle ph1 = pi/2;
               set_frequency(frame1, 1.0);
               shift_frequency(frame1, 1.0);
               float freq = get_frequency(frame1);
               set_frequency(frame1, ph1);
            }
            """,
            r"Frequency argument 'ph1' must be a FloatType with same size in frame 'frame1'",
            r"Error at line 8, column 15",
        ),
        (
            """
            OPENQASM 3.0;
            defcalgrammar "openpulse";
            cal {
               port d0;
               const float freq = 1.0;
               frame frame1 = newframe(d0, 5.0e9, 1.0);
               freq = get_frequency(frame1);
            }
            """,
            r"Variable 'freq' is constant, cannot be reassigned",
            r"Error at line 9, column 15",
        ),
        (
            """
            OPENQASM 3.0;
            defcalgrammar "openpulse";
            cal {
               port d0;
               float freq = 1.0;
               frame frame1 = newframe(d0, 5.0e9, 1.0);
            }
            cal {
               float freq = get_frequency(frame1);
            }
            """,
            r"Variable 'freq' already declared in OpenPulse scope",
            r"Error at line 11, column 15",
        ),
        (
            """
            OPENQASM 3.0;
            defcalgrammar "openpulse";
            cal {
               port d0;
               float freq = 1.0;
               frame frame1 = newframe(d0, 5.0e9, 1.0);
            }
            defcal test_waveform $0 {
               barrier $0;
               barrier frame1, frame2;
            }
            """,
            r"Frame 'frame2' not found in openpulse scope",
            r"Error at line 9, column 15",
        ),
        (
            """
            OPENQASM 3.0;
            defcalgrammar "openpulse";
            cal {
               int wf2;
               wf2 = gaussian(1.0 + 2.0im, 100ns, 5.0ns);
            }
            """,
            r"Invalid return type 'IntType' for function 'gaussian'",
            r"Error at line 7, column 15",
        ),
        (
            """
            OPENQASM 3.0;
            defcalgrammar "openpulse";
            cal {
               int wf2;
               complex amp;
               amp = sqrt(1.0 + 2.0im);
               int a;
               a = 2.0;
               port d0;
               frame fr1;
               fr1 = newframe(d0, 100.0, 5.0);
               wf2 = newframe(d0, 100.0, 5.0);
            }
            """,
            r"Invalid return type 'IntType' for function 'newframe'",
            r"Error at line 14, column 15",
        ),
        (
            """
            OPENQASM 3.0;
            defcalgrammar "openpulse";
            cal {
               waveform wf1 = capture_v1(frame1, 100ns);
            }
            """,
            r"Invalid waveform function 'capture_v1'",
            r"Error at line 6, column 15",
        ),
        (
            """
            OPENQASM 3.0;
            defcalgrammar "openpulse";
            cal {
               port d0;
               frame fr1 =  newframe(d0, 100.0, 5.0);
               set_frequency(2, 100.0);
            }
            """,
            r"Invalid frame argument 'IntegerLiteral' in set_frequency function",
            r"Error at line 4, column 15",
        ),
        (
            """
            OPENQASM 3.0;
            defcalgrammar "openpulse";
            cal {
                qubit q0;
            }
            """,
            r"Unsupported statement of type <class 'openqasm3.ast.QubitDeclaration'>",
            r"Error at line 6, column 16",
        ),
        (
            """
            OPENQASM 3.0;
            defcalgrammar "openpulse";
            float freq1 = 1.0;
            defcal test_waveform $0 {
                port d0;
                frame fr1 = newframe(d0, 100.0, 5.0);
                float freq = get_frequency(fr1);
                return freq1;
            }
            """,
            r"Return Variable 'freq1' not declared in OpenPulse scope",
            r"Error at line 5, column 16",
        ),
    ],
)  # pylint: disable-next= too-many-arguments
def test_pulse_general_error(qasm_code, error_message, error_span, caplog):
    with pytest.raises(ValidationError) as err:
        with caplog.at_level("ERROR"):
            loads(qasm_code).unroll()
    assert error_message in str(err.value)
    assert error_span in caplog.text


@pytest.mark.parametrize(
    "qasm_code,error_message,error_span",
    [
        (
            """
            OPENQASM 3.0;
            defcalgrammar "openpulse";
            defcal test_waveform $0 {
                port d0;
                frame fr1 = newframe(d0, 100.0, 5.0);
            }
            """,
            r"Frame initialization in defcal block is not allowed",
            r"Error at line 3, column 28",
        ),
        (
            """
            OPENQASM 3.0;
            defcalgrammar "openpulse";
            cal {
                port d0;
                frame fr1 = newframe(d0, 100.0, 5.0);
            }
            defcal test_waveform $0 {
                waveform wf2 = capture_v3(fr1, 100ns);
                complex[float[32]] wf1 = capture_v1(fr1, wf2);
                int wf3 = capture_v4(fr1, 100ns);
                play(fr1, gaussian(1.0 + 2.0im, 100ns, 5.0ns));
            }
            cal {
                play(fr1, gaussian(1.0 + 2.0im, 100ns, 5.0ns));
            }
            """,
            r"Play function is only allowed in defcal block",
            r"Error at line 2, column 16",
        ),
    ],
)  # pylint: disable-next= too-many-arguments
def test_pulse_input_error(qasm_code, error_message, error_span, caplog):
    with pytest.raises(ValidationError) as err:
        with caplog.at_level("ERROR"):
            loads(
                qasm_code,
                frame_in_def_cal=False,
                play_in_cal_block=False,
                implicit_phase_tracking=True,
            ).unroll()
    assert error_message in str(err.value)
    assert error_span in caplog.text
