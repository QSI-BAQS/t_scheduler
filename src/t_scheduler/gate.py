from __future__ import annotations
from abc import ABC
from enum import Enum
from typing import Any, List, Set

from t_scheduler.patch import Patch, PatchLock
from t_scheduler.router.transaction import TransactionList

class GateType(Enum):
    LOCAL_GATE = 1
    ANCILLA = 2
    T_STATE = 3
    IMPLEMENTATION_DEFINED = 4

class BaseGate:
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
