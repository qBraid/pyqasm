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