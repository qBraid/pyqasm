OPENQASM 3.0;
include "stdgates.inc";
include "custom_qasm2.qasm";

qubit[2] q;
int [32] var = 5;
int [32] result = my_func(var);