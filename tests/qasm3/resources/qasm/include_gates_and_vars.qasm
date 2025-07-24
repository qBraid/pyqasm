OPENQASM 3.0;
include "stdgates.inc";
include "include_gates_and_vars.inc";

// OpenQASM3 script utilizes pre-defined variables & gates from .inc
qubit[A] q;

for int i in [0:A-1] {
    float theta = c[i % 3][i % 2];  
    d(theta) q[i];
}
