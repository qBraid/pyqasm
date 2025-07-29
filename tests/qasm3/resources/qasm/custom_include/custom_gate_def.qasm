OPENQASM 3;
include "stdgates.inc";

gate custom(a) p, q {
    h p;
    z q;
    rx(a) p;
    cx p,q;
}