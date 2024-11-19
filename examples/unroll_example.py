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
Script demonstrating how to unroll a QASM 3 program using pyqasm.

"""

from pyqasm import dumps, loads

qasm = """
// A program containing the Deutsch-Josza algorithm in OpenQASM 3
OPENQASM 3;
include "stdgates.inc";

// Define a custom gate for the Hadamard operation
gate hgate q {
    h q;
}

// Define a custom gate for the X operation
gate xgate q {
    x q;
}

const int[32] N = 4;
qubit[4] q;
qubit ancilla;


// Define the Deutsch-Josza algorithm
def deutsch_jozsa(qubit[N] q_func, qubit[1] ancilla_q) {

    // Initialize the ancilla qubit to |1>
    xgate ancilla_q;

    // Apply Hadamard gate to all qubits
    for int i in [0:N-1] {
        hgate q_func[i];
    }

    hgate ancilla_q;

    // Apply the oracle 
    for int i in [0:N-1] {
        cx q_func[i], ancilla_q;
    }

    // Apply Hadamard gate to all qubits again
    for int i in [0:N-1] {
        hgate q_func[i];
    }
}


// Run the Deutsch-Josza algorithm for N qubits
deutsch_jozsa(q, ancilla);

// Measure the results 
bit[4] result;
result = measure q;
"""

program = loads(qasm)

program.unroll()

print(dumps(program))
