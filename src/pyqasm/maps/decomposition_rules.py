from enum import Enum
from pyqasm.maps.expressions import CONSTANTS_MAP
from pyqasm.elements import BasisSet

class AppliedQubit(Enum):
    QUBIT1 = 0  # Control qubit
    QUBIT2 = 1  # Target qubit

"""Decomposition rules for the gates in the basis sets. 
The rules are defined as a dictionary where the key is the gate name and the value is a list of dictionaries. 
Each dictionary in the list represents a step in the decomposition of the gate. 
Each step is defined by a dictionary with the following keys:
    - gate: The name of the gate to be applied.
    - param: The parameter of the gate.
    - target_bit: The target qubit of the gate. This key is only used for decomposition of gates that operate on two qubits.
    - controll_bit: The control qubit of the gate. This key is only used for gates that operate on two qubits.
"""
DECOMPOSITION_RULES = {
    
    BasisSet.ROTATIONAL_CX: {
        "x": [
            {"gate": "rx", "param": CONSTANTS_MAP["pi"]}
        ],
        "y": [
            {"gate": "ry", "param": CONSTANTS_MAP["pi"]}
        ],
        "z": [
            {"gate": "rz", "param": CONSTANTS_MAP["pi"]}
        ],
        "h": [
            {"gate": "ry", "param": CONSTANTS_MAP["pi"]/2},
            {"gate": "rx", "param": CONSTANTS_MAP["pi"]}
        ],
        "s": [
            {"gate": "rz", "param": CONSTANTS_MAP["pi"]/2}
        ],
        "t": [
            {"gate": "rz", "param": CONSTANTS_MAP["pi"]/4}
        ],
        "sx": [
            {"gate": "rx", "param": CONSTANTS_MAP["pi"]/2}
        ],
        "sdg": [
            {"gate": "rz", "param": -CONSTANTS_MAP["pi"]/2}
        ],
        "tgd": [
            {"gate": "rz", "param": -CONSTANTS_MAP["pi"]/4}
        ],
        "cz": [
            {"gate": "ry", "param": CONSTANTS_MAP["pi"]/2, "target_bit": AppliedQubit.QUBIT2},
            {"gate": "rx", "param": CONSTANTS_MAP["pi"], "target_bit": AppliedQubit.QUBIT2},
            {"gate": "cx", "controll_bit": AppliedQubit.QUBIT1, "target_bit": AppliedQubit.QUBIT2},
            {"gate": "ry", "param": CONSTANTS_MAP["pi"]/2, "target_bit": AppliedQubit.QUBIT2},
            {"gate": "rx", "param": CONSTANTS_MAP["pi"], "target_bit": AppliedQubit.QUBIT2}
        ],
        "swap": [
            {"gate": "cx", "controll_bit": AppliedQubit.QUBIT1, "target_bit": AppliedQubit.QUBIT2},
            {"gate": "cx", "controll_bit": AppliedQubit.QUBIT2, "target_bit": AppliedQubit.QUBIT1},
            {"gate": "cx", "controll_bit": AppliedQubit.QUBIT1, "target_bit": AppliedQubit.QUBIT2}
        ]
    },
    BasisSet.CLIFFORD_T: {
        "x": [
            {"gate": "h"},
            {"gate": "s"},
            {"gate": "s"},
            {"gate": "h"}
        ],
        "y": [
            {"gate": "s"},
            {"gate": "s"},
            {"gate": "h"},
            {"gate": "s"},
            {"gate": "s"},
            {"gate": "h"}
        ],
        "z": [
            {"gate": "s"},
            {"gate": "s"}
        ],
        "sx": [
            {"gate": "s"},
            {"gate": "s"},
            {"gate": "s"},
            {"gate": "h"},
            {"gate": "s"},
            {"gate": "s"},
            {"gate": "s"}
        ],
        "cz": [
            {"gate": "h", "target_bit": AppliedQubit.QUBIT2},
            {"gate": "cx", "controll_bit": AppliedQubit.QUBIT1, "target_bit": AppliedQubit.QUBIT2},
            {"gate": "h", "target_bit": AppliedQubit.QUBIT2},
        ],
        "swap": [
            {"gate": "cx", "controll_bit": AppliedQubit.QUBIT1, "target_bit": AppliedQubit.QUBIT2},
            {"gate": "cx", "controll_bit": AppliedQubit.QUBIT2, "target_bit": AppliedQubit.QUBIT1},
            {"gate": "cx", "controll_bit": AppliedQubit.QUBIT1, "target_bit": AppliedQubit.QUBIT2}
        ]
    }
}
"""TODO: Implement the Solovay-Kitaev algorithm"""
def solovay_kitaev_algo(gate_name, param, accuracy):
    pass