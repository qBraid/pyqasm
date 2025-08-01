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

# pylint: disable=too-many-lines

"""
Module mapping supported QASM gates to lower level gate operations.

"""


from typing import Callable

import numpy as np
from openqasm3.ast import FloatLiteral, Identifier, IndexedIdentifier, QuantumGate, QuantumPhase

from pyqasm.elements import BasisSet, InversionOp
from pyqasm.exceptions import ValidationError, raise_qasm3_error
from pyqasm.linalg import kak_decomposition_angles
from pyqasm.maps.expressions import CONSTANTS_MAP


def u3_gate(
    theta: int | float,
    phi: int | float,
    lam: int | float,
    qubit_id,
) -> list[QuantumGate]:
    """
    Implements the U3 gate using the following decomposition:
         https://docs.quantum.ibm.com/api/qiskit/qiskit.circuit.library.UGate
         https://docs.quantum.ibm.com/api/qiskit/qiskit.circuit.library.PhaseGate

    Args:
        name (str): The name of the gate.
        theta (int | float): The theta parameter.
        phi (int | float): The phi parameter.
        lam (int | float): The lambda parameter.
        qubit_id (IndexedIdentifier): The qubit on which to apply the gate.

    Returns:
        list: A list of QuantumGate objects representing the decomposition of the U3 gate.
    """
    result: list[QuantumGate] = []
    result.extend(one_qubit_rotation_op("rz", lam, qubit_id))
    result.extend(one_qubit_rotation_op("rx", CONSTANTS_MAP["pi"] / 2, qubit_id))
    result.extend(one_qubit_rotation_op("rz", theta + CONSTANTS_MAP["pi"], qubit_id))
    result.extend(one_qubit_rotation_op("rx", CONSTANTS_MAP["pi"] / 2, qubit_id))
    result.extend(one_qubit_rotation_op("rz", phi + CONSTANTS_MAP["pi"], qubit_id))
    return result
    # global phase - e^(i*(phi+lambda)/2) is missing in the above implementation


def u3_inv_gate(
    theta: int | float,
    phi: int | float,
    lam: int | float,
    qubits,
) -> list[QuantumGate]:
    """
    Implements the inverse of the U3 gate using the decomposition present in
    the u3_gate function.
    """
    result: list[QuantumGate] = []
    result.extend(one_qubit_rotation_op("rz", -1.0 * (phi + CONSTANTS_MAP["pi"]), qubits))
    result.extend(one_qubit_rotation_op("rx", -1.0 * (CONSTANTS_MAP["pi"] / 2), qubits))
    result.extend(one_qubit_rotation_op("rz", -1.0 * (theta + CONSTANTS_MAP["pi"]), qubits))
    result.extend(one_qubit_rotation_op("rx", -1.0 * (CONSTANTS_MAP["pi"] / 2), qubits))
    result.extend(one_qubit_rotation_op("rz", -1.0 * lam, qubits))
    return result


def u2_gate(phi, lam, qubits) -> list[QuantumGate]:
    """
    Implements the U2 gate using the following decomposition:
        https://docs.quantum.ibm.com/api/qiskit/qiskit.circuit.library.U2Gate
    """
    return u3_gate(CONSTANTS_MAP["pi"] / 2, phi, lam, qubits)


def u2_inv_gate(phi, lam, qubits) -> list[QuantumGate]:
    """
    Implements the inverse of the U2 gate using the decomposition present in
    the u2_gate function.
    """
    return u3_inv_gate(CONSTANTS_MAP["pi"] / 2, phi, lam, qubits)


def global_phase_gate(theta: float, qubit_list: list[IndexedIdentifier]) -> list[QuantumPhase]:
    """
    Builds a global phase gate with the given theta and qubit list.

    Args:
        theta (float): The phase angle.
        qubit_list (list[IndexedIdentifier]): The list of qubits on which to apply the phase.

    Returns:
        list[QuantumPhase]: A QuantumPhase object representing the global phase gate.
    """
    return [
        QuantumPhase(
            argument=FloatLiteral(value=theta), qubits=qubit_list, modifiers=[]  # type: ignore
        )
    ]


def sxdg_gate_op(qubit_id) -> list[QuantumGate]:
    """
    Implements the conjugate transpose of the Sqrt(X) gate as a decomposition of other gates.
    """
    return one_qubit_rotation_op("rx", -CONSTANTS_MAP["pi"] / 2, qubit_id)


def cy_gate(qubit0: IndexedIdentifier, qubit1: IndexedIdentifier) -> list[QuantumGate]:
    """
    Implements the CY gate as a decomposition of other gates.
    """
    result: list[QuantumGate] = []
    result.extend(one_qubit_gate_op("sdg", qubit1))
    result.extend(two_qubit_gate_op("cx", qubit0, qubit1))
    result.extend(one_qubit_gate_op("s", qubit1))
    return result


def ch_gate(qubit0: IndexedIdentifier, qubit1: IndexedIdentifier) -> list[QuantumGate]:
    """
    Implements the CH gate as a decomposition of other gates.

    Used the following qiskit decomposition -

        In [10]: q = QuantumCircuit(2)

        In [11]: q.ch(0, 1)
        Out[11]: <qiskit.circuit.instructionset.InstructionSet at 0x127e00a90>

        In [12]: q.decompose().draw()
        Out[12]:

        q_0: ─────────────────■─────────────────────
             ┌───┐┌───┐┌───┐┌─┴─┐┌─────┐┌───┐┌─────┐
        q_1: ┤ S ├┤ H ├┤ T ├┤ X ├┤ Tdg ├┤ H ├┤ Sdg ├
             └───┘└───┘└───┘└───┘└─────┘└───┘└─────┘
    """
    result: list[QuantumGate] = []
    result.extend(one_qubit_gate_op("s", qubit1))
    result.extend(one_qubit_gate_op("h", qubit1))
    result.extend(one_qubit_gate_op("t", qubit1))
    result.extend(two_qubit_gate_op("cx", qubit0, qubit1))
    result.extend(one_qubit_gate_op("tdg", qubit1))
    result.extend(one_qubit_gate_op("h", qubit1))
    result.extend(one_qubit_gate_op("sdg", qubit1))

    return result


def xy_gate(
    theta: int | float, qubit0: IndexedIdentifier, qubit1: IndexedIdentifier
) -> list[QuantumGate]:
    """Implements the XXPlusYY gate matrix as defined by braket.

    Reference :
    https://amazon-braket-sdk-python.readthedocs.io/en/latest/_apidoc/braket.circuits.gate.html#braket.circuits.gate.Gate.XY

    """
    return xx_plus_yy_gate(theta, CONSTANTS_MAP["pi"], qubit0, qubit1)


