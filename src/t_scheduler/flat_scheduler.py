from typing import List
from t_scheduler import gate
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
            {5: "IIIZIIZIIIIII"},
            {6: "IIIIZIIZIIIII"},
            {7: "IIIIZIIIZIIII"},
            {8: "IIIIIIIIIXIII"},
            {4: "IIIZIIIIIIZII"},
            {3: "IIIIIIIIIIIZI"},
            {10: "IIIIIIIIIIIZZ"},
        ],
        "outputnodes": [11, 12, 9],
        "time": 7,
        "space": 10,
    }

def dag_create(obj):
    gates = [T_Gate(q) for q in range(obj['n_qubits'])]

    dag_layers = []
    for input_layer in obj['consumptionschedule']:
        layer = []
        for gate in input_layer:
            for targ, pre in gate.items(): # one element unpacking
                layer.append(gates[targ])
                for q in pre:
                    gates[targ].pre.append(gates[q])
                    gates[q].post.append(gates[targ])
        dag_layers.append(layer)
    print(dag_layers)
    dag_prune(dag_layers, gates) # type: ignore
    return dag_layers, gates

def dag_prune(dag_layers: List[List[BaseGate]], gates: List[BaseGate]):
    for g in gates:
        g.flag = set()
    base_layer = dag_layers[0]
    seen = set()
    stack = [(g, 0) for g in base_layer]
    while stack:
        curr, gate_idx = stack.pop()
        # print(curr, gate_idx, stack, curr.post)
        if gate_idx == 0:
            seen.add(curr)
        if gate_idx >= len(curr.post):
            seen.remove(curr)
            continue
        stack.append((curr, gate_idx + 1))

        gate = curr.post[gate_idx] # type: ignore
        # print(curr, gate)
        redundant = set(gate.pre) & seen
        redundant.discard(curr)
        # print(redundant)
        for extra in redundant:
            extra.flag.add(gate)
            gate.pre.remove(extra)
        stack.append((gate, 0))

    for g in gates:
        g.post = [x for x in g.post if x not in g.flag]
        g.flag = set()
obj = toffoli_example_input()
x, y = dag_create(obj)


def parse_weights():
    pass
