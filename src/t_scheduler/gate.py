from __future__ import annotations
from abc import ABC
from enum import Enum
from typing import Any, List, Set

from t_scheduler.patch import Patch, PatchLock
from t_scheduler.router.transaction import Transaction, TransactionList

class GateType(Enum):
    LOCAL_GATE = 1
    ANCILLA = 2
    T_STATE = 3
    IMPLEMENTATION_DEFINED = 4

class BaseGate(ABC):
    targ: int
    timer: int = 0
    duration: int = 0
    # path: List[Patch]
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

class Gate:
    pass

class T_Gate:
    targ: int
    timer: int = 0
    duration: int = 0

    pre: List[T_Gate]
    post: List[T_Gate]
    weight: float = 1
    schedule_weight: float = 0

    def __init__(self, targ: int, move_duration: int = 4, corr_duration: int = 3):
        self.targ: int = targ
        self.gate_type: GateType = GateType.T_STATE
        self.duration = move_duration
        self.correction_duration = corr_duration
        self.state = "JOINT"
        self.pre = []
        self.post = []

    def activate(self, transaction: TransactionList):
        self.transaction = transaction
        self.transaction.activate()
        self.transaction.lock_move(self)

    def cleanup(self, scheduler):
        if self.completed():
            self.transaction.unlock()
            if self.state == "JOINT":
                self.timer = 0
                self.state = "CORRECTION"
                self.duration = self.correction_duration
                self.transaction.lock_measure(self)
            else:
                self.transaction.release(scheduler.time)

    def available(self):
        return all(g.completed() for g in self.pre)

    def completed(self) -> bool:
        return self.timer >= self.duration

    def next(self, scheduler):
        return

    def tick(self):
        self.timer += 1

    def __repr__(self) -> str:
        return f"{','.join([str(x.targ) for x in self.pre])}->T{self.targ}->{','.join([str(x.targ) for x in self.post])}"


class RotateGate(BaseGate):

    targ: int
    timer: int = 0
    duration: int = 0

    pre: List[T_Gate]
    post: List[T_Gate]
    weight: float = 1
    schedule_weight: float = 0

    def __init__(self, t_patch, rotate_ancilla, reg_patch, rotate_for, duration: int):
        self.pre = []
        self.post = []

        self.t_patch = t_patch
        self.t_patch.register_rotation(self)

        self.post = [rotate_for]
        self.targ = rotate_for.targ
        self.duration = duration

        self.lock = None
        self.completed_at = None

        self.transaction = Transaction([t_patch, rotate_ancilla, reg_patch], [])

    def activate(self):
        self.transaction.activate()
        self.transaction.lock_move(self)

    def cleanup(self, scheduler):
        if self.completed():
            self.transaction.unlock()
            self.completed_at = scheduler.time
            # TODO add method for getting time

    def next(self, scheduler):
        if self.completed():
            self.t_patch.orientation = self.t_patch.orientation.inverse()
            # scheduler.deferred.append(self.dependent_gate)
            # TODO add method for deferring a gate
        pass