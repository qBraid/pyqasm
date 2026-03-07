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
 play(driveframe, constant(amp, 0.0001s));
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
 waveform wf1 = gaussian_square(amp, 1024.0ns, 128.0ns, 32.0ns);
 waveform wf2 = gaussian_square(amp, 1024.0ns, 128.0ns, 32.0ns);
 frame temp_frame = newframe(d1, get_frequency(frame0), get_phase(frame0));
 play(frame0, wf1);
 play(temp_frame, wf2);
}
"""
    module = loads(qasm_str)
    module.unroll()
    check_unrolled_qasm(dumps(module), expected_qasm)


def test_geometric_gate():
    qasm_str = """
    OPENQASM 3.0;
	 defcalgrammar "openpulse";
	 qubit q;
	 cal {
		 port dq;
		 float fq_01 = 5e9; // hardcode or pull from some function
		 float anharm = 300e6; // hardcode or pull from some function
		 frame frame_01 = newframe(dq, fq_01, 0.0);
		 frame frame_12 = newframe(dq, fq_01 + anharm, 0.0);
	 }

	 defcal geo_gate(angle[32] theta) q {
		 // theta: rotation angle (about z-axis) on Bloch sphere
		 // Assume we have calibrated 0->1 pi pulses and 1->2 pi pulse
		 // envelopes (no sideband)
		 waveform X_01 = gaussian(1.0 + 2.0im, 10.0ns, 0.1ns);
		 waveform X_12 = gaussian(1.0 + 2.0im, 10.0ns, 0.1ns);
		 float[32] a = sin(theta/2);
		 float[32] b = sqrt(1-a**2);

		 // Double-tap
		 play(frame_01, scale(X_01, a));
		 play(frame_12, scale(X_12, b));
		 play(frame_01, scale(X_01, a));
		 play(frame_12, scale(X_12, b));
	 }
	 geo_gate(pi/2) q;

    """

    expected_qasm = """OPENQASM 3.0;
qubit[1] __PYQASM_QUBITS__;
defcalgrammar "openpulse";
cal {
 port dq;
 float[32] fq_01 = 5000000000.0;
 float anharm = 300000000.0;
 frame frame_01 = newframe(dq, 5000000000.0, 0.0, 0ns);
 frame frame_12 = newframe(dq, 5300000000.0, 0.0, 0ns);
}
defcal geo_gate(angle[32] theta) q {
 waveform X_01 = gaussian(1.0 + 2.0im, 10.0ns, 0.1ns);
 waveform X_12 = gaussian(1.0 + 2.0im, 10.0ns, 0.1ns);
 float[32] a = sin(theta / 2);
 float[32] b = sqrt(1 - a ** 2);
 play(frame_01, scale(X_01, a));
 play(frame_12, scale(X_12, b));
 play(frame_01, scale(X_01, a));
 play(frame_12, scale(X_12, b));
}
geo_gate(1.5707963267948966) __PYQASM_QUBITS__[0];
"""
    module = loads(qasm_str)
    module.unroll()
    check_unrolled_qasm(dumps(module), expected_qasm)


def test_neutral_atom_gate():
    qasm_str = """
    OPENQASM 3.0;
    defcalgrammar "openpulse";

    // Raman transition detuning delta from the  5S1/2 to 5P1/2 transition
    const float delta = 100e6;

    // Hyperfine qubit frequency
    const float qubit_freq = 6.0e9;

    // Positional frequencies for the AODS to target the specific qubit
    const float q1_pos_freq = 5.0e9;
    const float q2_pos_freq = 5.0e9;
    const float q3_pos_freq = 5.0e9;

    // Calibrated amplitudes and durations for the Raman pulses supplied via the AOD envelopes
    const complex[float[32]] q1_π_half_amp = 1.0 + 2.0im;
    const complex[float[32]] q2_π_half_amp = 1.0 + 2.0im;
    const complex[float[32]] q3_π_half_amp = 1.0 + 2.0im;
    const duration pi_half_time = 10.0ns;

    // Time-proportional phase increment
    const float tppi_1 = 1.0;
    const float tppi_2 = 1.0;
    const float tppi_3 = 1.0;

    cal {
        port eom_a_port;
        port eom_b_port;
        port aod_port;

        // Define the Raman frames, which are detuned by an amount delta from the  5S1/2 to 5P1/2 transition
        // and offset from each other by the qubit_freq
        frame raman_a_frame = newframe(eom_a_port, delta, 0.0);
        frame raman_b_frame = newframe(eom_b_port, delta-qubit_freq, 0.0);
        const complex[float[32]] raman_a_amp = 1.0 + 2.0im;
        const complex[float[32]] raman_b_amp = 1.0 + 2.0im;

        // Three frames to phase track each qubit's rotating frame of reference at it's frequency
        frame q1_frame = newframe(aod_port, qubit_freq, 0.0);
        frame q2_frame = newframe(aod_port, qubit_freq, 0.0);
        frame q3_frame = newframe(aod_port, qubit_freq, 0.0);

        // Generic gaussian envelope
        waveform pi_half_sig = gaussian(1.0 + 2.0im, pi_half_time, 100ns);

        // Waveforms ultimately supplied to the AODs. We mix our general Gaussian pulse with a sine wave to
        // put a sideband on the outgoing pulse. This helps us target the qubit position while maintainig the
        // desired Rabi rate.
        waveform q1_pi_half_sig = mix(pi_half_sig, sine(q1_π_half_amp, pi_half_time, q1_pos_freq-qubit_freq, 0.0));
        waveform q2_pi_half_sig = mix(pi_half_sig, sine(q2_π_half_amp, pi_half_time, q2_pos_freq-qubit_freq, 0.0));
        waveform q3_pi_half_sig = mix(pi_half_sig, sine(q3_π_half_amp, pi_half_time, q3_pos_freq-qubit_freq, 0.0));
    }
    // π/2 pulses on all three qubits
    defcal rx(angle theta) $1, $2, $3 {
          // Simultaneous π/2 pulses
          play(raman_a_frame, constant(raman_a_amp, pi_half_time));
          play(raman_b_frame, constant(raman_b_amp, pi_half_time));
          play(q1_frame, q1_pi_half_sig);
          play(q2_frame, q2_pi_half_sig);
          play(q3_frame, q3_pi_half_sig);
    }
    // π/2 pulse on only qubit $2
    defcal rx(angle theta) $2 {
        play(raman_a_frame, constant(raman_a_amp, pi_half_time));
        play(raman_b_frame, constant(raman_b_amp, pi_half_time));
        play(q2_frame, q2_pi_half_sig);
    }
    // Ramsey sequence on qubit 1 and 3, Hahn echo on qubit 2
    for duration tau_val in [1us:1us:2us] {

        // First π/2 pulse
        rx(pi/2) $1, $2, $3;
        // First half of evolution time
        cal {
            delay[tau_val/2] raman_a_frame, raman_b_frame, q1_frame, q2_frame, q3_frame;
        }
        // Hahn echo π pulse composed of two π/2 pulses
        for int ct in [0:1]{
            rx(π/2) $2;
        }
        cal {
            // Align all frames
            barrier raman_a_frame, raman_b_frame, q1_frame, q2_frame, q3_frame;

            // Second half of evolution time
            delay[tau_val/2] raman_a_frame, raman_b_frame, q1_frame, q2_frame, q3_frame;

            // Time-proportional phase increment signals different amount
            shift_phase(q1_frame, tppi_1 * tau_val);
            shift_phase(q2_frame, tppi_2 * tau_val);
            shift_phase(q3_frame, tppi_3 * tau_val);
        }
        
        // Second π/2 pulse
        rx(π/2) $1, $2, $3;
    }
    """

    expected_qasm = """OPENQASM 3.0;
