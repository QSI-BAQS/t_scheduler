
from typing import List
from t_scheduler.gate import BaseGate, T_Gate


def toffoli_example_input():
    return {
        "n_qubits": 13,
        "statenodes": [0, 1, 2],
        "adjacencies": {
            0: [3],
            1: [4],
            2: [5, 6, 7, 8, 9],
            3: [0, 6, 7, 8, 9, 10, 11],
            4: [1, 5, 6, 8, 9, 10, 12],
            5: [2, 4],
            6: [2, 3, 4],
            7: [2, 3],
            8: [2, 3, 4],
            9: [2, 3, 4],
            10: [3, 4],
            11: [3],
            12: [4],
        },
        "local_cliffords": [
            "I",
            "I",
            "I",
            "I",
            "I",
            "H",
            "H",
            "H",
            "H",
            "I",
            "H",
            "H",
            "H",
        ],
        "consumptionschedule": [
            [{0: []}, {2: []}, {1: []}],
            [{5: [2, 1]}],
            [{6: [0, 5]}],
            [{7: [1, 6]}],
            [{4: [2, 7]}, {8: [7]}],
            [{3: [0, 5, 4]}, {10: [0, 4]}, {9: [8]}],
            [{11: [3, 10]}, {12: [10]}],
        ],
        "measurement_tags": [0, 0, 0, 1, 1, 2, 1, 2, 1, 0, 2, 0, 0],
        "paulicorrections": [
            {0: "IIIXIIXIIIXII"},
            {1: "IIIIXXIXXIIII"},
            {2: "IIIIZZIIIIIII"},
            {3: "IIIIIIIIIIIZI"},
            {4: "IIIZIIIIIIZII"},
            {5: "IIIZIIZIIIIII"},
            {6: "IIIIZIIZIIIII"},
            {7: "IIIIZIIIZIIII"},
            {8: "IIIIIIIIIXIII"},
            {10: "IIIIIIIIIIIZZ"},
        ],
        "outputnodes": [11, 12, 9],
        "time": 7,
        "space": 10,
    }


def make_gates(obj, func = lambda x: x):
    gates = [T_Gate(func(q), 2, 3, targ_orig=q) for q in range(obj['n_qubits'])]
    return gates

def dag_create(obj, gates):
    dag_layers = []
    for input_layer in obj['consumptionschedule']:
        layer = []
        for gate in input_layer:
            for targ, pre in gate.items():  # one element unpacking
                targ = int(targ)
                layer.append(gates[targ])
                for q in pre:
                    gates[targ].pre.append(gates[q])
                    gates[q].post.append(gates[targ])
        dag_layers.append(layer)
    print(dag_layers)
    dag_prune(dag_layers, gates)  # type: ignore
    return dag_layers, gates

def dag_prune(dag_layers: List[List[T_Gate]], gates: List[T_Gate]):
    for g in gates:
        g.post_discard = set() # type: ignore
    base_layer = dag_layers[0]
    seen = set()
    stack = [(g, 0) for g in base_layer]
    while stack:
        curr, gate_idx = stack.pop()
        if gate_idx == 0:
            seen.add(curr)
        if gate_idx >= len(curr.post):
            seen.remove(curr)
            continue
        stack.append((curr, gate_idx + 1))

        gate = curr.post[gate_idx]  # type: ignore
        redundant = set(gate.pre) & seen
        redundant.discard(curr)
        for extra in redundant:
            extra.post_discard.add(gate) # type: ignore
            gate.pre.remove(extra)
        stack.append((gate, 0))

    for g in gates:
        g.post = [x for x in g.post if x not in g.post_discard] # type: ignore
        del g.post_discard # type: ignore

def topological_sort(dag_roots):
    seen = set()
    stack = []
    L = []
    for root in dag_roots:
        if root in seen:
            continue
        stack.append((root, 0))
        while stack:
            node, child_idx = stack.pop()
            if child_idx == 0 and node in seen:
                continue
            elif child_idx >= len(node.post):
                seen.add(node)
                L.append(node)
                continue
            stack.append((node, child_idx + 1))
            stack.append((node.post[child_idx], 0))
    return L


def parse_weights(gate_layers):
    parse_order = topological_sort(gate_layers[0])

    for gate in parse_order:
        if len(gate.post) == 0:
            gate.schedule_weight = 0
        else:
            gate.schedule_weight = sum(
                g.schedule_weight + g.weight for g in gate.post)



MOVE_T_ADJ_DELAY = 1
MOVE_T_NONLOCAL_DELAY = 4
MEASURE_AND_CORR_DELAY = 2
ROTATE_DELAY = 3
RESET_PLUS_DELAY = 1

