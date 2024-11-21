OPENQASM 3;
include "stdgates.inc";

qubit[1] q;
bit[1] c;

// bad code
h q[2];

c = measure q;