def xx_plus_yy_gate(
    theta: int | float,
    phi: int | float,
    qubit0: IndexedIdentifier,
    qubit1: IndexedIdentifier,
) -> list[QuantumGate]:
    """
    Implements the XXPlusYY gate as a decomposition of other gates.

    Uses the following qiskit decomposition:

    In [7]: qc.draw()
    Out[7]:
         ┌─────────────────────┐
    q_0: ┤0                    ├
         │  (XX+YY)(theta,phi) │
    q_1: ┤1                    ├
         └─────────────────────┘

    In [8]: qc.decompose().draw()
    Out[8]:
         ┌─────────┐ ┌───┐            ┌───┐┌──────────────┐┌───┐  ┌─────┐   ┌──────────┐
    q_0: ┤ Rz(phi) ├─┤ S ├────────────┤ X ├┤ Ry(-theta/2) ├┤ X ├──┤ Sdg ├───┤ Rz(-phi) ├───────────
         ├─────────┴┐├───┴┐┌─────────┐└─┬─┘├──────────────┤└─┬─┘┌─┴─────┴──┐└─┬──────┬─┘┌─────────┐
    q_1: ┤ Rz(-π/2) ├┤ √X ├┤ Rz(π/2) ├──■──┤ Ry(-theta/2) ├──■──┤ Rz(-π/2) ├──┤ √Xdg ├──┤ Rz(π/2) ├
         └──────────┘└────┘└─────────┘     └──────────────┘     └──────────┘  └──────┘  └─────────┘
    """
    result: list[QuantumGate] = []

    result.extend(one_qubit_rotation_op("rz", phi, qubit0))
    result.extend(one_qubit_rotation_op("rz", -1 * (CONSTANTS_MAP["pi"] / 2), qubit1))
    result.extend(one_qubit_gate_op("s", qubit0))
    result.extend(one_qubit_gate_op("sx", qubit1))
    result.extend(one_qubit_rotation_op("rz", (CONSTANTS_MAP["pi"] / 2), qubit0))
    result.extend(two_qubit_gate_op("cx", qubit1, qubit0))
    result.extend(one_qubit_rotation_op("ry", -1 * theta / 2, qubit0))
    result.extend(one_qubit_rotation_op("ry", -1 * theta / 2, qubit1))
    result.extend(two_qubit_gate_op("cx", qubit1, qubit0))
    result.extend(one_qubit_rotation_op("rz", (-1 * CONSTANTS_MAP["pi"] / 2), qubit0))
    result.extend(one_qubit_gate_op("sxdg", qubit1))
    result.extend(one_qubit_gate_op("sdg", qubit0))
    result.extend(one_qubit_rotation_op("rz", (CONSTANTS_MAP["pi"] / 2), qubit1))
    result.extend(one_qubit_rotation_op("rz", -1 * phi, qubit0))

    return result


def ryy_gate(
    theta: int | float, qubit0: IndexedIdentifier, qubit1: IndexedIdentifier
) -> list[QuantumGate]:
    """
    Implements the YY gate as a decomposition of other gates.

    Uses the following qiskit decomposition:

    In [9]: qc.draw()
    Out[9]:
         ┌─────────────┐
    q_0: ┤0            ├
         │  Ryy(theta) │
    q_1: ┤1            ├
         └─────────────┘

    In [10]: qc.decompose().draw()
    Out[10]:
         ┌─────────┐                       ┌──────────┐
    q_0: ┤ Rx(π/2) ├──■─────────────────■──┤ Rx(-π/2) ├
         ├─────────┤┌─┴─┐┌───────────┐┌─┴─┐├──────────┤
    q_1: ┤ Rx(π/2) ├┤ X ├┤ Rz(theta) ├┤ X ├┤ Rx(-π/2) ├
         └─────────┘└───┘└───────────┘└───┘└──────────┘

    """
    result: list[QuantumGate] = []
    result.extend(one_qubit_rotation_op("rx", CONSTANTS_MAP["pi"] / 2, qubit0))
    result.extend(one_qubit_rotation_op("rx", CONSTANTS_MAP["pi"] / 2, qubit1))
    result.extend(two_qubit_gate_op("cx", qubit0, qubit1))
    result.extend(one_qubit_rotation_op("rz", theta, qubit1))
    result.extend(two_qubit_gate_op("cx", qubit0, qubit1))
    result.extend(one_qubit_rotation_op("rx", -CONSTANTS_MAP["pi"] / 2, qubit0))
    result.extend(one_qubit_rotation_op("rx", -CONSTANTS_MAP["pi"] / 2, qubit1))
    return result


def zz_gate(
    theta: int | float, qubit0: IndexedIdentifier, qubit1: IndexedIdentifier
) -> list[QuantumGate]:
    """
    Implements the ZZ gate as a decomposition of other gates.
    """
    result: list[QuantumGate] = []
    result.extend(two_qubit_gate_op("cz", qubit0, qubit1))
    result.extend(one_qubit_gate_op("h", qubit1))
    result.extend(one_qubit_rotation_op("rz", theta, qubit1))
    result.extend(one_qubit_gate_op("h", qubit1))
    result.extend(two_qubit_gate_op("cz", qubit0, qubit1))
    return result


def phaseshift_gate(theta: int | float, qubit: IndexedIdentifier) -> list[QuantumGate]:
    """
    Implements the phase shift gate as a decomposition of other gates.
    """
    result: list[QuantumGate] = []
    result.extend(one_qubit_gate_op("h", qubit))
    result.extend(one_qubit_rotation_op("rx", theta, qubit))
    result.extend(one_qubit_gate_op("h", qubit))
    return result


def cswap_gate(
    qubit0: IndexedIdentifier, qubit1: IndexedIdentifier, qubit2: IndexedIdentifier
) -> list[QuantumGate]:
    """
    Implements the CSWAP gate as a decomposition of other gates.
    """
    result: list[QuantumGate] = []
    result.extend(two_qubit_gate_op("cx", qubit2, qubit1))
    result.extend(one_qubit_gate_op("h", qubit2))
    result.extend(two_qubit_gate_op("cx", qubit1, qubit2))
    result.extend(one_qubit_gate_op("tdg", qubit2))
    result.extend(two_qubit_gate_op("cx", qubit0, qubit2))
    result.extend(one_qubit_gate_op("t", qubit2))
    result.extend(two_qubit_gate_op("cx", qubit1, qubit2))
    result.extend(one_qubit_gate_op("t", qubit1))
    result.extend(one_qubit_gate_op("tdg", qubit2))
    result.extend(two_qubit_gate_op("cx", qubit0, qubit2))
    result.extend(two_qubit_gate_op("cx", qubit0, qubit1))
    result.extend(one_qubit_gate_op("t", qubit2))
    result.extend(one_qubit_gate_op("t", qubit0))
    result.extend(one_qubit_gate_op("tdg", qubit1))
    result.extend(one_qubit_gate_op("h", qubit2))
    result.extend(two_qubit_gate_op("cx", qubit0, qubit1))
    result.extend(two_qubit_gate_op("cx", qubit2, qubit1))
    return result


