# Copyright (C) 2025 qBraid
#
# This file is part of PyQASM
#
# PyQASM is free software released under the GNU General Public License v3
# or later. You can redistribute and/or modify it under the terms of the GPL v3.
# See the LICENSE file in the project root or <https://www.gnu.org/licenses/gpl-3.0.html>.
#
# THERE IS NO WARRANTY for PyQASM, as per Section 15 of the GPL v3.

"""
Definition of the decomposition rules for the gates in the basis sets.
"""
from enum import Enum

from pyqasm.elements import BasisSet
from pyqasm.maps.expressions import CONSTANTS_MAP


class AppliedQubit(Enum):
    """Enum to represent the qubits that are involved in the decomposition of a gate."""

    QUBIT1 = 0  # Control qubit
    QUBIT2 = 1  # Target qubit


# Decomposition rules for the gates in the basis sets.
# The rules are defined as a dictionary where the key is the gate name.
# The value is a list of dictionaries.
# Each dictionary in the list represents a step in the decomposition of the gate.
# Each step is defined by a dictionary with the following keys:
#     - gate: The name of the gate to be applied.
#     - param: The parameter of the gate.
#     - target_bit: The target qubit of the gate.
#                   This key is only used for decomposition of gates that operate on two qubits.
#     - controll_bit: The control qubit of the gate.
#                   This key is only used for gates that operate on two qubits.
#
DECOMPOSITION_RULES = {
    BasisSet.ROTATIONAL_CX: {
        "x": [{"gate": "rx", "param": CONSTANTS_MAP["pi"]}],
        "y": [{"gate": "ry", "param": CONSTANTS_MAP["pi"]}],
        "z": [{"gate": "rz", "param": CONSTANTS_MAP["pi"]}],
        "h": [
            {"gate": "ry", "param": CONSTANTS_MAP["pi"] / 2},
            {"gate": "rx", "param": CONSTANTS_MAP["pi"]},
        ],
        "s": [{"gate": "rz", "param": CONSTANTS_MAP["pi"] / 2}],
        "t": [{"gate": "rz", "param": CONSTANTS_MAP["pi"] / 4}],
        "sx": [{"gate": "rx", "param": CONSTANTS_MAP["pi"] / 2}],
        "sdg": [{"gate": "rz", "param": -CONSTANTS_MAP["pi"] / 2}],
        "tdg": [{"gate": "rz", "param": -CONSTANTS_MAP["pi"] / 4}],
        "cz": [
            {"gate": "ry", "param": CONSTANTS_MAP["pi"] / 2, "target_bit": AppliedQubit.QUBIT2},
            {"gate": "rx", "param": CONSTANTS_MAP["pi"], "target_bit": AppliedQubit.QUBIT2},
            {"gate": "cx", "controll_bit": AppliedQubit.QUBIT1, "target_bit": AppliedQubit.QUBIT2},
            {"gate": "ry", "param": CONSTANTS_MAP["pi"] / 2, "target_bit": AppliedQubit.QUBIT2},
            {"gate": "rx", "param": CONSTANTS_MAP["pi"], "target_bit": AppliedQubit.QUBIT2},
        ],
        "swap": [
            {"gate": "cx", "controll_bit": AppliedQubit.QUBIT1, "target_bit": AppliedQubit.QUBIT2},
            {"gate": "cx", "controll_bit": AppliedQubit.QUBIT2, "target_bit": AppliedQubit.QUBIT1},
            {"gate": "cx", "controll_bit": AppliedQubit.QUBIT1, "target_bit": AppliedQubit.QUBIT2},
        ],
    },
    BasisSet.CLIFFORD_T: {
        "x": [{"gate": "h"}, {"gate": "s"}, {"gate": "s"}, {"gate": "h"}],
        "y": [
            {"gate": "s"},
            {"gate": "s"},
            {"gate": "h"},
            {"gate": "s"},
            {"gate": "s"},
            {"gate": "h"},
        ],
        "z": [{"gate": "s"}, {"gate": "s"}],
        "sx": [
            {"gate": "s"},
            {"gate": "s"},
            {"gate": "s"},
            {"gate": "h"},
            {"gate": "s"},
            {"gate": "s"},
            {"gate": "s"},
        ],
        "cz": [
            {"gate": "h", "target_bit": AppliedQubit.QUBIT2},
            {"gate": "cx", "controll_bit": AppliedQubit.QUBIT1, "target_bit": AppliedQubit.QUBIT2},
            {"gate": "h", "target_bit": AppliedQubit.QUBIT2},
        ],
        "swap": [
            {"gate": "cx", "controll_bit": AppliedQubit.QUBIT1, "target_bit": AppliedQubit.QUBIT2},
            {"gate": "cx", "controll_bit": AppliedQubit.QUBIT2, "target_bit": AppliedQubit.QUBIT1},
            {"gate": "cx", "controll_bit": AppliedQubit.QUBIT1, "target_bit": AppliedQubit.QUBIT2},
        ],
    },
}

ROTATIONAL_LOOKUP_RULES = {
    BasisSet.CLIFFORD_T: {
        "rz": {
            CONSTANTS_MAP['pi']: [
                {"gate": "s"},
                {"gate": "s"},
            ],
            CONSTANTS_MAP['pi']/2 :[
                {"gate": "s"}
            ],
            CONSTANTS_MAP['pi']/4 :[
                {"gate": "t"}
            ]
        },
        
        # Rx(∅) = H.Rz(∅).H
        "rx": {
            CONSTANTS_MAP['pi']: [
                {"gate": "h"},
                {"gate": "s"},
                {"gate": "s"},
                {"gate": "h"},
            ],
            CONSTANTS_MAP['pi']/2 :[
                {"gate": "h"},
                {"gate": "s"},
                {"gate": "h"},
            ],
            CONSTANTS_MAP['pi']/4 :[
                {"gate": "h"},
                {"gate": "t"},
                {"gate": "h"},
            ]
        },
        
        # Ry(∅) = S†.H.Rz(∅).H.S
        "ry": {
            CONSTANTS_MAP['pi']: [
                {"gate": "sdg"},
                {"gate": "h"},
                {"gate": "s"},
                {"gate": "s"},
                {"gate": "h"},
                {"gate": "s"},
            ],
            CONSTANTS_MAP['pi']/2 :[
                {"gate": "sdg"},
                {"gate": "h"},
                {"gate": "s"},
                {"gate": "h"},
                {"gate": "s"},
            ],
            CONSTANTS_MAP['pi']/4 :[
                {"gate": "sdg"},
                {"gate": "h"},
                {"gate": "t"},
                {"gate": "h"},
                {"gate": "s"},
            ]
        },
    }
}

# """TODO: Implement the Solovay-Kitaev algorithm"""
#
# def solovay_kitaev_algo(gate_name, param, accuracy):
#     pass
