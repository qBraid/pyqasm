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

# pylint: disable=redefined-outer-name

"""
Module containing tests for the PyQASM statevector simulator.

"""

import numpy as np
import pytest
from qiskit import transpile
from qiskit.qasm3 import loads
from qiskit_aer import AerSimulator

from pyqasm.simulator.statevector import Simulator


@pytest.fixture
def aer_simulator():
    """Fixture to create and return a Qiskit AerSimulator."""
    return AerSimulator(method="statevector")


@pytest.fixture
def pyqasm_simulator():
    """Fixture to create and return a pyqasm simulator."""
    return Simulator(seed=22)


@pytest.mark.parametrize(
    "qasm, description",
    [
        (
            """
            OPENQASM 3;
            include "stdgates.inc";
            qubit[1] q;
            h q[0];
            """,
            "Hadamard gate",
        ),
        (
            """
            OPENQASM 3;
            include "stdgates.inc";
            qubit[1] q;
            rx(pi) q[0];
            """,
            "RX(pi) gate",
        ),
        (
            """
            OPENQASM 3;
            include "stdgates.inc";
            qubit[1] q;
            ry(pi) q[0];
            """,
            "RY(pi) gate",
        ),
        (
            """
            OPENQASM 3;
            include "stdgates.inc";
            qubit[1] q;
            rz(pi) q[0];
            """,
            "RZ(pi) gate",
        ),
        (
            """
            OPENQASM 3;
            include "stdgates.inc";
            qubit[1] q;
            s q[0];
            """,
            "S gate",
        ),
        (
            """
            OPENQASM 3;
            include "stdgates.inc";
            qubit[1] q;
            t q[0];
            """,
            "T gate",
        ),
        (
            """
            OPENQASM 3;
            include "stdgates.inc";
            qubit[1] q;
            sdg q[0];
            """,
            "Sdg gate",
        ),
        (
            """
            OPENQASM 3;
            include "stdgates.inc";
            qubit[1] q;
            tdg q[0];
            """,
            "Tdg gate",
        ),
        (
            """
            OPENQASM 3;
            include "stdgates.inc";
            qubit[1] q;
            id q[0];
            """,
            "Identity gate",
        ),
        (
            """
            OPENQASM 3;
            include "stdgates.inc";
            qubit[1] q;
            u3(1.0, 0.5, 0.3) q[0];
            """,
            "U3 gate (global phase)",
        ),
        (
            """
            OPENQASM 3;
            include "stdgates.inc";
            qubit[1] q;
            h q[0];
            rx(pi) q[0];
            ry(pi) q[0];
            rz(pi) q[0];
            s q[0];
            t q[0];
            sdg q[0];
            tdg q[0];
            id q[0];
            """,
            "Combined gates: H, RX(pi), RY(pi), RZ(pi), S, T, Sdg, Tdg, ID",
        ),
        (
            """
            OPENQASM 3;
            include "stdgates.inc";
            qubit[2] q;
            cx q[0], q[1];
            """,
            "CX gate",
        ),
        (
            """
            OPENQASM 3;
            include "stdgates.inc";
            qubit[2] q;
            x q[0];
            x q[1];
            cy q[0], q[1];
            """,
            "CY on |11>",
        ),
        (
            """
            OPENQASM 3;
            include "stdgates.inc";
            qubit[2] q;
            x q[0];
            x q[1];
            cz q[0], q[1];
            """,
            "CZ on |11>",
        ),
        (
            """
            OPENQASM 3;
            include "stdgates.inc";
            qubit[2] q;
            x q[1];
            swap q[0], q[1];
            """,
            "SWAP on |01>",
        ),
        (
            """
            OPENQASM 3;
            include "stdgates.inc";
            qubit[3] q;
            x q[0];
            id q[1];
            id q[2];
            """,
            "X on qubit 0 of 3-qubit system",
        ),
        (
            """
            OPENQASM 3;
            include "stdgates.inc";
            qubit[2] q;
            cy q[0], q[1];
            """,
            "CY gate",
        ),
        (
            """
            OPENQASM 3;
            include "stdgates.inc";
            qubit[2] q;
            cz q[0], q[1];
            """,
            "CZ gate",
        ),
        (
            """
            OPENQASM 3;
            include "stdgates.inc";
            qubit[2] q;
            swap q[0], q[1];
            """,
            "Swap gate",
        ),
        (
            """
            OPENQASM 3;
            include "stdgates.inc";
            qubit[2] q;
            h q[0];
            crz(pi/4) q[0], q[1];
            """,
            "CRZ gate",
        ),
        (
            """
            OPENQASM 3;
            include "stdgates.inc";
            qubit[2] q;
            h q[0];
            h q[1];
            """,
            "Two H Gates",
        ),
        (
            """
            OPENQASM 3;
            include "stdgates.inc";
            qubit[2] q;
            h q[0];
            cx q[0], q[1];
            """,
            "Bell state",
        ),
        (
            """
            OPENQASM 3;
            include "stdgates.inc";
            qubit[3] q;
            h q[0];
            cx q[0], q[1];
            cx q[1], q[2];
            """,
            "GHZ state",
        ),
        (
            """
            OPENQASM 3;
            include "stdgates.inc";
            qubit[2] q;
            h q[0];
            swap q[0], q[1];
            cx q[0], q[1];
            """,
            "Bell state with swap",
        ),
        (
            """
            OPENQASM 3;
            include "stdgates.inc";
            qubit[2] q;
            h q[0];
            swap q[1], q[0];
            cx q[0], q[1];
            """,
            "Bell state with swap rev qubits",
        ),
    ],
)
def test_simulator_sv_results(qasm, description, aer_simulator, pyqasm_simulator):
    """Test PyQASM simulator by comparing SV results against the Qiskit Aer simulator."""
    circuit = loads(qasm)
    circuit.save_statevector()
    compiled_circuit = transpile(circuit, aer_simulator, optimization_level=0)
    result = aer_simulator.run(compiled_circuit).result()
    sv_qiskit = result.get_statevector(compiled_circuit)
    sv_expected = np.asarray(sv_qiskit)

    result = pyqasm_simulator.run(qasm, shots=1000)

    sv_actual = result.final_statevector
    if "global phase" in description:
        # Compare up to global phase: find first nonzero element and normalize
        idx = np.argmax(np.abs(sv_expected) > 1e-10)
        phase = sv_actual[idx] / sv_expected[idx]
        sv_actual = sv_actual / phase

    assert np.allclose(sv_actual, sv_expected), (
        f"Test failed for: {description}\n"
        f"PyQASM simulator statevector: {result.final_statevector}\n"
        f"Expected statevector: {sv_expected}"
    )


def test_simulator_large_circuit(aer_simulator, pyqasm_simulator):
    """Test PyQASM simulator on an 8-qubit circuit."""
    qasm = """
    OPENQASM 3;
    include "stdgates.inc";
    qubit[8] q;
    h q[0];
    cx q[0], q[1];
    cx q[1], q[2];
    cx q[2], q[3];
    h q[4];
    cx q[4], q[5];
    cx q[5], q[6];
    cx q[6], q[7];
    swap q[3], q[4];
    """
    circuit = loads(qasm)
    circuit.save_statevector()
    compiled_circuit = transpile(circuit, aer_simulator, optimization_level=0)
    result_qiskit = aer_simulator.run(compiled_circuit).result()
    sv_expected = np.asarray(result_qiskit.get_statevector(compiled_circuit))

    result = pyqasm_simulator.run(qasm, shots=0)

    assert np.allclose(result.final_statevector, sv_expected), (
        f"Test failed for 8-qubit circuit\n"
        f"PyQASM: {result.final_statevector}\n"
        f"Expected: {sv_expected}"
    )
