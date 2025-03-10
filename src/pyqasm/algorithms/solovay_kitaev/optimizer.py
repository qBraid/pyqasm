"""
Definition of the optimizer for the Solovay-Kitaev theorem.
"""

from pyqasm.algorithms.solovay_kitaev.utils import get_identity_weight_group_for_optimizer
from pyqasm.elements import BasisSet


def optimize_gate_sequence(seq: list[str], target_basis_set):
    """Optimize a gate sequence based on the identity weight group.
    Args:
        seq (list[str]): The gate sequence to optimize.
        target_basis_set (BasisSet): The target basis set.

    Returns:
        list[str]: The optimized gate sequence.
    """
    target_identity_weight_group = get_identity_weight_group_for_optimizer(target_basis_set)
    for _ in range(int(1e6)):
        current_group = None
        current_weight = 0
        start_index = 0
        changed = False

        for i, gate_name in enumerate(seq):
            if gate_name not in target_identity_weight_group:
                continue

            gate = target_identity_weight_group[gate_name]
            new_group = gate["group"]
            new_weight = gate["weight"]

            if current_group is None or new_group != current_group:
                current_group = new_group
                current_weight = new_weight
                start_index = i
            else:
                current_weight += new_weight

            if current_weight == 1:
                seq = seq[:start_index] + seq[i + 1 :]
                changed = True
                break
            if current_weight > 1:
                remaining_weight = current_weight - 1
                for key, value in target_identity_weight_group.items():
                    if value["group"] == current_group and value["weight"] == remaining_weight:
                        seq = seq[:start_index] + [key] + seq[i + 1 :]
                        changed = True
                        break
                break

        if not changed:
            return seq

    return seq


if __name__ == "__main__":
    s1 = ["s", "s", "s", "t", "t", "tdg", "sdg", "sdg", "sdg", "tdg", "s", "h", "s"]
    s2 = [
        "t",
        "s",
        "s",
        "s",
        "t",
        "tdg",
        "tdg",
        "sdg",
        "sdg",
        "sdg",
        "t",
        "s",
        "s",
        "s",
        "t",
        "tdg",
        "tdg",
        "sdg",
        "sdg",
        "sdg",
        "s",
        "h",
        "s",
    ]
    s3 = ["h", "s", "s", "t", "t", "s", "t"]  # ['h', 't']
    s4 = ["h", "s", "s", "t", "t", "s", "h"]  # []
    s5 = ["h", "s", "s", "t", "h", "h", "t", "s", "h", "t"]  # ['t']

    print(optimize_gate_sequence(s1, BasisSet.CLIFFORD_T) == ["s", "h", "s"])
    print(optimize_gate_sequence(s2, BasisSet.CLIFFORD_T) == ["s", "h", "s"])
    print(optimize_gate_sequence(s3, BasisSet.CLIFFORD_T) == ["h", "t"])
    print(optimize_gate_sequence(s4, BasisSet.CLIFFORD_T) == [])
    print(optimize_gate_sequence(s5, BasisSet.CLIFFORD_T) == ["t"])
