OPENQASM 3.0;
include "stdgates.inc";
include "vars.inc";
include "custom_gate_def.qasm";

qubit[A] q;
custom(0.1+1) q[0], q[1];
custom(0.5) q[2], q[3];
custom(0.5) q[3], q[4];