qubit[4] __PYQASM_QUBITS__;
defcalgrammar "openpulse";
cal {
 port eom_a_port;
 port eom_b_port;
 port aod_port;
 frame raman_a_frame = newframe(eom_a_port, 100000000.0, 0.0, 0ns);
 frame raman_b_frame = newframe(eom_b_port, -5900000000.0, 0.0, 0ns);
 const complex[float[32]] raman_a_amp = 1.0 + 2.0im;
 const complex[float[32]] raman_b_amp = 1.0 + 2.0im;
 frame q1_frame = newframe(aod_port, 6000000000.0, 0.0, 0ns);
 frame q2_frame = newframe(aod_port, 6000000000.0, 0.0, 0ns);
 frame q3_frame = newframe(aod_port, 6000000000.0, 0.0, 0ns);
 waveform pi_half_sig = gaussian(1.0 + 2.0im, 10.0ns, 100.0ns);
 waveform q1_pi_half_sig = mix(pi_half_sig, sine(1.0 + 2.0im, 10.0ns, -1000000000.0, 0.0));
 waveform q2_pi_half_sig = mix(pi_half_sig, sine(1.0 + 2.0im, 10.0ns, -1000000000.0, 0.0));
 waveform q3_pi_half_sig = mix(pi_half_sig, sine(1.0 + 2.0im, 10.0ns, -1000000000.0, 0.0));
}
defcal rx(angle theta) $1, $2, $3 {
 play(raman_a_frame, constant(raman_a_amp, pi_half_time));
 play(raman_b_frame, constant(raman_b_amp, pi_half_time));
 play(q1_frame, q1_pi_half_sig);
 play(q2_frame, q2_pi_half_sig);
 play(q3_frame, q3_pi_half_sig);
}
defcal rx(angle theta) $2 {
 play(raman_a_frame, constant(raman_a_amp, pi_half_time));
 play(raman_b_frame, constant(raman_b_amp, pi_half_time));
 play(q2_frame, q2_pi_half_sig);
}
rx(1.5707963267948966) __PYQASM_QUBITS__[1], __PYQASM_QUBITS__[2], __PYQASM_QUBITS__[3];
cal {
 delay[500.0ns] raman_a_frame, raman_b_frame, q1_frame, q2_frame, q3_frame;
}
rx(1.5707963267948966) __PYQASM_QUBITS__[2];
rx(1.5707963267948966) __PYQASM_QUBITS__[2];
cal {
 barrier raman_a_frame, raman_b_frame, q1_frame, q2_frame, q3_frame;
 delay[500.0ns] raman_a_frame, raman_b_frame, q1_frame, q2_frame, q3_frame;
 shift_phase(q1_frame, 0.9735361584457891);
 shift_phase(q2_frame, 0.9735361584457891);
 shift_phase(q3_frame, 0.9735361584457891);
}
rx(1.5707963267948966) __PYQASM_QUBITS__[1], __PYQASM_QUBITS__[2], __PYQASM_QUBITS__[3];
rx(1.5707963267948966) __PYQASM_QUBITS__[1], __PYQASM_QUBITS__[2], __PYQASM_QUBITS__[3];
cal {
 delay[1000.0ns] raman_a_frame, raman_b_frame, q1_frame, q2_frame, q3_frame;
}
rx(1.5707963267948966) __PYQASM_QUBITS__[2];
rx(1.5707963267948966) __PYQASM_QUBITS__[2];
cal {
 barrier raman_a_frame, raman_b_frame, q1_frame, q2_frame, q3_frame;
 delay[1000.0ns] raman_a_frame, raman_b_frame, q1_frame, q2_frame, q3_frame;
 shift_phase(q1_frame, 2.920608475337346);
 shift_phase(q2_frame, 2.920608475337346);
 shift_phase(q3_frame, 2.920608475337346);
}
rx(1.5707963267948966) __PYQASM_QUBITS__[1], __PYQASM_QUBITS__[2], __PYQASM_QUBITS__[3];
"""
    module = loads(qasm_str)
    module.unroll()
    check_unrolled_qasm(dumps(module), expected_qasm)


def test_multiplexed_readout_and_capture():
    qasm_str = """
    OPENQASM 3.0;
    defcalgrammar "openpulse";

    const duration electrical_delay = 100ns;
    const float q0_ro_freq = 5.0e9;
    const float q1_ro_freq = 6.0e9;

    cal {
      // the transmission/captures ports are the same for $0 and $1
      port ro_tx;
      port ro_rx;

      // readout stimulus and capture frames of different frequencies
      frame q0_stimulus_frame = newframe(ro_tx, q0_ro_freq, 0.0);
      frame q0_capture_frame = newframe(ro_rx, q0_ro_freq, 0.0);
      frame q1_stimulus_frame = newframe(ro_tx, q1_ro_freq, 0.0);
      frame q1_capture_frame = newframe(ro_rx, q1_ro_freq, 0.0);
    }
    defcal multiplexed_readout_and_capture $0, $1 -> bit[2] {
        bit[2] b;
        int sairam;
        waveform q0_ro_wf = constant(1.0 + 2.0im, 100ns);
        waveform q1_ro_wf = constant(1.0 + 2.0im, 100ns);
      
        // multiplexed readout
        play(q0_stimulus_frame, q0_ro_wf);
        play(q1_stimulus_frame, q1_ro_wf);
        
        // simple boxcar kernel
        waveform ro_kernel = constant(1.0 + 2.0im, 100ns);
        barrier q0_stimulus_frame, q1_stimulus_frame, q0_capture_frame, q1_capture_frame;
        delay[electrical_delay] q0_capture_frame, q1_capture_frame;
        b[0] = capture_v2(q0_capture_frame, ro_kernel);
        b[1] = capture_v2(q1_capture_frame, ro_kernel);
        return b;
    }

    multiplexed_readout_and_capture $0, $1;
    """
    expected_qasm = """OPENQASM 3.0;
