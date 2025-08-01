OPENQASM 3.0;
include "stdgates.inc";

qubit[5] q;
include "custom_gate_def.qasm";
custom(0.1+1) q[0], q[1];
