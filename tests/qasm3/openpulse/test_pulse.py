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
Module containing unit tests for the pulse operation.

"""

from pyqasm.entrypoint import dumps, loads
from tests.utils import check_unrolled_qasm


def test_qubit_spectroscopy():
    qasm_str = """
    OPENQASM 3.0;
    defcalgrammar "openpulse";
    
    complex[float[32]] amp = 1.0 + 2.0im;
    cal {
       port d0;
       frame driveframe = newframe(d0, 5.0e9, 0.0);
       waveform wf = gaussian(amp, 16ns, 4ns);
    }
    
    const float frequency_start = 4.5e9;
    const float frequency_step = 1e6;
    const int frequency_num_steps = 3;
    
    defcal saturation_pulse $0 {
       play(driveframe, constant(amp, 100e-6s));
    }
    
    cal {
       set_frequency(driveframe, frequency_start);
    }
    
    for int i in [1:frequency_num_steps] {
       cal {
           shift_frequency(driveframe, frequency_step);
       }
       saturation_pulse $0;
    }
    """

    expected_qasm = """OPENQASM 3.0;
qubit[1] __PYQASM_QUBITS__;
defcalgrammar "openpulse";
cal {
 port d0;
 frame driveframe = newframe(d0, 5000000000.0, 0.0, 0ns);
 waveform wf = gaussian(1.0 + 2.0im, 16.0ns, 4.0ns);
}
defcal saturation_pulse() $0 {
 play(driveframe, constant(1.0 + 2.0im, 100000.0ns));
}
cal {
 set_frequency(driveframe, 4500000000.0);
}
cal {
 shift_frequency(driveframe, 4501000000.0);
}
saturation_pulse __PYQASM_QUBITS__[0];
cal {
 shift_frequency(driveframe, 4502000000.0);
}
saturation_pulse __PYQASM_QUBITS__[0];
cal {
 shift_frequency(driveframe, 4503000000.0);
}
saturation_pulse __PYQASM_QUBITS__[0];
"""
    module = loads(qasm_str)
    module.unroll()
    check_unrolled_qasm(dumps(module), expected_qasm)


def test_rabi_time_spectroscopy():
    qasm_str = """
    OPENQASM 3.0;
    defcalgrammar "openpulse";
    qubit[4] q;
    const duration pulse_length_start = 20ns;
    const duration pulse_length_step = 1ns;
    const int pulse_length_num_steps = 3;
    cal {
       port d0;
       frame driveframe = newframe(d0, 5.0e9, 0.0);
    }
    for int i in [1:pulse_length_num_steps] {
        duration pulse_length = pulse_length_start + (i-1)*pulse_length_step;
        duration sigma = pulse_length / 4;
        // since we are manipulating pulse lengths it is easier to define and play the waveform in a `cal` block
        cal {
            waveform wf = gaussian(1.0 + 2.0im, pulse_length, sigma);
            // assume frame can be linked from a vendor supplied `cal` block
            play(driveframe, wf);
        }
        measure $0;
    }
    """

    expected_qasm = """OPENQASM 3.0;
qubit[4] __PYQASM_QUBITS__;
defcalgrammar "openpulse";
cal {
 port d0;
 frame driveframe = newframe(d0, 5000000000.0, 0.0, 0ns);
}
cal {
 waveform wf = gaussian(1.0 + 2.0im, 20.0ns, 5.0ns);
 play(driveframe, wf);
}
measure __PYQASM_QUBITS__[0];
cal {
 waveform wf = gaussian(1.0 + 2.0im, 21.0ns, 5.25ns);
 play(driveframe, wf);
}
measure __PYQASM_QUBITS__[0];
cal {
 waveform wf = gaussian(1.0 + 2.0im, 22.0ns, 5.5ns);
 play(driveframe, wf);
}
measure __PYQASM_QUBITS__[0];
"""
    module = loads(qasm_str)
    module.unroll()
    check_unrolled_qasm(dumps(module), expected_qasm)


def test_cross_resonance():
    qasm_str = """
	OPENQASM 3.0;
	defcalgrammar "openpulse";

	cal {
		// Access globally (or externally) defined ports
		port d0;
		port d1;
		frame frame0 = newframe(d0, 5.0e9, 0.0);
		const complex[float[32]] amp = 1.0 + 2.0im;
	}

	defcal cross_resonance $0, $1 {
		waveform wf1 = gaussian_square(amp, 1024ns, 128ns, 32ns);
		waveform wf2 = gaussian_square(amp, 1024ns, 128ns, 32ns);

		/*** Do pre-rotation ***/

		// generate new frame for second drive that is locally scoped
		// initialized to time at the beginning of `cross_resonance`
		frame temp_frame = newframe(d1, get_frequency(frame0), get_phase(frame0));

		play(frame0, wf1);
		play(temp_frame, wf2);

		/*** Do post-rotation ***/

	}
    """

    expected_qasm = """OPENQASM 3.0;
qubit[2] __PYQASM_QUBITS__;
defcalgrammar "openpulse";
cal {
 port d0;
 port d1;
 frame frame0 = newframe(d0, 5000000000.0, 0.0, 0ns);
 const complex[float[32]] amp = 1.0 + 2.0im;
}
defcal cross_resonance() $0, $1 {
 waveform wf1 = gaussian_square(1.0 + 2.0im, 1024.0ns, 128.0ns, 32.0ns);
 waveform wf2 = gaussian_square(1.0 + 2.0im, 1024.0ns, 128.0ns, 32.0ns);
 frame temp_frame = newframe(d1, FloatLiteral(span=None, value=5000000000.0), FloatLiteral(span=None, value=0.0), 0ns);
 play(frame0, wf1);
 play(temp_frame, wf2);
}
"""
    module = loads(qasm_str)
    module.unroll()
    check_unrolled_qasm(dumps(module), expected_qasm)