qubit[2] __PYQASM_QUBITS__;
defcalgrammar "openpulse";
cal {
 port ro_tx;
 port ro_rx;
 frame q0_stimulus_frame = newframe(ro_tx, 5000000000.0, 0.0, 0ns);
 frame q0_capture_frame = newframe(ro_rx, 5000000000.0, 0.0, 0ns);
 frame q1_stimulus_frame = newframe(ro_tx, 6000000000.0, 0.0, 0ns);
 frame q1_capture_frame = newframe(ro_rx, 6000000000.0, 0.0, 0ns);
}
defcal multiplexed_readout_and_capture() $0, $1 -> bit[2] {
 bit[2] b;
 int sairam;
 waveform q0_ro_wf = constant(1.0 + 2.0im, 100.0ns);
 waveform q1_ro_wf = constant(1.0 + 2.0im, 100.0ns);
 play(q0_stimulus_frame, q0_ro_wf);
 play(q1_stimulus_frame, q1_ro_wf);
 waveform ro_kernel = constant(1.0 + 2.0im, 100.0ns);
 barrier q0_stimulus_frame, q1_stimulus_frame, q0_capture_frame, q1_capture_frame;
 delay[electrical_delay] q0_capture_frame, q1_capture_frame;
 b[0] = capture_v2(q0_capture_frame, ro_kernel);
 b[1] = capture_v2(q1_capture_frame, ro_kernel);
 return b;
}
multiplexed_readout_and_capture __PYQASM_QUBITS__[0], __PYQASM_QUBITS__[1];
"""
    module = loads(qasm_str)
    module.unroll()
    check_unrolled_qasm(dumps(module), expected_qasm)
