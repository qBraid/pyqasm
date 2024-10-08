OPENQASM 3.0;
include "stdgates.inc";

gate custom2(g) s {
    h s;
    rz(g) s;
}
gate custom(a,b,c) p, q{
    custom2(a) q;
    h p;
    cx p,q;
    rx(a) q;
    ry(0.5/0.1) q;
}

qubit[2] q;
custom(2 + 3 - 1/5, 0.1, 0.3) q[0], q[1];
