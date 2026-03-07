OPENQASM 2.0;
include "qelib1.inc";
include "custom_qasm2.qasm";

qreg q[2];
creg c[2];

int [32] var = 5;
int [32] result = my_func(var);