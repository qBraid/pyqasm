OPENQASM 3;
include "stdgates.inc";

gate custom(a) p, q {
    h p;
    z q;
    rx(a) p;
    cx p,q;
}

qubit[2] q;
custom(0.1+1) q[0], q[1];