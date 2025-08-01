OPENQASM 3.0;
include "stdgates.inc";
include "nested.inc";

def doublenested_routine(qubit[3] q) {
    nested_routine(q);
    for int i in [0:2] {
        rz(0.5) q[i];
    }
}