def pswap_gate(
    theta: int | float, qubit0: IndexedIdentifier, qubit1: IndexedIdentifier
) -> list[QuantumGate]:
    """
    Implements the PSWAP gate as a decomposition of other gates.
    """
    result: list[QuantumGate] = []
    result.extend(two_qubit_gate_op("swap", qubit0, qubit1))
    result.extend(two_qubit_gate_op("cx", qubit0, qubit1))
    result.extend(u3_gate(0, 0, theta, qubit1))
    result.extend(two_qubit_gate_op("cx", qubit0, qubit1))
    return result


def iswap_gate(qubit0: IndexedIdentifier, qubit1: IndexedIdentifier) -> list[QuantumGate]:
    """Implements the iSwap gate as a decomposition of other gates.

    Reference: https://docs.quantum.ibm.com/api/qiskit/qiskit.circuit.library.iSwapGate
    """

    result: list[QuantumGate] = []

    result.extend(one_qubit_gate_op("s", qubit0))
    result.extend(one_qubit_gate_op("s", qubit1))
    result.extend(one_qubit_gate_op("h", qubit0))
    result.extend(two_qubit_gate_op("cx", qubit0, qubit1))
    result.extend(two_qubit_gate_op("cx", qubit1, qubit0))
    result.extend(one_qubit_gate_op("h", qubit1))

    return result


def crx_gate(
    theta: int | float, qubit0: IndexedIdentifier, qubit1: IndexedIdentifier
) -> list[QuantumGate]:
    """
    Implements the CRX gate as a decomposition of other gates.

    Used the following qiskit decomposition:

        In [26]: q.draw()
        Out[26]:

        q_0: ──────■──────
             ┌─────┴─────┐
        q_1: ┤ Rx(theta) ├
             └───────────┘

        In [27]: q.decompose().decompose().decompose().draw()
        Out[27]:

        q_0: ────────────────■───────────────────────■───────────────────────
             ┌────────────┐┌─┴─┐┌─────────────────┐┌─┴─┐┌───────────────────┐
        q_1: ┤ U(0,0,π/2) ├┤ X ├┤ U(-theta/2,0,0) ├┤ X ├┤ U(theta/2,-π/2,0) ├
             └────────────┘└───┘└─────────────────┘└───┘└───────────────────┘
    """
    result: list[QuantumGate] = []
    result.extend(u3_gate(0, 0, CONSTANTS_MAP["pi"] / 2, qubit1))
    result.extend(two_qubit_gate_op("cx", qubit0, qubit1))
    result.extend(u3_gate(-1 * theta / 2, 0, 0, qubit1))
    result.extend(two_qubit_gate_op("cx", qubit0, qubit1))
    result.extend(u3_gate(theta / 2, -1 * CONSTANTS_MAP["pi"] / 2, 0, qubit1))
    return result


def cry_gate(
    theta: int | float, qubit0: IndexedIdentifier, qubit1: IndexedIdentifier
) -> list[QuantumGate]:
    """
    Implements the CRY gate as a decomposition of other gates.

    Used the following qiskit decomposition -

        In [4]: q.draw()
        Out[4]:

        q_0: ──────■──────
             ┌─────┴─────┐
        q_1: ┤ Ry(theta) ├
             └───────────┘

        In [5]: q.decompose().decompose().decompose().draw()
        Out[5]:

        q_0: ─────────────────────■────────────────────────■──
             ┌─────────────────┐┌─┴─┐┌──────────────────┐┌─┴─┐
        q_1: ┤ U3(theta/2,0,0) ├┤ X ├┤ U3(-theta/2,0,0) ├┤ X ├
             └─────────────────┘└───┘└──────────────────┘└───┘
    """
    result: list[QuantumGate] = []
    result.extend(u3_gate(theta / 2, 0, 0, qubit1))
    result.extend(two_qubit_gate_op("cx", qubit0, qubit1))
    result.extend(u3_gate(-1 * theta / 2, 0, 0, qubit1))
    result.extend(two_qubit_gate_op("cx", qubit0, qubit1))
    return result


def crz_gate(
    theta: int | float, qubit0: IndexedIdentifier, qubit1: IndexedIdentifier
) -> list[QuantumGate]:
    """
    Implements the CRZ gate as a decomposition of other gates.

    Used the following qiskit decomposition -

        In [4]: q.draw()
        Out[4]:

    q_0: ──────■──────
         ┌─────┴─────┐
    q_1: ┤ Rz(theta) ├
         └───────────┘

        In [5]: q.decompose().decompose().decompose().draw()
        Out[5]:
        global phase: 0

    q_0: ─────────────────────■────────────────────────■──
         ┌─────────────────┐┌─┴─┐┌──────────────────┐┌─┴─┐
    q_1: ┤ U3(0,0,theta/2) ├┤ X ├┤ U3(0,0,-theta/2) ├┤ X ├
         └─────────────────┘└───┘└──────────────────┘└───┘
    """
    result: list[QuantumGate] = []
    result.extend(u3_gate(0, 0, theta / 2, qubit1))
    result.extend(two_qubit_gate_op("cx", qubit0, qubit1))
    result.extend(u3_gate(0, 0, -1 * theta / 2, qubit1))
    result.extend(two_qubit_gate_op("cx", qubit0, qubit1))
    return result


def cu_gate(  # pylint: disable=too-many-arguments
    theta: int | float,
    phi: int | float,
    lam: int | float,
    gamma: int | float,
    qubit0: IndexedIdentifier,
    qubit1: IndexedIdentifier,
) -> list[QuantumGate]:
    """
    Implements the CU gate as a decomposition of other gates.

    Uses the following qiskit decomposition -

        In [7]: qc.draw()
        Out[7]:

        q_0: ────────────■─────────────
             ┌───────────┴────────────┐
        q_1: ┤ U(theta,phi,lam,gamma) ├
             └────────────────────────┘

        In [8]: qc.decompose().decompose().decompose().draw()
        Out[8]:
                 ┌──────────────┐    ┌──────────────────────┐                                     »
        q_0: ────┤ U(0,0,gamma) ├────┤ U(0,0,lam/2 + phi/2) ├──■──────────────────────────────────»
             ┌───┴──────────────┴───┐└──────────────────────┘┌─┴─┐┌──────────────────────────────┐»
        q_1: ┤ U(0,0,lam/2 - phi/2) ├────────────────────────┤ X ├┤ U(-theta/2,0,-lam/2 - phi/2) ├»
             └──────────────────────┘                        └───┘└──────────────────────────────┘»
        «
        «q_0: ──■──────────────────────
        «     ┌─┴─┐┌──────────────────┐
        «q_1: ┤ X ├┤ U(theta/2,phi,0) ├
        «     └───┘└──────────────────┘
    """
    result: list[QuantumGate] = []
    result.extend(u3_gate(0, 0, gamma, qubit0))
    result.extend(u3_gate(0, 0, lam / 2 + phi / 2, qubit0))
    result.extend(u3_gate(0, 0, lam / 2 - phi / 2, qubit1))
    result.extend(two_qubit_gate_op("cx", qubit0, qubit1))
    result.extend(u3_gate(-theta / 2, 0, -lam / 2 - phi / 2, qubit1))
    result.extend(two_qubit_gate_op("cx", qubit0, qubit1))
    result.extend(u3_gate(theta / 2, phi, 0, qubit1))

    return result


