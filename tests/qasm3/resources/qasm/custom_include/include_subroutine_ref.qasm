OPENQASM 3.0;
include "stdgates.inc";

def routine(qubit[3] q) {
    for int[16] i in [0:2] {
        h q[i];
        x q[i];
    }
    cx q[0], q[1];
}

qubit[3] q;
routine(q);