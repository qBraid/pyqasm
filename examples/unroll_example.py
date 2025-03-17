# Copyright 2025 qBraid
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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