def cu3_gate(  # pylint: disable=too-many-arguments
    theta: int | float,
    phi: int | float,
    lam: int | float,
    qubit0: IndexedIdentifier,
    qubit1: IndexedIdentifier,
) -> list[QuantumGate]:
    """
    Implements the CU3 gate as a decomposition of other gates.

    Uses the following qiskit decomposition -

        In [7]: qc.draw()
        Out[7]:

        q_0: ──────────■──────────
             ┌─────────┴─────────┐
        q_1: ┤ U3(theta,phi,lam) ├
             └───────────────────┘

        In [8]: qc.decompose().decompose().decompose().draw()
        Out[8]:
             ┌──────────────────────┐
        q_0: ┤ U(0,0,lam/2 + phi/2) ├──■────────────────────────────────────■──────────────────────
             ├──────────────────────┤┌─┴─┐┌──────────────────────────────┐┌─┴─┐┌──────────────────┐
        q_1: ┤ U(0,0,lam/2 - phi/2) ├┤ X ├┤ U(-theta/2,0,-lam/2 - phi/2) ├┤ X ├┤ U(theta/2,phi,0) ├
             └──────────────────────┘└───┘└──────────────────────────────┘└───┘└──────────────────┘
    """
    result: list[QuantumGate] = []
    result.extend(u3_gate(0, 0, lam / 2 + phi / 2, qubit0))
    result.extend(u3_gate(0, 0, lam / 2 - phi / 2, qubit1))
    result.extend(two_qubit_gate_op("cx", qubit0, qubit1))
    result.extend(u3_gate(-theta / 2, 0, -lam / 2 - phi / 2, qubit1))
    result.extend(two_qubit_gate_op("cx", qubit0, qubit1))
    result.extend(u3_gate(theta / 2, phi, 0, qubit1))

    return result


def cu1_gate(
    theta: int | float, qubit0: IndexedIdentifier, qubit1: IndexedIdentifier
) -> list[QuantumGate]:
    """
    Implements the CU1 gate as a decomposition of other gates.

    Uses the following qiskit decomposition -

        In [11]: qc.draw()
        Out[11]:

        q_0: ─■──────────
              │U1(theta)
        q_1: ─■──────────


        In [12]: qc.decompose().decompose().decompose().draw()
        Out[12]:
             ┌────────────────┐
        q_0: ┤ U(0,0,theta/2) ├──■───────────────────────■────────────────────
             └────────────────┘┌─┴─┐┌─────────────────┐┌─┴─┐┌────────────────┐
        q_1: ──────────────────┤ X ├┤ U(0,0,-theta/2) ├┤ X ├┤ U(0,0,theta/2) ├
                               └───┘└─────────────────┘└───┘└────────────────┘
    """
    result: list[QuantumGate] = []
    result.extend(u3_gate(0, 0, theta / 2, qubit0))
    result.extend(two_qubit_gate_op("cx", qubit0, qubit1))
    result.extend(u3_gate(0, 0, -theta / 2, qubit1))
    result.extend(two_qubit_gate_op("cx", qubit0, qubit1))
    result.extend(u3_gate(0, 0, theta / 2, qubit1))

    return result


def csx_gate(qubit0: IndexedIdentifier, qubit1: IndexedIdentifier) -> list[QuantumGate]:
    """Implement the CSX gate as a decomposition of other gates.

    Used the following qiskit decomposition -

        In [19]: q = QuantumCircuit(2)

        In [20]: q.csx(0,1)
        Out[20]: <qiskit.circuit.instructionset.InstructionSet at 0x127e022f0>

        In [21]: q.draw()
        Out[21]:

        q_0: ──■───
             ┌─┴──┐
        q_1: ┤ Sx ├
             └────┘

        In [22]: q.decompose().decompose().draw()
        Out[22]:
                 ┌─────────┐
            q_0: ┤ U1(π/4) ├──■────────────────■────────────────────────
                 ├─────────┤┌─┴─┐┌──────────┐┌─┴─┐┌─────────┐┌─────────┐
            q_1: ┤ U2(0,π) ├┤ X ├┤ U1(-π/4) ├┤ X ├┤ U1(π/4) ├┤ U2(0,π) ├
                 └─────────┘└───┘└──────────┘└───┘└─────────┘└─────────┘
    """
    result: list[QuantumGate] = []
    result.extend(phaseshift_gate(CONSTANTS_MAP["pi"] / 4, qubit0))
    result.extend(u2_gate(0, CONSTANTS_MAP["pi"], qubit1))
    result.extend(two_qubit_gate_op("cx", qubit0, qubit1))
    result.extend(phaseshift_gate(-CONSTANTS_MAP["pi"] / 4, qubit1))
    result.extend(two_qubit_gate_op("cx", qubit0, qubit1))
    result.extend(phaseshift_gate(CONSTANTS_MAP["pi"] / 4, qubit1))
    result.extend(u2_gate(0, CONSTANTS_MAP["pi"], qubit1))

    return result


def rxx_gate(
    theta: int | float, qubit0: IndexedIdentifier, qubit1: IndexedIdentifier
) -> list[QuantumGate | QuantumPhase]:
    """
    Implements the RXX gate as a decomposition of other gates.
    """

    result: list[QuantumGate | QuantumPhase] = []
    result.extend(global_phase_gate(-theta / 2, [qubit0, qubit1]))
    result.extend(one_qubit_gate_op("h", qubit0))
    result.extend(one_qubit_gate_op("h", qubit1))
    result.extend(two_qubit_gate_op("cx", qubit0, qubit1))
    result.extend(one_qubit_rotation_op("rz", theta, qubit1))
    result.extend(two_qubit_gate_op("cx", qubit0, qubit1))
    result.extend(one_qubit_gate_op("h", qubit1))
    result.extend(one_qubit_gate_op("h", qubit0))

    return result


def rccx_gate(
    qubit0: IndexedIdentifier, qubit1: IndexedIdentifier, qubit2: IndexedIdentifier
) -> list[QuantumGate]:
    result: list[QuantumGate] = []
    result.extend(u2_gate(0, CONSTANTS_MAP["pi"], qubit2))
    result.extend(phaseshift_gate(CONSTANTS_MAP["pi"] / 4, qubit2))
    result.extend(two_qubit_gate_op("cx", qubit1, qubit2))
    result.extend(phaseshift_gate(-CONSTANTS_MAP["pi"] / 4, qubit2))
    result.extend(two_qubit_gate_op("cx", qubit0, qubit2))
    result.extend(phaseshift_gate(CONSTANTS_MAP["pi"] / 4, qubit2))
    result.extend(two_qubit_gate_op("cx", qubit1, qubit2))
    result.extend(phaseshift_gate(-CONSTANTS_MAP["pi"] / 4, qubit2))
    result.extend(u2_gate(0, CONSTANTS_MAP["pi"], qubit2))

    return result


