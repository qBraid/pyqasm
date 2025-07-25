OPENQASM 3.0;
include "stdgates.inc";

const int A = 5; 
float b = 2.34; 
array[float[32], 3, 2] c = {{1.1, 1.2}, {2.1,2.2}, {3.1, 3.2}}; 
gate d(n) a { h a; x a; rx(n) a; }

qubit[A] q;

for int i in [0:A-1] {
    float theta = c[i % 3][i % 2];  
    d(theta) q[i];
}
