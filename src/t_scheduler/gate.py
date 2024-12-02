from __future__ import annotations
from abc import ABC
from enum import Enum
from typing import Any, List, Set

from t_scheduler.patch import Patch, PatchLock


class GateType(Enum):
    LOCAL_GATE = 1
    ANCILLA = 2
    T_STATE = 3
    IMPLEMENTATION_DEFINED = 4


class BaseGate(ABC):
    targ: int
    timer: int = 0
    duration: int = 0
    path: List[Patch]
    lock: None | PatchLock

    pre: List[BaseGate] | Set[BaseGate]
    post: List[BaseGate] | Set[BaseGate]
    weight: float = 1
    schedule_weight: float = 0
    flag: Any = None

    def __init__(self):
        self.pre = []
        self.post = []

    def available(self):
        # TODO: implement for when converting to dependency graph
        return True

    def tick(self):
        self.timer += 1

    def completed(self) -> bool:
        return self.timer >= self.duration

    def activate(self):
        """
            Start the gate
        """
        self.lock = PatchLock(self, self.path, self.duration)
        self.lock.lock()

    def cleanup(self, scheduler):
        """
            Release held resources
        """
        pass

    def next(self, scheduler):
        """
            Schedule dependent gates
        """
        pass


class Gate(BaseGate):
    def __init__(self, targ, gate_type=GateType.T_STATE, duration=1):
        super().__init__()
        self.targ: int = targ
        self.lock: None | PatchLock = None
        self.gate_type: GateType = gate_type
        self.duration = duration

    def activate(self, path):
        self.path = path
        super().activate()

    def cleanup(self, scheduler):
        if self.completed():
            assert self.lock is not None
            self.lock.unlock()


class T_Gate(Gate):
    def __init__(self, targ: int, measure_duration: int = 1, corr_duration: int = 3):
        super().__init__(targ, GateType.T_STATE, measure_duration)
        self.duration = measure_duration
        self.correction_duration = corr_duration

    def activate(self, path, t_patch: Patch):
        self.t_patch = t_patch
        self.t_patch.use()

        super().activate(path)

    def cleanup(self, scheduler):
        if self.completed():
            assert self.lock is not None
            self.lock.unlock()

    def next(self, scheduler):
        if self.completed():
            c_gate = CorrectionGate(
                self.path[-1], self.path[0], self.correction_duration)
            c_gate.activate()
            scheduler.next_active.append(c_gate)
            # TODO add schedule_next to scheduler

    def __repr__(self) -> str:
        return f"{','.join([str(x.targ) for x in self.pre])}->T{self.targ}->{','.join([str(x.targ) for x in self.post])}"

class RotateGate(BaseGate):
    def __init__(self, path: List[Patch], dependent_gate: Gate, duration: int):
        """
        path must be in order [Reg --> Routing --> T_State]
        """
        self.t_patch = path[0]
        self.t_patch.register_rotation(self)

        self.path = [path[0], path[1], path[-1]]
        self.dependent_gate = dependent_gate
        self.lock = None
        self.targ = dependent_gate.targ
        self.duration = duration

        self.completed_at = None

    def cleanup(self, scheduler):
        if self.completed():
            assert self.lock is not None
            self.lock.unlock()
            self.completed_at = scheduler.time
            # TODO add method for getting time

    def next(self, scheduler):
        if self.completed():
            self.t_patch.orientation = self.t_patch.orientation.inverse()
            scheduler.deferred.append(self.dependent_gate)
            # TODO add method for deferring a gate


class CorrectionGate(BaseGate):
    def __init__(self, reg_patch: Patch, t_patch: Patch, duration: int):
        self.reg_patch = reg_patch
        self.t_patch = t_patch

        self.path = [reg_patch, t_patch]
        self.lock = None
        self.targ = reg_patch.col // 2
        self.duration = duration

    def cleanup(self, scheduler):
        if self.completed():
            assert self.lock is not None
            self.lock.unlock()
            self.t_patch.release(scheduler.time)
            # TODO add get time method