def rzz_gate(
    theta: int | float, qubit0: IndexedIdentifier, qubit1: IndexedIdentifier
) -> list[QuantumGate | QuantumPhase]:
    """
    Implements the RZZ gate as a decomposition of other gates.

    Used the following qiskit decomposition -

        In [32]: q.draw()
        Out[32]:

        q_0: ─■──────────
              │ZZ(theta)
        q_1: ─■──────────


        In [33]: q.decompose().decompose().decompose().draw()
        Out[33]:
        global phase: -theta/2

        q_0: ──■─────────────────────■──
             ┌─┴─┐┌───────────────┐┌─┴─┐
        q_1: ┤ X ├┤ U3(0,0,theta) ├┤ X ├
             └───┘└───────────────┘└───┘
    """
    result: list[QuantumGate | QuantumPhase] = []

    result.extend(global_phase_gate(-theta / 2, [qubit0, qubit1]))
    result.extend(two_qubit_gate_op("cx", qubit0, qubit1))
    result.extend(u3_gate(0, 0, theta, qubit1))
    result.extend(two_qubit_gate_op("cx", qubit0, qubit1))

    return result


def cphaseshift_gate(
    theta: int | float, qubit0: IndexedIdentifier, qubit1: IndexedIdentifier
) -> list[QuantumGate]:
    """
    Implements the controlled phase shift gate as a decomposition of other gates.

    Uses the following qiskit decomposition -

        In [11]: qc.draw()
        Out[11]:

        q_0: ─■─────────
             │P(theta)
        q_1: ─■─────────


        In [12]: qc.decompose().decompose().decompose().draw()
        Out[12]:
             ┌────────────────┐
        q_0: ┤ U(0,0,theta/2) ├──■───────────────────────■────────────────────
             └────────────────┘┌─┴─┐┌─────────────────┐┌─┴─┐┌────────────────┐
        q_1: ──────────────────┤ X ├┤ U(0,0,-theta/2) ├┤ X ├┤ U(0,0,theta/2) ├
                               └───┘└─────────────────┘└───┘└────────────────┘
    """
    result: list[QuantumGate] = []
    result.extend(u3_gate(0, 0, theta / 2, qubit0))
    result.extend(two_qubit_gate_op("cx", qubit0, qubit1))
    result.extend(u3_gate(0, 0, -theta / 2, qubit1))
    result.extend(two_qubit_gate_op("cx", qubit0, qubit1))
    result.extend(u3_gate(0, 0, theta / 2, qubit1))

    return result


def cphaseshift00_gate(
    theta: int | float, qubit0: IndexedIdentifier, qubit1: IndexedIdentifier
) -> list[QuantumGate]:
    """
    Implements the controlled phase shift 00 gate as a decomposition of other gates.
    """
    result: list[QuantumGate] = []
    result.extend(one_qubit_gate_op("x", qubit0))
    result.extend(one_qubit_gate_op("x", qubit1))
    result.extend(u3_gate(0, 0, theta / 2, qubit0))
    result.extend(u3_gate(0, 0, theta / 2, qubit1))
    result.extend(two_qubit_gate_op("cx", qubit0, qubit1))
    result.extend(u3_gate(0, 0, -theta / 2, qubit1))
    result.extend(two_qubit_gate_op("cx", qubit0, qubit1))
    result.extend(one_qubit_gate_op("x", qubit0))
    result.extend(one_qubit_gate_op("x", qubit1))
    return result


def cphaseshift01_gate(
    theta: int | float, qubit0: IndexedIdentifier, qubit1: IndexedIdentifier
) -> list[QuantumGate]:
    """
    Implements the controlled phase shift 01 gate as a decomposition of other gates.
    """
    result: list[QuantumGate] = []
    result.extend(one_qubit_gate_op("x", qubit0))
    result.extend(u3_gate(0, 0, theta / 2, qubit1))
    result.extend(u3_gate(0, 0, theta / 2, qubit0))
    result.extend(two_qubit_gate_op("cx", qubit0, qubit1))
    result.extend(u3_gate(0, 0, -theta / 2, qubit1))
    result.extend(two_qubit_gate_op("cx", qubit0, qubit1))
    result.extend(one_qubit_gate_op("x", qubit0))
    return result


def cphaseshift10_gate(
    theta: int | float, qubit0: IndexedIdentifier, qubit1: IndexedIdentifier
) -> list[QuantumGate]:
    """
    Implements the controlled phase shift 10 gate as a decomposition of other gates.
    """
    result: list[QuantumGate] = []
    result.extend(u3_gate(0, 0, theta / 2, qubit0))
    result.extend(one_qubit_gate_op("x", qubit1))
    result.extend(u3_gate(0, 0, theta / 2, qubit1))
    result.extend(two_qubit_gate_op("cx", qubit0, qubit1))
    result.extend(u3_gate(0, 0, -theta / 2, qubit1))
    result.extend(two_qubit_gate_op("cx", qubit0, qubit1))
    result.extend(one_qubit_gate_op("x", qubit1))
    return result


def gpi_gate(phi, qubit_id) -> list[QuantumGate]:
    """
    Implements the gpi gate as a decomposition of other gates.
    """
    theta_0 = CONSTANTS_MAP["pi"]
    phi_0 = phi
    lambda_0 = -phi_0 + CONSTANTS_MAP["pi"]
    return u3_gate(theta_0, phi_0, lambda_0, qubit_id)


def gpi2_gate(phi, qubit_id) -> list[QuantumGate]:
    """
    Implements the gpi2 gate as a decomposition of other gates.
    """
    # Reference:
    # https://amazon-braket-sdk-python.readthedocs.io/en/latest/_apidoc/braket.circuits.circuit.html#braket.circuits.circuit.Circuit.gpi2
    # https://docs.quantum.ibm.com/api/qiskit/qiskit.circuit.library.U3Gate#u3gate
    theta_0 = CONSTANTS_MAP["pi"] / 2
    phi_0 = phi - CONSTANTS_MAP["pi"] / 2
    lambda_0 = CONSTANTS_MAP["pi"] / 2 - phi
    return u3_gate(theta_0, phi_0, lambda_0, qubit_id)


