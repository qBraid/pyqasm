# Copyright (C) 2025 qBraid
#
# This file is part of PyQASM
#
# PyQASM is free software released under the GNU General Public License v3
# or later. You can redistribute and/or modify it under the terms of the GPL v3.
# See the LICENSE file in the project root or <https://www.gnu.org/licenses/gpl-3.0.html>.
#
# THERE IS NO WARRANTY for PyQASM, as per Section 15 of the GPL v3.

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
        # (
        #     """
        #     OPENQASM 3;
        #     include "stdgates.inc";
        #     qubit[1] q;
        #     u3(0,0,0) q[0];
        #     """,
        #     "U3 gate",
        # ),
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
    compiled_circuit = transpile(circuit, aer_simulator)
    result = aer_simulator.run(compiled_circuit).result()
    sv_qiskit = result.get_statevector(compiled_circuit)
    sv_expected = np.asarray(sv_qiskit)

    result = pyqasm_simulator.run(qasm, shots=1000)

    assert np.allclose(result.final_statevector, sv_expected), (
        f"Test failed for: {description}\n"
        f"PyQASM simulator statevector: {result.final_statevector}\n"
        f"Expected statevector: {sv_expected}"
    )
