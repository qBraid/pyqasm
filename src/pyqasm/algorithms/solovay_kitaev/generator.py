import pickle
import sys
from collections import deque

import numpy as np

gate_sets = {
    "clifford_T": [
        {
            "name": "h", 
            "identity": {
                "group": "h",
                "weight": 0.5
            },
            "matrix": (1 / np.sqrt(2)) * np.array([[1, 1], [1, -1]])
        },
        {
            "name": "s",
            "identity": {
                "group": "s-t",
                "weight": 0.25
            },
            "matrix": np.array([[1, 0], [0, 1j]])
        },
        {
            "name": "t",
            "identity": {
                "group": "s-t",
                "weight": 0.125
            },
            "matrix": np.array([[1, 0], [0, np.exp(1j * np.pi / 4)]]),
        },
    ]
}


def generate_solovay_kitaev_tree_cache(target_gate_set, max_depth, pkl_file_name):
    queue = deque([{"name": [], "depth": 0, "matrix": np.eye(2), "identity": {"group": None, "weight": 0}}])
    result = []

    while queue:
        node = queue.popleft()
        if node["depth"] == max_depth:
            break

        for gate in target_gate_set:
            new_group = gate["identity"]["group"]
            new_weight = gate["identity"]["weight"]
            current_group = node["identity"]["group"]
            current_weight = node["identity"]["weight"]

            if current_group != new_group:
                new_node = {
                    "name": node["name"] + [gate["name"]],
                    "depth": node["depth"] + 1,
                    "matrix": np.dot(node["matrix"], gate["matrix"]),
                    "identity": {"group": new_group, "weight": new_weight}
                }
                queue.append(new_node)
                result.append(new_node)
            elif current_weight + new_weight < 1:
                new_node = {
                    "name": node["name"] + [gate["name"]],
                    "depth": node["depth"] + 1,
                    "matrix": np.dot(node["matrix"], gate["matrix"]),
                    "identity": {"group": current_group, "weight": current_weight + new_weight}
                }
                queue.append(new_node)
                result.append(new_node)

    print(result)

    with open("cache/" + pkl_file_name, "wb") as f:
        pickle.dump(result, f)


if __name__ == "__main__":
    """
    How to use:
    
    Run this file direct, and pass the following command line arguments:
    
    target_gate_set: The target basis set of which you want to generate cached tree.
    max_depth: Max depth of the tree which you want to cache.
    pkl_file_name: Name of the pickel file in with you want to save the generated cache tree.
    
    Your command will look like this:
    python generator.py <target_gate_set> <max_depth> <pkl_file_name>
    eg.:
    python generator.py clifford_T 10 <pkl_file_name> clifford-t_depth-10.pkl
    
    The file will be saved in cache dir.
    """
    
    
    target_gate_set = sys.argv[1]
    max_depth = sys.argv[2]
    pkl_file_name = sys.argv[3]

    t = generate_solovay_kitaev_tree_cache(
        gate_sets[target_gate_set], int(max_depth), pkl_file_name
    )
