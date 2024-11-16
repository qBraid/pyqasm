# Copyright (C) 2024 qBraid
#
# This file is part of pyqasm
#
# Pyqasm is free software released under the GNU General Public License v3
# or later. You can redistribute and/or modify it under the terms of the GPL v3.
# See the LICENSE file in the project root or <https://www.gnu.org/licenses/gpl-3.0.html>.
#
# THERE IS NO WARRANTY for pyqasm, as per Section 15 of the GPL v3.

# pylint: disable=invalid-name

"""
Script demonstrating how to validate a QASM 3 program using pyqasm.

"""

from pyqasm import loads

qasm = """
OPENQASM 3;
include "stdgates.inc";

// Define custom gates
gate hgate q {
    h q;
}

gate xgate q {
    x q;
}

gate cxgate q1, q2 {
    cx q1, q2;
}

// Define a subroutine for creating a Bell state
def create_bell_state(qubit[2] q) {
    hgate q[0];
    cxgate q[0], q[1];
    return;
}

// Define a subroutine for a generic quantum operation
def generic_operation(qubit[N] q) {
    for int i in [0:N-1] {
        hgate q[i];
        xgate q[i];
        y q[i];
        rx(pi) q[i];
    }
    return;
}

// Main program
const int[32] N = 4;
qubit[4] q;
bit[4] c;

// Create a Bell state using the alias
create_bell_state(q[0:2]);

measure q[0:1] -> c[0:1];

// Perform a generic operation on all qubits
generic_operation(q);

// Classical control flow
if (c[0]) {
    hgate q[0];
} else {
    xgate q[0];
}

// Define an array of angles for parameterized gates
array[float[64], N] angles = {pi/2, pi/4, pi/8, pi/16};

// Apply parameterized rotations
for int i in [0:N-1] {
    rx(angles[i]) q[i];
}

// Measure the qubits
c = measure q;
"""

program = loads(qasm)

program.validate()
