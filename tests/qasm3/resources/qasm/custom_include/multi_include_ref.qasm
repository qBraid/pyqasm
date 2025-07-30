OPENQASM 3.0;
include "stdgates.inc";


const int A = 5; 
float b = 2.34; 
array[float[32], 3, 2] c = {{1.1, 1.2}, {2.1,2.2}, {3.1, 3.2}}; 
gate d(n) a { h a; x a; rx(n) a; }


gate custom(a) p, q {
    h p;
    z q;
    rx(a) p;
    cx p,q;
}

qubit[A] q;
custom(0.1+1) q[0], q[1];
custom(0.5) q[2], q[3];
custom(0.5) q[3], q[4];