# pylint: disable-next=too-many-arguments
def ms_gate(phi0, phi1, theta, qubit0, qubit1) -> list[QuantumGate]:
    """
    Implements the Molmer Sorenson gate as a decomposition of other gates.
    """
    mat = np.array(
        [
            [
                np.cos(np.pi * theta),
                0,
                0,
                -1j * np.exp(-1j * 2 * np.pi * (phi0 + phi1)) * np.sin(np.pi * theta),
            ],
            [
                0,
                np.cos(np.pi * theta),
                -1j * np.exp(-1j * 2 * np.pi * (phi0 - phi1)) * np.sin(np.pi * theta),
                0,
            ],
            [
                0,
                -1j * np.exp(1j * 2 * np.pi * (phi0 - phi1)) * np.sin(np.pi * theta),
                np.cos(np.pi * theta),
                0,
            ],
            [
                -1j * np.exp(1j * 2 * np.pi * (phi0 + phi1)) * np.sin(np.pi * theta),
                0,
                0,
                np.cos(np.pi * theta),
            ],
        ]
    )
    angles = kak_decomposition_angles(mat)
    qubits = [qubit0, qubit1]

    result: list[QuantumGate] = []
    result.extend(u3_gate(angles[0][0], angles[0][1], angles[0][2], qubits[0]))
    result.extend(u3_gate(angles[1][0], angles[1][1], angles[1][2], qubits[1]))
    result.extend(one_qubit_gate_op("sx", qubits[0]))
    result.extend(two_qubit_gate_op("cx", qubits[0], qubits[1]))
    result.extend(
        one_qubit_rotation_op("rx", ((1 / 2) - 2 * theta) * CONSTANTS_MAP["pi"], qubits[0])
    )
    result.extend(one_qubit_rotation_op("rx", CONSTANTS_MAP["pi"] / 2, qubits[1]))
    result.extend(two_qubit_gate_op("cx", qubits[1], qubits[0]))
    result.extend(sxdg_gate_op(qubits[1]))
    result.extend(one_qubit_gate_op("s", qubits[1]))
    result.extend(two_qubit_gate_op("cx", qubits[0], qubits[1]))
    result.extend(u3_gate(angles[2][0], angles[2][1], angles[2][2], qubits[0]))
    result.extend(u3_gate(angles[3][0], angles[3][1], angles[3][2], qubits[1]))
    return result


def ccx_gate_op(
    qubit0: IndexedIdentifier, qubit1: IndexedIdentifier, qubit2: IndexedIdentifier
) -> list[QuantumGate]:
    return [
        QuantumGate(
            modifiers=[],
            name=Identifier(name="ccx"),
            arguments=[],
            qubits=[qubit0, qubit1, qubit2],
        )
    ]


def ecr_gate(qubit0: IndexedIdentifier, qubit1: IndexedIdentifier) -> list[QuantumGate]:
    """
    Implements the ECR gate as a decomposition of other gates.
    """
    result: list[QuantumGate] = []
    result.extend(one_qubit_gate_op("s", qubit0))
    result.extend(one_qubit_rotation_op("rx", CONSTANTS_MAP["pi"] / 2, qubit1))
    result.extend(two_qubit_gate_op("cx", qubit0, qubit1))
    result.extend(one_qubit_gate_op("x", qubit0))
    return result


def c3sx_gate(
    qubit0: IndexedIdentifier,
    qubit1: IndexedIdentifier,
    qubit2: IndexedIdentifier,
    qubit3: IndexedIdentifier,
) -> list[QuantumGate]:
    """
    Implements the c3sx gate as a decomposition of other gates.

    Uses the following qiskit decomposition -

    In [15]: qc.draw()
    Out[15]:

    q_0: ──■───
           │
    q_1: ──■───
           │
    q_2: ──■───
         ┌─┴──┐
    q_3: ┤ Sx ├
         └────┘

    In [16]: qc.decompose().draw()
    Out[16]:

    q_0: ──────■──────────■────────────────────■────────────────────────────────────────■────────
               │        ┌─┴─┐                ┌─┴─┐                                      │
    q_1: ──────┼────────┤ X ├──────■─────────┤ X ├──────■──────────■────────────────────┼────────
               │        └───┘      │         └───┘      │        ┌─┴─┐                ┌─┴─┐
    q_2: ──────┼───────────────────┼────────────────────┼────────┤ X ├──────■─────────┤ X ├──────
         ┌───┐ │U1(π/8) ┌───┐┌───┐ │U1(-π/8) ┌───┐┌───┐ │U1(π/8) ├───┤┌───┐ │U1(-π/8) ├───┤┌───┐
    q_3: ┤ H ├─■────────┤ H ├┤ H ├─■─────────┤ H ├┤ H ├─■────────┤ H ├┤ H ├─■─────────┤ H ├┤ H ├─
         └───┘          └───┘└───┘           └───┘└───┘          └───┘└───┘           └───┘└───┘
    «
    «q_0:─────────────────────────────────■──────────────────────
    «                                     │
    «q_1:────────────■────────────────────┼──────────────────────
    «              ┌─┴─┐                ┌─┴─┐
    «q_2:─■────────┤ X ├──────■─────────┤ X ├──────■─────────────
    «     │U1(π/8) ├───┤┌───┐ │U1(-π/8) ├───┤┌───┐ │U1(π/8) ┌───┐
    «q_3:─■────────┤ H ├┤ H ├─■─────────┤ H ├┤ H ├─■────────┤ H ├
    «              └───┘└───┘           └───┘└───┘          └───┘
    """

    result: list[QuantumGate] = []
    result.extend(one_qubit_gate_op("h", qubit3))
    result.extend(cu1_gate(CONSTANTS_MAP["pi"] / 8, qubit0, qubit3))
    result.extend(two_qubit_gate_op("cx", qubit0, qubit1))
    # h(q[3]) * h (q[3]) = Identity
    result.extend(cu1_gate(-CONSTANTS_MAP["pi"] / 8, qubit1, qubit3))
    result.extend(two_qubit_gate_op("cx", qubit0, qubit1))
    # h(q[3]) * h (q[3]) = Identity
    result.extend(cu1_gate(CONSTANTS_MAP["pi"] / 8, qubit1, qubit3))
    result.extend(two_qubit_gate_op("cx", qubit1, qubit2))
    # h(q[3]) * h (q[3]) = Identity
    result.extend(cu1_gate(-CONSTANTS_MAP["pi"] / 8, qubit2, qubit3))
    result.extend(two_qubit_gate_op("cx", qubit0, qubit2))
    # h(q[3]) * h (q[3]) = Identity
    result.extend(cu1_gate(CONSTANTS_MAP["pi"] / 8, qubit2, qubit3))
    result.extend(two_qubit_gate_op("cx", qubit1, qubit2))
    # h(q[3]) * h (q[3]) = Identity
    result.extend(cu1_gate(-CONSTANTS_MAP["pi"] / 8, qubit2, qubit3))
    result.extend(two_qubit_gate_op("cx", qubit0, qubit2))
    # h(q[3]) * h (q[3]) = Identity
    result.extend(cu1_gate(CONSTANTS_MAP["pi"] / 8, qubit2, qubit3))
    result.extend(one_qubit_gate_op("h", qubit3))

    return result


