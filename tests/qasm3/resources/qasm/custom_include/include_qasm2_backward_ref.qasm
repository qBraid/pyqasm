OPENQASM 3.0;
include "stdgates.inc";
include "qelib1.inc";


def my_func(int[32] a) -> int[32] {
    return a;
}

qubit[2] q;
int [32] var = 5;
int [32] result = my_func(var);