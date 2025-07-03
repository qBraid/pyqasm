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

# pylint: disable=invalid-name

"""
Script demonstrating how to unroll a QASM 3 program using pyqasm.

"""

from pyqasm import dumps, loads

complex_example = """
OPENQASM 3;
defcalgrammar "openpulse";

cal {
    extern port q0_drive;
    extern port q0_readout;
    extern frame q0_frame = newframe(q0_drive, 5.2e9, 0.0);
    extern frame q0_readout_frame = newframe(q0_readout, 6.1e9, 0.0);
    extern frame q0_acquire = newframe(q0_readout, 6.1e9, 0.0);
}

const duration pulse_length = 60ns;
const duration meas_length = 800ns;
const duration buffer_time = 20ns;

waveform gaussian_pulse = gaussian(pulse_length, 0.3, 10ns);
waveform drag_pulse = gaussian(pulse_length, 0.25, 10ns, alpha=0.5);
waveform meas_pulse = constant(meas_length, 0.2);
waveform zero_pad = constant(buffer_time, 0.0);

defcal rb_sequence $q0 {
    for int i in [0:20] {
        bit[2] selector = random[2];
        
        switch(selector) {
            case 0: play(q0_frame, gaussian_pulse);
            case 1: play(q0_frame, drag_pulse);
            case 2: {
                play(q0_frame, gaussian_pulse);
                delay[pulse_length] q0_frame;
                play(q0_frame, drag_pulse);
            }
            default: {
                play(q0_frame, drag_pulse);
                delay[pulse_length] q0_frame;
                play(q0_frame, gaussian_pulse);
            }
        }
        delay[buffer_time] q0_frame;
    }
    
    play(q0_readout_frame, meas_pulse);
    capture(q0_acquire, meas_pulse);
    
    box {
        bit result = get_measure(q0_acquire);
        stream result;
        if (result) {
            delay[1ms] q0_frame;
        }
    }
}

qubit[1] q;
bit[1] c;

rb_sequence q[0];
c[0] = measure q[0];
"""

simple_example = """
OPENQASM 3;
defcalgrammar "openpulse";

cal {
    port tx_port;
    frame tx_frame = newframe(tx_port2, 7883050000.0, 0);
    waveform readout_waveform_wf = constant(5e-06, 0.03);
    for int shot in [0:499] {
        play(readout_waveform_wf, tx_frame2);
        barrier tx_frame2;
    }
}
"""

# cal {
#    extern drag(complex[size] amp, duration l, duration sigma, float[size] beta) -> waveform;
#    extern gaussian_square(complex[size] amp, duration l, duration square_width, duration sigma) -> waveform;

#    extern port q0;
#    extern port q1;

#    frame q0_frame = newframe(q0, q0_freq, 0);
#    frame q1_frame = newframe(q1, q1_freq, 0);
# }

example = """
OPENQASM 3;
defcalgrammar "openpulse";

const float q0_freq = 5.0e9;
const float q1_freq = 5.1e9;

defcal rz(angle theta, angle theta) $0 {
   shift_phase(q0_frame, theta);
}

defcal rz(angle theta) $1 {
   shift_phase(q1_frame, theta);
}

defcal sx $0 {
   waveform sx_wf = drag(0.2+0.1im, 160dt, 40dt, 0.05);
   play(q0_frame, sx_wf);
}

defcal sx $1 {
   waveform sx_wf = drag(0.1+0.05im, 160dt, 40dt, 0.1);
   play(q1_frame, sx_wf);
}
"""

program = loads(example)

program.unroll()

print(dumps(program))
