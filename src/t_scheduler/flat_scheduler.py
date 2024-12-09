from ast import parse
from collections import deque
from multiprocessing import active_children
from typing import List
from t_scheduler import gate
from t_scheduler.gate import BaseGate, GateType, T_Gate
from t_scheduler.patch import Patch, PatchOrientation, PatchType
from t_scheduler.scheduler import RotationStrategy, print_board
from t_scheduler.widget import Widget


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

    # debug!
    # for g in gates:
    #     g.schedule_weight = None

    for gate in parse_order:
        if len(gate.post) == 0:
            gate.schedule_weight = 0
        else:
            gate.schedule_weight = sum(g.schedule_weight + g.weight for g in gate.post)

    
    # for g in gates:
    #     print(g, g.schedule_weight)



class FlatScheduler:
    def __init__(
        self,
        gate_layers,
        widget,
        # rot_strat: RotationStrategy,
        debug: bool = False,
    ):
        # self.rot_strat = rot_strat
        self.widget = widget

        self.waiting = deque(gate_layers)
        self.queued = deque()
        self.deferred = []
        self.next_deferred = []
        self.active = []
        self.next_active = []

        self.output_layers = []

        self.curr_layer = []

        self.debug = debug

        self.ROTATION_DURATION = 3
        self.time = 0

        self.hazard = {}

    def schedule(self):
        # while self.waiting:
        self.queued.extend(self.waiting.popleft())

        while self.queued or self.deferred or self.active:
            self.schedule_pass()

    def schedule_pass(self):
        # breakpoint()
        for gate in self.deferred:
            if gate.available() and self.alloc_gate(gate):
                pass
            else:
                self.next_deferred.append(gate)

        self.deferred = self.next_deferred
        self.next_deferred = []

        next_queued = []
        for gate in self.queued:
            if gate.available() and self.alloc_gate(gate):
                pass
            else:
                next_queued.append(gate)

        self.queued = next_queued

        if self.debug:
            print_board(self.widget)

        if not self.active:
            raise Exception("No progress!")

        output_layer = []
        for gate in self.active:
            output_layer.append(gate.path)
        self.output_layers.append(output_layer)

        for gate in self.active:
            gate.tick()

        for gate in self.active:
            gate.cleanup(self)

        for gate in self.active:
            # gate.next(self)
            if not gate.completed():
                self.next_active.append(gate)
            else:
                for child in gate.post:
                    if all(g.completed() for g in child.pre):
                        self.queued.append(child)
        self.active = self.next_active
        self.next_active = []

        self.time += 1

    def alloc_gate(self, gate):
        path = [self.widget[0, gate.targ * 2]]
        if any(p.locked() for p in path): 
            return False
        gate.activate(path, Patch(PatchType.T, -1, -1))
        self.active.append(gate)
        return True
    
    # def alloc_gate(self, gate):
    #     if gate.gate_type == GateType.T_STATE:
    #         path = self.search(self.widget, gate.targ)
    #         # TODO unhack
    #         if path is None and not self.widget[0, 2 * gate.targ].locked():
    #             self.hazard[self.time] = self.hazard.get(self.time, 0) + 1
    #         if path is None:
    #             return False
    #         return self.process_rotation(path, gate)
    #     else:
    #         raise NotImplementedError()

    # def process_rotation(self, path, gate):

    #     T_patch = path[0]
    #     attack_patch = path[1]

    #     matching_rotation = (T_patch.row == attack_patch.row) ^ (
    #         T_patch.orientation == PatchOrientation.Z_TOP
    #     )

    #     if matching_rotation:
    #         T_patch.use()
    #         gate.activate(path, path[0])
    #         self.active.append(gate)
    #         return True
    #     else:
    #         return False

wid = Widget.default_widget(obj['n_qubits'] * 2, 3)
z = FlatScheduler(x, wid, True)