def c4x_gate(
    qubit0: IndexedIdentifier,
    qubit1: IndexedIdentifier,
    qubit2: IndexedIdentifier,
    qubit3: IndexedIdentifier,
) -> list[QuantumGate]:
    """
    Implements the c4x gate
    """
    return [
        QuantumGate(
            modifiers=[],
            name=Identifier(name="c4x"),
            arguments=[],
            qubits=[qubit0, qubit1, qubit2, qubit3],
        )
    ]


def prx_gate(theta, phi, qubit_id) -> list[QuantumGate]:
    """
    Implements the PRX gate as a decomposition of other gates.
    """
    # Reference:
    # https://amazon-braket-sdk-python.readthedocs.io/en/latest/_apidoc/braket.circuits.circuit.html#braket.circuits.circuit.Circuit.prx
    # https://docs.quantum.ibm.com/api/qiskit/qiskit.circuit.library.U3Gate#u3gate
    theta_0 = theta
    phi_0 = phi - CONSTANTS_MAP["pi"] / 2
    lambda_0 = CONSTANTS_MAP["pi"] / 2 - phi
    return u3_gate(theta_0, phi_0, lambda_0, qubit_id)


def one_qubit_gate_op(gate_name: str, qubit_id: IndexedIdentifier) -> list[QuantumGate]:
    return [
        QuantumGate(
            modifiers=[],
            name=Identifier(name=gate_name),
            arguments=[],
            qubits=[qubit_id],
        )
    ]


def one_qubit_rotation_op(
    gate_name: str, rotation: float, qubit_id: IndexedIdentifier
) -> list[QuantumGate]:
    return [
        QuantumGate(
            modifiers=[],
            name=Identifier(name=gate_name),
            arguments=[FloatLiteral(value=rotation)],
            qubits=[qubit_id],
        )
    ]


def two_qubit_gate_op(
    gate_name: str, qubit_id1: IndexedIdentifier, qubit_id2: IndexedIdentifier
) -> list[QuantumGate]:
    return [
        QuantumGate(
            modifiers=[],
            name=Identifier(name=gate_name.lower()),
            arguments=[],
            qubits=[qubit_id1, qubit_id2],
        )
    ]


ONE_QUBIT_OP_MAP = {
    "id": lambda qubit_id: one_qubit_gate_op("id", qubit_id),
    "h": lambda qubit_id: one_qubit_gate_op("h", qubit_id),
    "x": lambda qubit_id: one_qubit_gate_op("x", qubit_id),
    "not": lambda qubit_id: one_qubit_gate_op("x", qubit_id),
    "y": lambda qubit_id: one_qubit_gate_op("y", qubit_id),
    "z": lambda qubit_id: one_qubit_gate_op("z", qubit_id),
    "s": lambda qubit_id: one_qubit_gate_op("s", qubit_id),
    "t": lambda qubit_id: one_qubit_gate_op("t", qubit_id),
    "sdg": lambda qubit_id: one_qubit_gate_op("sdg", qubit_id),
    "si": lambda qubit_id: one_qubit_gate_op("sdg", qubit_id),
    "tdg": lambda qubit_id: one_qubit_gate_op("tdg", qubit_id),
    "ti": lambda qubit_id: one_qubit_gate_op("tdg", qubit_id),
    "v": lambda qubit_id: one_qubit_gate_op("sx", qubit_id),
    "sx": lambda qubit_id: one_qubit_gate_op("sx", qubit_id),
    "nop": lambda qubit_id: one_qubit_gate_op("nop", qubit_id),
    "vi": sxdg_gate_op,
    "sxdg": sxdg_gate_op,
}


ONE_QUBIT_ROTATION_MAP = {
    "rx": lambda rotation, qubit_id: one_qubit_rotation_op("rx", rotation, qubit_id),
    "ry": lambda rotation, qubit_id: one_qubit_rotation_op("ry", rotation, qubit_id),
    "rz": lambda rotation, qubit_id: one_qubit_rotation_op("rz", rotation, qubit_id),
    "u1": phaseshift_gate,
    "U1": phaseshift_gate,
    "u": u3_gate,
    "U": u3_gate,
    "u3": u3_gate,
    "U3": u3_gate,
    "U2": u2_gate,
    "u2": u2_gate,
    "prx": prx_gate,
    "phaseshift": phaseshift_gate,
    "p": phaseshift_gate,
    "gpi": gpi_gate,
    "gpi2": gpi2_gate,
}

TWO_QUBIT_OP_MAP = {
    "cx": lambda qubit_id1, qubit_id2: two_qubit_gate_op("cx", qubit_id1, qubit_id2),
    "CX": lambda qubit_id1, qubit_id2: two_qubit_gate_op("cx", qubit_id1, qubit_id2),
    "cnot": lambda qubit_id1, qubit_id2: two_qubit_gate_op("cx", qubit_id1, qubit_id2),
    "cz": lambda qubit_id1, qubit_id2: two_qubit_gate_op("cz", qubit_id1, qubit_id2),
    "swap": lambda qubit_id1, qubit_id2: two_qubit_gate_op("swap", qubit_id1, qubit_id2),
    "cv": csx_gate,
    "cy": cy_gate,
    "ch": ch_gate,
    "xx": rxx_gate,
    "rxx": rxx_gate,
    "yy": ryy_gate,
    "ryy": ryy_gate,
    "zz": rzz_gate,
    "rzz": rzz_gate,
    "xy": xy_gate,
    "xx_plus_yy": xx_plus_yy_gate,
    "pswap": pswap_gate,
    "iswap": iswap_gate,
    "cp": cphaseshift_gate,
    "crx": crx_gate,
    "cry": cry_gate,
    "crz": crz_gate,
    "cu": cu_gate,
    "cu3": cu3_gate,
    "csx": csx_gate,
    "cphaseshift": cphaseshift_gate,
    "cu1": cu1_gate,
    "cp00": cphaseshift00_gate,
    "cphaseshift00": cphaseshift00_gate,
    "cp01": cphaseshift01_gate,
    "cphaseshift01": cphaseshift01_gate,
    "cp10": cphaseshift10_gate,
    "cphaseshift10": cphaseshift10_gate,
    "ecr": ecr_gate,
    "ms": ms_gate,
}

THREE_QUBIT_OP_MAP = {
    "ccx": ccx_gate_op,
    "toffoli": ccx_gate_op,
    "ccnot": ccx_gate_op,
    "cswap": cswap_gate,
    "rccx": rccx_gate,
}

FOUR_QUBIT_OP_MAP = {"c3sx": c3sx_gate, "c3sqrtx": c3sx_gate}

FIVE_QUBIT_OP_MAP = {
    "c4x": c4x_gate,
}

