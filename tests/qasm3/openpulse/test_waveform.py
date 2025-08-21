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
Module containing unit tests for the waveform.

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
            float amp = 1.0;
            cal {
                waveform wf1 = drag(amp, 100ns, 20ns, 0.05);
            }
            """,
            r"Invalid amplitude type 'FloatType' for 'amp' in 'drag'",
            r"Error at line 2, column 31",
        ),
        (
            """
            OPENQASM 3.0;
            defcalgrammar "openpulse";
            complex[float[32]] amp;
            cal {
                waveform wf1 = drag(amp, 100ns, 20ns, 0.05);
            }
            """,
            r"Uninitialized amplitude 'amp' in 'drag'",
            r"Error at line 2, column 31",
        ),
        (
            """
            OPENQASM 3.0;
            defcalgrammar "openpulse";
            cal {
                waveform wf1 = drag(1.0, 100ns, 20ns, 0.05);
            }
            """,
            r"Invalid amplitude initialization 'FloatLiteral' in 'drag'",
            r"Error at line 2, column 31",
        ),
        (
            """
            OPENQASM 3.0;
            defcalgrammar "openpulse";
            cal {
                waveform wf1 = drag(pi/2, 100ns, 20ns, 0.05);
            }
            """,
            r"Invalid amplitude value '1.5707963267948966' in 'drag'",
            r"Error at line 2, column 31",
        ),
        (
            """
            OPENQASM 3.0;
            defcalgrammar "openpulse";
            duration l;
            cal {
                waveform wf1 = drag(1.0 + 2.0im, l, 20ns, 0.05);
            }
            """,
            r"Uninitialized 'Total duration' 'l' in 'drag'",
            r"Error at line 2, column 31",
        ),
        (
            """
            OPENQASM 3.0;
            defcalgrammar "openpulse";
            float l;
            cal {
                waveform wf1 = drag(1.0 + 2.0im, l, 20ns, 0.05);
            }
            """,
            r"Invalid 'Total duration' type 'FloatType' for 'l' in 'drag'",
            r"Error at line 2, column 31",
        ),
        (
            """
            OPENQASM 3.0;
            defcalgrammar "openpulse";
            cal {
                waveform wf1 = drag(1.0 + 2.0im, 100, 20ns, 0.05);
            }
            """,
            r"Invalid 'Total duration' initialization 'IntegerLiteral' in 'drag'",
            r"Error at line 2, column 31",
        ),
        (
            """
            OPENQASM 3.0;
            defcalgrammar "openpulse";
            duration l = 20ns;
            cal {
                waveform wf1 = drag(1.0 + 2.0im, 100ns, l, 0.05);
                waveform wf2 = gaussian_square(1.0 + 2.0im, 100ns, 20ns, -20ns);
            }
            """,
            r"Standard deviation value '-20.0' in 'gaussian_square' cannot be negative",
            r"Error at line 3, column 31",
        ),
        (
            """
            OPENQASM 3.0;
            defcalgrammar "openpulse";
            duration l = 20ns;
            cal {
                waveform wf1 = drag(1.0 + 2.0im, 100ns, l, 0.05);
                duration d = -20ns;
                waveform wf2 = gaussian_square(1.0 + 2.0im, 100ns, 20ns, d);
            }
            """,
            r"Standard deviation value '-20.0' in 'gaussian_square' cannot be negative",
            r"Error at line 4, column 31",
        ),
        (
            """
            OPENQASM 3.0;
            defcalgrammar "openpulse";
            cal {
                waveform wf1 = gaussian(1.0 + 2.0im, 100ns, -20ns);
            }
            """,
            r"Standard deviation value '-20.0' in 'gaussian' cannot be negative",
            r"Error at line 2, column 31",
        ),
        (
            """
            OPENQASM 3.0;
            defcalgrammar "openpulse";
            cal {
                waveform wf1 = drag(1.0 + 2.0im, 100ns, -20ns, 0.05);
            }
            """,
            r"Standard deviation value '-20.0' in 'drag' cannot be negative",
            r"Error at line 2, column 31",
        ),
        (
            """
            OPENQASM 3.0;
            defcalgrammar "openpulse";
            int l = 20;
            cal {
                waveform wf1 = drag(1.0 + 2.0im, 100ns, 20ns, l);
            }
            """,
            r"Invalid 'Y correction amplitude' type 'IntType' for 'l' in 'drag'",
            r"Error at line 2, column 31",
        ),
        (
            """
            OPENQASM 3.0;
            defcalgrammar "openpulse";
            float l;
            cal {
                waveform wf1 = drag(1.0 + 2.0im, 100ns, 20ns, l);
            }
            """,
            r"Uninitialized 'Y correction amplitude' 'l' in 'drag'",
            r"Error at line 2, column 31",
        ),
        (
            """
            OPENQASM 3.0;
            defcalgrammar "openpulse";
            float beta = 0.05;
            cal {
                waveform wf1 = drag(1.0 + 2.0im, 100ns, 20ns, beta);
                waveform wf2 = drag(1.0 + 2.0im, 100ns, 20ns, -2);
            }
            """,
            r"Invalid 'Y correction amplitude' value '2' in 'drag'",
            r"Error at line 3, column 31",
        ),
        (
            """
            OPENQASM 3.0;
            defcalgrammar "openpulse";
            cal {
                waveform wf1 = drag(1.0 + 2.0im, 100ns, 20ns, 2);
            }
            """,
            r"Invalid 'Y correction amplitude' initialization 'IntegerLiteral' in 'drag'",
            r"Error at line 2, column 31",
        ),
        (
            """
            OPENQASM 3.0;
            defcalgrammar "openpulse";
            cal {
                float freq = 5.0;
                angle phase = 1.0;
                waveform wf1 = sine(1.0 + 2.0im, 100ns, freq, phase);
                waveform wf2 = sine(1.0 + 2.0im, 100ns, 5, phase);
            }
            """,
            r"Invalid 'frequency' initialization 'IntegerLiteral' in 'sine",
            r"Error at line 5, column 31",
        ),
        (
            """
            OPENQASM 3.0;
            defcalgrammar "openpulse";
            int l = 5;
            cal {
                waveform wf1 = sine(1.0 + 2.0im, 100ns, l, 0.0);
            }
            """,
            r"Invalid 'frequency' type 'IntType' for 'l' in 'sine'",
            r"Error at line 2, column 31",
        ),
        (
            """
            OPENQASM 3.0;
            defcalgrammar "openpulse";
            float l;
            cal {
                waveform wf1 = sine(1.0 + 2.0im, 100ns, l, 0.0);
            }
            """,
            r"Uninitialized 'frequency' 'l' in 'sine'",
            r"Error at line 2, column 31",
        ),
        (
            """
            OPENQASM 3.0;
            defcalgrammar "openpulse";
            cal {
                waveform wf1 = sine(1.0 + 2.0im, 100ns, -2.0, 0.0);
                waveform wf2 = sine(1.0 + 2.0im, 100ns, -2, 0.0);
            }
            """,
            r"Invalid 'frequency' value '-2' in 'sine'",
            r"Error at line 3, column 31",
        ),
        (
            """
            OPENQASM 3.0;
            defcalgrammar "openpulse";
            cal {
                waveform wf1 = sine(1.0 + 2.0im, 100ns, 5.0, 5);
            }
            """,
            r"Invalid 'phase' initialization 'IntegerLiteral' in 'sine",
            r"Error at line 2, column 31",
        ),
        (
            """
            OPENQASM 3.0;
            defcalgrammar "openpulse";
            int l = 5;
            cal {
                waveform wf1 = sine(1.0 + 2.0im, 100ns, 5.0, l);
            }
            """,
            r"Invalid 'phase' type 'IntType' for 'l' in 'sine'",
            r"Error at line 2, column 31",
        ),
        (
            """
            OPENQASM 3.0;
            defcalgrammar "openpulse";
            angle l;
            cal {
                waveform wf1 = sine(1.0 + 2.0im, 100ns, 5.0, l);
            }
            """,
            r"Uninitialized 'phase' 'l' in 'sine'",
            r"Error at line 2, column 31",
        ),
        (
            """
            OPENQASM 3.0;
            defcalgrammar "openpulse";
            cal {
                waveform wf1 = sine(1.0 + 2.0im, 100ns, 5.0, -2.0);
                waveform wf2 = sine(1.0 + 2.0im, 100ns, 5.0, -2);
            }
            """,
            r"Invalid 'phase' value '-2' in 'sine'",
            r"Error at line 3, column 31",
        ),
        (
            """
            OPENQASM 3.0;
            defcalgrammar "openpulse";
            cal {
               int wf1 = 20;
               waveform wf2 = sine(1.0 + 2.0im, 100ns, 5.0, 0.0);
               waveform wfs = sum(wf1,wf2);
            }
            """,
            r"'wf1' should be a waveform variable",
            r"Error at line 4, column 30",
        ),
        (
            """
            OPENQASM 3.0;
            defcalgrammar "openpulse";
            cal {
               waveform wf2 = sine(1.0 + 2.0im, 100ns, 5.0, 0.0);
               waveform wfs = sum(cos(2),wf2);
            }
            """,
            r"Invalid function call 'cos' in 'sum'",
            r"Error at line 3, column 30",
        ),
        (
            """
            OPENQASM 3.0;
            defcalgrammar "openpulse";
            cal {
               waveform wf1 = sine(1.0 + 2.0im, 100ns, 5.0, 0.0);
               waveform wf2 = sine(1.0 + 2.0im, 100ns, 5.0, 0.0);
               waveform wf3 = mix(sum(wf1,wf2),wf2);
               waveform wfs = sum(2,wf2);
            }
            """,
            r"Invalid 'Waveform 1' initialization 'IntegerLiteral' in 'sum'",
            r"Error at line 5, column 30",
        ),
        (
            """
            OPENQASM 3.0;
            defcalgrammar "openpulse";
            cal {
               int wf1;
               angle p1 = 2.0;
               waveform wf2 = phase_shift(gaussian(1.0 + 2.0im, 100ns, 5.0ns),p1);
               waveform wfphase = phase_shift(wf1,pi/2);
            }
            """,
            r"'wf1' should be a waveform variable",
            r"Error at line 5, column 34",
        ),
        (
            """
            OPENQASM 3.0;
            defcalgrammar "openpulse";
            cal {
               int wf1;
               waveform wf2 = phase_shift(phase_shift(gaussian(1.0 + 2.0im, 10ns, 5.0ns),2.0),pi/2);
               waveform wfphase = phase_shift(cos(2),pi/2);
            }
            """,
            r"Invalid function call 'cos' in 'phase_shift'",
            r"Error at line 4, column 34",
        ),
        (
            """
            OPENQASM 3.0;
            defcalgrammar "openpulse";
            cal {
               int wf1;
               waveform wfphase = phase_shift(2,pi/2);
            }
            """,
            r"Invalid waveform argument 'IntegerLiteral' in 'phase_shift'",
            r"Error at line 3, column 34",
        ),
        (
            """
            OPENQASM 3.0;
            defcalgrammar "openpulse";
            int phase = 2;
            cal {
               waveform wf1 = gaussian(1.0 + 2.0im, 100ns, 5.0ns);
               waveform wfphase = phase_shift(wf1,phase);
            }
            """,
            r"Invalid phase type 'IntType' for 'phase' in 'phase_shift'",
            r"Error at line 3, column 34",
        ),
        (
            """
            OPENQASM 3.0;
            defcalgrammar "openpulse";
            angle phase;
            cal {
               waveform wf1 = gaussian(1.0 + 2.0im, 100ns, 5.0ns);
               waveform wfphase = phase_shift(wf1,phase);
            }
            """,
            r"Uninitialized phase in 'phase_shift'",
            r"Error at line 3, column 34",
        ),
        (
            """
            OPENQASM 3.0;
            defcalgrammar "openpulse";
            cal {
               waveform wf1 = gaussian(1.0 + 2.0im, 100ns, 5.0ns);
               waveform wfphase = phase_shift(wf1,-2);
            }
            """,
            r"Invalid phase value '-2' in 'phase_shift'",
            r"Error at line 3, column 34",
        ),
        (
            """
            OPENQASM 3.0;
            defcalgrammar "openpulse";
            cal {
               waveform wf1 = gaussian(1.0 + 2.0im, 100ns, 5.0ns);
               waveform wfphase = phase_shift(wf1,2);
            }
            """,
            r"Invalid phase initialization 'IntegerLiteral' in 'phase_shift'",
            r"Error at line 3, column 34",
        ),
        (
            """
            OPENQASM 3.0;
            defcalgrammar "openpulse";
            cal {
               int wf1;
               waveform wf2 = scale(gaussian(1.0 + 2.0im, 100ns, 5.0ns),2.0);
               waveform wfphase = scale(wf1,pi/2);
            }
            """,
            r"'wf1' should be a waveform variable",
            r"Error at line 4, column 34",
        ),
        (
            """
            OPENQASM 3.0;
            defcalgrammar "openpulse";
            cal {
               int wf1;
               waveform wfphase = scale(cos(2),pi/2);
            }
            """,
            r"Invalid function call 'cos' in 'scale'",
            r"Error at line 3, column 34",
        ),
        (
            """
            OPENQASM 3.0;
            defcalgrammar "openpulse";
            cal {
               int wf1;
               waveform wfphase = scale(2,pi/2);
            }
            """,
            r"Invalid waveform argument 'IntegerLiteral' in 'scale'",
            r"Error at line 3, column 34",
        ),
        (
            """
            OPENQASM 3.0;
            defcalgrammar "openpulse";
            int phase = 2;
            cal {
               waveform wf1 = gaussian(1.0 + 2.0im, 100ns, 5.0ns);
               waveform wfphase = scale(wf1,phase);
            }
            """,
            r"Invalid factor type 'IntType' for 'phase' in 'scale'",
            r"Error at line 3, column 34",
        ),
        (
            """
            OPENQASM 3.0;
            defcalgrammar "openpulse";
            float phase;
            cal {
               waveform wf1 = gaussian(1.0 + 2.0im, 100ns, 5.0ns);
               waveform wfphase = scale(wf1,phase);
            }
            """,
            r"Uninitialized factor in 'scale'",
            r"Error at line 3, column 34",
        ),
        (
            """
            OPENQASM 3.0;
            defcalgrammar "openpulse";
            cal {
               waveform wf1 = gaussian(1.0 + 2.0im, 100ns, 5.0ns);
               waveform wfphase = scale(wf1,-2);
            }
            """,
            r"Invalid factor value '-2' in 'scale'",
            r"Error at line 3, column 34",
        ),
        (
            """
            OPENQASM 3.0;
            defcalgrammar "openpulse";
            cal {
               waveform wf1 = gaussian(1.0 + 2.0im, 100ns, 5.0ns);
               waveform wfphase = scale(wf1,2);
            }
            """,
            r"Invalid factor initialization 'IntegerLiteral' in 'scale'",
            r"Error at line 3, column 34",
        ),
        (
            """
            OPENQASM 3.0;
            defcalgrammar "openpulse";
            cal {
               port d0;
               frame frame1 = newframe(d0, 5.0e9, 0.0);
               waveform wf1 = capture_v3(frame1, 100ns);
               int wf11 = capture_v4(frame1, 100ns);
               int wf2 = capture_v4(2, 100ns);
            }
            """,
            r"Invalid frame argument 'IntegerLiteral' in 'capture_v4'",
            r"Error at line 6, column 25",
        ),
        (
            """
            OPENQASM 3.0;
            defcalgrammar "openpulse";
            cal {
               port d0;
               waveform wf1 = gaussian(1.0 + 2.0im, 100ns, 5.0ns);
               complex[float[32]] cp1 = capture_v1(2, wf1);
            }
            """,
            r"Invalid frame argument 'IntegerLiteral' in 'capture_v1' function",
            r"Error at line 4, column 40",
        ),
        (
            """
            OPENQASM 3.0;
            defcalgrammar "openpulse";
            cal {
               port d0;
               frame frame1 = newframe(d0, 5.0e9, 0.0);
               complex[float[32]] cp1 = capture_v1(frame1, 2);
            }
            """,
            r"Invalid waveform argument 'IntegerLiteral' in 'capture_v1' function",
            r"Error at line 4, column 40",
        ),
        (
            """
            OPENQASM 3.0;
            defcalgrammar "openpulse";
            cal {
               port d0;
               frame frame1 = newframe(d0, 5.0e9, 0.0);
               int wf1 = 2;
               complex[float[32]] cp1 = capture_v1(frame1, wf1);
            }
            """,
            r"'wf1' should be a waveform variable",
            r"Error at line 5, column 40",
        ),
    ],
)  # pylint: disable-next= too-many-arguments
def test_waveform_error(qasm_code, error_message, error_span, caplog):
    with pytest.raises(ValidationError) as err:
        with caplog.at_level("ERROR"):
            loads(qasm_code).unroll()
    assert error_message in str(err.value)
    assert error_span in caplog.text
