OPENQASM 2.0;
include "qelib1.inc";

def my_func(int[32] a) -> int[32] {
    return a;
}

qreg q[2];
creg c[2];

int [32] var = 5;
int [32] result = my_func(var);