PARAMS_OP_SET = {
    1: {
        "rx",
        "ry",
        "rz",
        "phaseshift",
        "p",
        "u1",
        "U1",
        "gpi",
        "gpi2",
        "xx",
        "rxx",
        "yy",
        "ryy",
        "zz",
        "rzz",
        "xy",
        "pswap",
        "cp",
        "cu1",
        "crx",
        "cry",
        "crz",
        "cphaseshift",
        "cp10",
        "cphaseshift01",
        "cphaseshift10",
        "cp01",
        "cp00",
        "cphaseshift00",
    },
    2: {"xx_plus_yy", "u2", "U2", "prx"},
    3: {"ms", "cu3", "u", "U", "u3", "U3"},
    4: {"cu"},
}
BASIS_GATE_MAP = {
    # default basis set is the gate set of the stdgates.inc library file
    BasisSet.DEFAULT: {
        "id",
        "rx",
        "ry",
        "rz",
        "h",
        "x",
        "y",
        "z",
        "s",
        "sx",
        "t",
        "sdg",
        "tdg",
        "cx",
        "cz",
        "swap",
    },
    BasisSet.ROTATIONAL_CX: {"rx", "ry", "rz", "cx"},
    BasisSet.CLIFFORD_T: {"h", "t", "s", "cx", "tdg", "sdg"},
}


def map_qasm_op_num_params(op_name: str) -> int:
    """
    Map a basic QASM operation to the number of parameters it takes.

    Args:
        op_name (str): The QASM operation name.

    Returns:
        int: The number of parameters the operation takes.

    Raises:
        ValidationError: If the QASM operation is unsupported or undeclared.
    """
    for num_params, op_set in PARAMS_OP_SET.items():
        if op_name in op_set:
            return num_params
    return 0


# pylint: disable-next=inconsistent-return-statements
def map_qasm_op_to_callable(op_node: QuantumGate) -> tuple[Callable, int]:  # type: ignore[return]
    """
    Map a QASM operation to a callable.

    Args:
        op_node (QuantumGate): The QASM operation.

    Returns:
        tuple: A tuple containing the callable and the number of qubits the operation acts on.

    Raises:
        ValidationError: If the QASM operation is unsupported or undeclared.
    """
    op_name = op_node.name.name

    op_maps: list[tuple[dict, int]] = [
        (ONE_QUBIT_OP_MAP, 1),
        (ONE_QUBIT_ROTATION_MAP, 1),
        (TWO_QUBIT_OP_MAP, 2),
        (THREE_QUBIT_OP_MAP, 3),
        (FOUR_QUBIT_OP_MAP, 4),
        (FIVE_QUBIT_OP_MAP, 5),
    ]

    for op_map, qubit_count in op_maps:
        try:
            return op_map[op_name], qubit_count
        except KeyError:
            continue

    raise_qasm3_error(
        f"Unsupported / undeclared QASM operation: {op_name}", error_node=op_node, span=op_node.span
    )


SELF_INVERTING_ONE_QUBIT_OP_SET = {"id", "h", "x", "y", "z"}
ST_GATE_INV_MAP = {
    "s": "sdg",
    "t": "tdg",
    "sdg": "s",
    "tdg": "t",
}
ROTATION_INVERSION_ONE_QUBIT_OP_MAP = {"rx", "ry", "rz"}
U_INV_ROTATION_MAP = {
    "U": u3_inv_gate,
    "u3": u3_inv_gate,
    "U3": u3_inv_gate,
    "U2": u2_inv_gate,
    "u2": u2_inv_gate,
}


def map_qasm_inv_op_to_callable(op_name: str):
    """
    Map a QASM operation to a callable.

    Args:
        op_name (str): The QASM operation name.

    Returns:
        tuple: A tuple containing the callable, the number of qubits the operation acts on,
        and what is to be done with the basic gate which we are trying to invert.
    """
    if op_name in SELF_INVERTING_ONE_QUBIT_OP_SET:
        return ONE_QUBIT_OP_MAP[op_name], 1, InversionOp.NO_OP
    if op_name in ST_GATE_INV_MAP:
        inv_gate_name = ST_GATE_INV_MAP[op_name]
        return ONE_QUBIT_OP_MAP[inv_gate_name], 1, InversionOp.NO_OP
    if op_name in TWO_QUBIT_OP_MAP:
        return TWO_QUBIT_OP_MAP[op_name], 2, InversionOp.NO_OP
    if op_name in THREE_QUBIT_OP_MAP:
        return THREE_QUBIT_OP_MAP[op_name], 3, InversionOp.NO_OP
    if op_name in U_INV_ROTATION_MAP:
        # Special handling for U gate as it is composed of multiple
        # basic gates and we need to invert each of them
        return U_INV_ROTATION_MAP[op_name], 1, InversionOp.NO_OP
    if op_name in ROTATION_INVERSION_ONE_QUBIT_OP_MAP:
        return (
            ONE_QUBIT_ROTATION_MAP[op_name],
            1,
            InversionOp.INVERT_ROTATION,
        )
    raise ValidationError(f"Unsupported / undeclared QASM operation: {op_name}")


REV_CTRL_GATE_MAP = {
    "cx": "x",
    "cy": "y",
    "cz": "z",
    "crx": "rx",
    "cry": "ry",
    "crz": "rz",
    "cp": "p",
    "ch": "h",
    "cu": "u",
    "cswap": "swap",
    "ccx": "cx",
}

CTRL_GATE_MAP = {
    "x": "cx",
    "y": "cy",
    "z": "cz",
    "rx": "crx",
    "ry": "cry",
    "rz": "crz",
    "p": "cp",
    "h": "ch",
    "u": "cu",
    "swap": "cswap",
    "cx": "ccx",
}


def map_qasm_ctrl_op_to_callable(op_name: str, ctrl_count: int):
    """
    Map a controlled QASM operation to a callable.

    Args:
        op_name (str): The QASM operation name.
        ctrl_count (int): The number of control qubits.

    Returns:
        tuple: A tuple containing the callable and the number of qubits the operation acts on.
    """

    ctrl_op_name, c = op_name, ctrl_count
    while c > 0 and ctrl_op_name in CTRL_GATE_MAP:
        ctrl_op_name = CTRL_GATE_MAP[ctrl_op_name]
        c -= 1
    if c == 0:
        if ctrl_op_name in ONE_QUBIT_OP_MAP:
            return ONE_QUBIT_OP_MAP[ctrl_op_name], 1
        if ctrl_op_name in TWO_QUBIT_OP_MAP:
            return TWO_QUBIT_OP_MAP[ctrl_op_name], 2
        if ctrl_op_name in THREE_QUBIT_OP_MAP:
            return THREE_QUBIT_OP_MAP[ctrl_op_name], 3

    # TODO: decompose controls if not built in
    raise ValidationError(
        f"Unsupported controlled QASM operation: {op_name} with {ctrl_count} controls"
    )
