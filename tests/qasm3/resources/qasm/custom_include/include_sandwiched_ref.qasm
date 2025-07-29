OPENQASM 3.0;
include "stdgates.inc";

gate custom(a) p, q {
    h p;
    z q;
    rx(a) p;
    cx p,q;
}

qubit[5] q;

custom(0.1+1) q[0], q[1];