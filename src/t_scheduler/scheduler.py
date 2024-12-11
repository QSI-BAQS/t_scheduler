from collections import deque
from enum import Enum

from t_scheduler.patch import Patch, PatchOrientation, PatchType, TCultPatch
from t_scheduler.widget import TreeNode
from t_scheduler.gate import RotateGate, GateType

class RotationStrategy(Enum):
    BACKPROP_INIT = 0
    LOOKBACK = 1
    INJECT = 2
    REJECT = 3

class SchedulerException(Exception):
    pass

class Scheduler:
    def __init__(
        self,
        gate_layers,
        widget,
        search,
        rot_strat: RotationStrategy,
        debug: bool = False,
    ):
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

        self.ROTATION_DURATION = 3
        self.time = 0
        self.search = search

        self.hazard = {}

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
            raise SchedulerException("No progress!")

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
        self.active = self.next_active
        self.next_active = []

        self.time += 1

    def alloc_gate(self, gate):
        if gate.gate_type == GateType.T_STATE:
            path = self.search(self.widget, gate.targ)
            # TODO unhack
            if path is None and not self.widget[0, 2 * gate.targ].locked():
                self.hazard[self.time] = self.hazard.get(self.time, 0) + 1
            if path is None:
                return False
            return self.process_rotation(path, gate)

        elif gate.gate_type == GateType.LOCAL_GATE:
            reg = self.widget[0, gate.targ * 2]
            if reg.locked():
                return False
            gate.activate([reg])
            self.active.append(gate)
            return True
        elif gate.gate_type == GateType.ANCILLA:
            reg = self.widget[0, gate.targ * 2]
            anc = self.widget[0, gate.targ * 2 + 1]
            if reg.locked() or anc.locked():
                return False
            gate.activate([reg, anc])
            self.active.append(gate)
            return True

    def process_rotation(self, path, gate):

        T_patch = path[0]
        attack_patch = path[1]

        matching_rotation = (T_patch.row == attack_patch.row) ^ (
            T_patch.orientation == PatchOrientation.Z_TOP
        )

        if matching_rotation:
            T_patch.use()
            gate.activate(path, path[0])
            self.active.append(gate)
        elif T_patch.rotation:
            T_patch.orientation = T_patch.orientation.inverse()
            rotate_gate = T_patch.rotation
            for layer in range(
                rotate_gate.completed_at,
                rotate_gate.completed_at - rotate_gate.duration,
                -1,
            ):
                self.output_layers[layer].remove(rotate_gate.path)
            T_patch.rotation = None
            T_patch.use()
            gate.activate(path, path[0])
            self.active.append(gate)
        elif self.rot_strat == RotationStrategy.BACKPROP_INIT:
            T_patch.orientation = T_patch.orientation.inverse()
            T_patch.use()
            gate.activate(path, path[0])
            self.active.append(gate)
        elif self.rot_strat == RotationStrategy.INJECT:
            # reg_patch = self.widget[0, gate.targ * 2]
            rot_gate = RotateGate(path, gate, self.ROTATION_DURATION)
            rot_gate.activate()
            self.active.append(rot_gate)
        elif self.rot_strat == RotationStrategy.LOOKBACK:
            if not attack_patch.release_time or (
                lookback_cycles := self.time - attack_patch.release_time - 1 <= 0
            ):
                # reg_patch = self.widget[0, gate.targ * 2]
                rot_gate = RotateGate(path, gate, self.ROTATION_DURATION)
                rot_gate.activate()
                self.active.append(rot_gate)
            else:
                lookback_cycles = min(lookback_cycles, self.ROTATION_DURATION)
                rot_gate = RotateGate(path, gate, self.ROTATION_DURATION)
                rot_gate.timer += lookback_cycles
                rot_gate.activate()
                for i in range(lookback_cycles):
                    self.output_layers[-i - 1].append(rot_gate)
                if rot_gate.completed():
                    rot_gate.cleanup(self)
                    rot_gate.next(self)
                else:
                    self.active.append(rot_gate)
        elif self.rot_strat == RotationStrategy.REJECT:
            return False
        else:
            raise NotImplementedError()
        return True

def print_board(board):
    for row in board:
        for cell in row:
            if cell.patch_type == PatchType.BELL:
                print("$", end="")
            elif cell.locked():
                print(cell.lock.owner.targ, end="")
            elif cell.patch_type == PatchType.REG:
                print("R", end="")
            elif cell.patch_type == PatchType.ROUTE:
                print(" ", end="")
            elif cell.T_available():
                if cell.orientation == PatchOrientation.Z_TOP:
                    print("T", end="")
                else:
                    print("t", end="")
            elif cell.patch_type == PatchType.CULTIVATOR:
                print("@", end="")
            else:
                print(".", end="")
        print()
    print("-" * len(board[0]))

