from collections import deque
from typing import List
from t_scheduler import gate
from t_scheduler.gate import BaseGate, GateType, T_Gate
from t_scheduler.patch import Patch, PatchOrientation, PatchType, TCultPatch
from t_scheduler.scheduler import RotationStrategy
from t_scheduler.widget import Widget
from .util import *


def dag_create(obj):
    gates = [T_Gate(q, 2, 3) for q in range(obj['n_qubits'])]

    dag_layers = []
    for input_layer in obj['consumptionschedule']:
        layer = []
        for gate in input_layer:
            for targ, pre in gate.items():  # one element unpacking
                layer.append(gates[targ])
                for q in pre:
                    gates[targ].pre.append(gates[q])
                    gates[q].post.append(gates[targ])
        dag_layers.append(layer)
    print(dag_layers)
    dag_prune(dag_layers, gates)  # type: ignore
    return dag_layers, gates

def dag_prune(dag_layers: List[List[BaseGate]], gates: List[BaseGate]):
    for g in gates:
        g.flag = set()
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
            extra.flag.add(gate)
            gate.pre.remove(extra)
        stack.append((gate, 0))

    for g in gates:
        g.post = [x for x in g.post if x not in g.flag]
        g.flag = set()

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


class FlatScheduler:
    def __init__(
        self,
        gate_layers,
        widget,
        debug: bool = False,
    ):
        self.widget = widget

        self.processed = set()

        self.waiting = deque(gate_layers)
        self.queued = []
        # self.deferred = []
        # self.next_deferred = []
        self.active = []
        self.next_active = []

        self.output_layers = []

        self.curr_layer = []

        self.debug = debug

        self.ROTATION_DURATION = 3
        self.time = 0

        self.hazard = {}

        self.T_queue = []
        self.next_T_queue = []

    def schedule(self):
        self.queued.extend(self.waiting.popleft())

        while self.queued or self.active:
            self.schedule_pass()

    def schedule_pass(self):
        # breakpoint()
        self.T_queue.extend(self.widget.update())
        # print(self.T_queue)
        self.queued.sort(key=lambda g: g.targ)
        next_queued = []
        for gate in self.queued:
            if gate.available() and self.alloc_gate(gate):
                pass
            else:
                next_queued.append(gate)

        self.queued = next_queued

        if self.debug:
            print_board(self.widget)

        output_layer = []
        for gate in self.active:
            output_layer.append(gate.path)
        self.output_layers.append(output_layer)

        for gate in self.active:
            gate.tick()

        for gate in self.active:
            gate.cleanup(self)

        for gate in self.active:
            gate.next(self)
            if not gate.completed():
                self.next_active.append(gate)
            else:
                for child in gate.post:
                    if all(g.completed() for g in child.pre) and child not in self.processed:
                        self.queued.append(child)
                        self.processed.add(child)
        self.active = self.next_active
        self.next_active = []

        self.time += 1

    def alloc_gate(self, gate):
        path = self.flat_sparse_search(self.widget, gate)
        if not path or any(p.locked() for p in path):
            return False
        gate.activate(path, path[0])
        for p in path[1:-1]:
            if p.patch_type == PatchType.CULTIVATOR:
                p.cultivator.reset()
        self.active.append(gate)
        return True

    def flat_dense_search(self, widget, gate, prefer_route_row=False):
        gate_col = gate.targ * 2
        if widget[0, gate_col].locked():
            return None

        # search_bounds = max(0, gate_col - self.SEARCH_WIDTH), min(widget.width, gate_col + self.SEARCH_WIDTH + 1)
        self.T_queue.sort(key=lambda p: (abs(p.col - gate_col), p.row))

        for i, T_patch in enumerate(self.T_queue):

            if prefer_route_row:
                vert = [widget[x, T_patch.col] for x in range(2, T_patch.row)]
            else:
                vert = [widget[x, gate_col] for x in range(2, T_patch.row)]

            if all(p.route_available() for p in vert):
                if prefer_route_row:
                    horizontal = [widget[1, i]
                                  for i in range_directed(T_patch.col, gate_col)]
                    path = [T_patch] + vert + \
                        horizontal + [widget[0, gate_col]]
                else:
                    horizontal = [widget[T_patch.row, i]
                                  for i in range_directed(T_patch.col, gate_col)]
                    path = horizontal + vert + \
                        [widget[1, gate_col], widget[0, gate_col]]

                if all(p.route_available() for p in path[1:-1]):
                    self.T_queue.pop(i)
                    return path
        return None

    def flat_sparse_search(self, widget, gate):
        gate_col = gate.targ * 2
        # search_bounds = max(0, gate_col - SEARCH_WIDTH), min(widget.width, gate_col + SEARCH_WIDTH + 1)
        self.T_queue.sort(key=lambda p: (abs(p.col - gate_col), p.row))

        for T_patch in self.T_queue:
            r, c = T_patch.row, T_patch.col
            vert = [widget[x, c] for x in range(2, r)]
            if widget[r, c].T_available() and all(p.route_available() for p in vert):
                return gen_sparse_path(widget, gate, widget[r, c])
        return None

def range_directed(a, b):
    if a <= b:
        return range(a, b + 1)
    else:
        return range(a, b - 1, -1)


def cancel_cost(patch):
    if not patch.route_available():
        return float('inf')
    elif patch.patch_type == PatchType.ROUTE:
        return 0
    elif patch.patch_type == PatchType.CULTIVATOR:
        return patch.cultivator.curr_stage * 10 + patch.cultivator._curr_cycle
    else:
        return float('inf')

def gen_sparse_path(widget, gate, T_patch):
    row, col = T_patch.row, T_patch.col

    gate_col = gate.targ * 2
    path = [T_patch]

    if widget[row - 1, col].patch_type == PatchType.CULTIVATOR:
        path.append(widget[row - 1, col])
        row -= 1

    row -= 1
    while row >= 4:
        best_col = col
        best_cost = max(cancel_cost(
            widget[row - 2][col]), cancel_cost(widget[row - 1][col]))

        for i in range_directed(col, gate_col):
            cost = max(cancel_cost(widget[row - 2][i]),
                       cancel_cost(widget[row - 1][i]))
            if cost < best_cost:
                best_col, best_cost = i, cost

        # hor_bounds = min(col, best_col), max(col, best_col) + 1

        path.extend(widget[row, c] for c in range_directed(col, best_col))

        path.append(widget[row - 1][best_col])
        path.append(widget[row - 2][best_col])
        col = best_col
        row -= 3
    path.extend(widget[r, col] for r in range(row, 1, -1))
    # hor_bounds = min(col, gate_col), max(col, gate_col) + 1
    path.extend(widget[1, c] for c in range_directed(col, gate_col))
    path.append(widget[0, gate_col])

    if all(p.route_available() for p in path[1:-1]):
        return path
    else:
        return None


if __name__ == "__main__":
    obj = toffoli_example_input()
    x, y = dag_create(obj)
    wid = Widget.t_cultivator_widget_row_sparse(obj['n_qubits'] * 2, 8)
    z = FlatScheduler(x, wid, True)
