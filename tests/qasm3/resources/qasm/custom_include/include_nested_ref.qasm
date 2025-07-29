OPENQASM 3.0;
include "stdgates.inc";

def nested_routine(qubit[3] q) { 
  for int i in [0:2] { 
    h q[i]; 
    x q[i]; 
  } 
}

def doublenested_routine(qubit[3] q) {
    nested_routine(q);
    for int i in [0:2] {
        rz(0.5) q[i];
    }
}

qubit[3] q;
doublenested_routine(q);
