OPENQASM 3.0;
include "stdgates.inc";
include "circular_import.qasm";

gate custom(a) p, q {
    h p;
    z q;
    rx(a) p;
    cx p,q;
}