from typing import *
from util import *
from itertools import chain
from collections import deque

def debug_gates():
    # gate_layers = [[0, 2, 1], [0, 2, 1]]
    gate_layers = [[*chain(*(([x] * 8) for x in [5,0,6,8,7]))], ]
    gate_layers2 = [[T_Gate(t) for t in layer] for layer in gate_layers]
    print(gate_layers)
    # output = schedule_undermine(20, 5, gate_layers2, True)

    wid = Widget.default_widget(20, 5)
    sched = Scheduler(RotationStrategy.BACKPROP_INIT, wid, gate_layers2, True)
    sched.schedule()
    print(sched.output_layers)
    print(len(sched.output_layers))

class RotationStrategy(Enum):
    BACKPROP_INIT = 0
    LOOKBACK = 1
    INJECT = 2

class Scheduler:
    def __init__(self, rot_strat: RotationStrategy, widget: Widget, gate_layers, debug:bool=False):
        self.rot_strat = rot_strat
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

    def schedule(self):
        while self.waiting:
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
            gate.cleanup()
        
        for gate in self.active:
            gate.next(self)
            if not gate.completed():
                self.next_active.append(gate)
        self.active = self.next_active
        self.next_active = []



    def alloc_gate(self, gate):
        if gate.gate_type == GateType.T_STATE:
            path = vertical_search(self.widget, gate.targ)
            if path is None:
                return False
            return self.process_rotation(path, gate)

        elif gate.gate_type == GateType.NO_RESOURCE:
            reg = self.widget[0, gate.targ*2]
            if reg.locked():
                return False
            gate.activate([reg])
            self.active.append(gate)
            return True
        elif gate.gate_type == GateType.ANCILLA:
            reg = self.widget[0, gate.targ*2]
            anc = self.widget[0, gate.targ*2 + 1]
            if reg.locked() or anc.locked():
                return False
            gate.activate([reg, anc])
            self.active.append(gate)
            return True
    
    def process_rotation(self, path, gate):
        
        T_patch = path[0]
        attack_patch = path[1]
        
        matching_rotation = (T_patch.row == attack_patch.row) ^ (T_patch.orientation == PatchOrientation.Z_TOP)

        if matching_rotation:
            T_patch.use()
            gate.activate(path, path[0])
            self.active.append(gate)
        elif self.rot_strat == RotationStrategy.BACKPROP_INIT:
            T_patch.orientation = T_patch.orientation.inverse()
            T_patch.use()
            gate.activate(path, path[0])
            self.active.append(gate)
        elif self.rot_strat == RotationStrategy.INJECT:
            reg_patch = self.widget[0, gate.targ * 2]
            rot_gate = RotateGate(path, gate)
            rot_gate.activate()
            self.active.append(rot_gate)
        else:
            raise NotImplementedError()
        return True

def T_search_owning(widget, reg) -> Patch | None:
    for r in range(2, widget.height):
        for c in range(2 * reg, 2 * reg + 2):
            if (patch := widget[r,c]).T_available():
                return patch



def T_path_owning(widget, reg, T_patch):
    if 2 * reg == T_patch.col:
        return [widget[r, T_patch.col] for r in range(T_patch.row, -1,-1)]
    else:
        hor = [widget[1, 2*reg], widget[0, 2*reg]]
        vert =  [widget[r, T_patch.col] for r in range(T_patch.row, 0,-1)]
        return vert + hor


def probe_left_nonowning(widget, reg, prefix):
    start_row = prefix[-1].row
    start_col = prefix[-1].col

    left_path = []

    if start_row > 1:
        for c in range(start_col-1, 0, -1):
            if (patch := widget[start_row,c]).route_available():
                left_path.append(patch)
            elif patch.T_available():
                return [patch] + left_path[::-1] + prefix[::-1]
            else:
                break

    next_left_path = []
    for r in range(start_row - 1, 1, -1):
        for c in range(start_col - 1, 0, -1):
            if (patch := widget[r,c]).route_available():
                next_left_path.append(patch)
            elif patch.T_available() and left_path and patch.col >= left_path[-1].col:
                # breakpoint()
                return [patch] + left_path[:start_col - c][::-1] + prefix[:r+2][::-1]
            else:
                break
        left_path = next_left_path

def probe_right_nonowning(widget, reg, prefix):
    start_row = prefix[-1].row
    start_col = prefix[-1].col

    right_path = []

    if start_row > 1:
        for c in range(start_col+1, widget.width - 1):
            if (patch := widget[start_row,c]).route_available():
                right_path.append(patch)
            elif patch.T_available():
                return [patch] + right_path[::-1] + prefix[::-1]
            else:
                break

    next_right_path = []
    for r in range(start_row - 1, 1, -1):
        for c in range(start_col+1, widget.width-1):
            if (patch := widget[r,c]).route_available():
                next_right_path.append(patch)
            elif patch.T_available() and right_path and patch.col <= right_path[-1].col:
                return [patch] + right_path[c - start_col :-1:-1] + prefix[r::-1]
            else:
                break
        right_path = next_right_path
   
def probe_down(widget, reg):
    if widget[0, 2*reg].locked() or widget[0, 2*reg + 1].locked():
        return []
    prefix = [widget[0, 2 * reg], widget[1, 2 * reg]]
    probe_col = 2 * reg
    if reg == 0:
        prefix.append(widget[1, 1])
        probe_col = 1
    for i in range(2, widget.height):
        if (patch := widget[i, probe_col]).route_available():
            prefix.append(patch)
        else:
            break
    return prefix

# T --> reg
def validate_T_path(path):
    # print(path)
    if not path[0].T_available():
        return False
    if not all(p.route_available() for p in path[1:-1]):
        return False
    if path[-1].locked():
        return False
    return True

def vertical_search(widget, reg):
    if widget[0,2*reg].locked():
        return None

    if (T := T_search_owning(widget, reg)) and validate_T_path(path := T_path_owning(widget, reg, T)):
        return path
    
    if not (prefix := probe_down(widget, reg)):
        # breakpoint()
        return None

    # breakpoint()

    if path := probe_left_nonowning(widget, reg, prefix):
        return path

    if path := probe_right_nonowning(widget, reg, prefix):
        return path

    return None


# def print_layers(width, height, output_layers):
#     board = create_default_board(width, height)
#     for r in range(height):
#         for c in range(width):


def print_board(board):
    for row in board:
        for cell in row:
            if cell.patch_type == PatchType.BELL:
                print("$", end='')
            elif cell.locked():
                print(cell.lock.owner.targ, end='')
            elif cell.patch_type == PatchType.REG:
                print("R", end='')
            elif cell.patch_type == PatchType.ROUTE:
                print(" ", end='')
            elif cell.T_available():
                if cell.orientation == PatchOrientation.Z_TOP:
                    print("T", end='')
                else:
                    print("t", end='')
            else:
                print(".", end='')
        print()
    print('-' * len(board[0]))


debug_gates()