from __future__ import annotations
from abc import ABC
from enum import Enum
from typing import Any, List

from .patch import Patch, PatchType
from .transaction import Transaction, TransactionList


class GateType(Enum):
    LOCAL_GATE = 1
    ANCILLA = 2
    T_STATE = 3
    IMPLEMENTATION_DEFINED = 4


class BaseGate(ABC):
    targ: int
    targ_orig: int
    timer: int = 0
    duration: int = 0
    transaction: None | Transaction

    pre: List[BaseGate]
    post: List[BaseGate]
    weight: float = 1
    schedule_weight: float = 0
    flag: Any = None

    def __init__(self):
        self.pre = []
        self.post = []

    def available(self):
        raise NotImplementedError()

    def tick(self):
        """
        Default impl: single stage gate.
        """
        self.timer += 1

    def completed(self) -> bool:
        """
        Returns if gate has completed, and is ready to be retired.
        """
        return self.timer >= self.duration

    def activate(self, *args, **kwargs):
        """
        Start the gate. Generic impl.
        """
        raise NotImplementedError()

    def cleanup(self, scheduler):
        """
        Release held resources. No-op if not overridden.
        """
        pass

    def next(self, scheduler):
        """
        Schedule dependent gates. No-op if not overridden.
        """
        pass


class Gate(BaseGate):
    def available(self):
        """
        Basic gate is always available
        """
        return True

    def activate(self, *args, **kwargs):
        # TODO impl ancilla/single qubit gates
        return super().activate(*args, **kwargs)


class T_Gate(BaseGate):
    targ: int
    targ_orig: int
    timer: int = 0
    duration: int = 0

    pre: List[BaseGate]
    post: List[BaseGate]
    weight: float = 1
    schedule_weight: float = 0

    def __init__(
        self, targ: int, move_duration: int = 4, corr_duration: int = 3, targ_orig=None
    ):
        if targ_orig is None:
            self.targ_orig = targ
        else:
            self.targ_orig = targ_orig

        self.targ: int = targ
        self.gate_type: GateType = GateType.T_STATE
        self.duration = move_duration
        self.correction_duration = corr_duration
        self.state = "JOINT"

        super().__init__()

    def available(self):
        return all(g.completed() for g in self.pre)

    def activate(self, transaction: TransactionList):
        transaction.activate()
        transaction.lock_move(self)
        self.transaction = transaction  # type: ignore

    def cleanup(self, scheduler):
        if self.completed():
            self.transaction.unlock()  # type: ignore
            if self.state == "JOINT":
                self.timer = 0
                self.state = "CORRECTION"
                self.duration = self.correction_duration
                self.transaction.lock_measure(self)  # type: ignore
            else:
                self.transaction.release(scheduler.time)  # type: ignore

    def next(self, scheduler):
        return

    def __repr__(self) -> str:
        str_pre = ",".join([str(x.targ_orig) for x in self.pre])
        str_post = ",".join([str(x.targ_orig) for x in self.post])
        return f"{str_pre}->T{self.targ_orig}({self.targ})->{str_post}"


class MoveGate(BaseGate):
    targ: str
    timer: int = 0
    duration: int

    move_target: None | Patch

    def __init__(self, move_duration: int = 2):
        self.targ = "%"  # type: ignore
        self.gate_type: GateType = GateType.IMPLEMENTATION_DEFINED
        self.duration = move_duration
        self.move_target = None
        super().__init__()

    def available(self):
        return True

    def activate(self, transaction: TransactionList, move_target: Patch):
        transaction.activate()
        transaction.lock_move(self)
        self.transaction = transaction  # type: ignore
        self.move_target = move_target

    def cleanup(self, scheduler):
        if self.completed():
            self.transaction.unlock()  # type: ignore
            self.transaction.release(scheduler.time)  # type: ignore
            self.move_target.patch_type = PatchType.T  # type: ignore

    def next(self, scheduler):
        pass


class RotateGate(BaseGate):
    targ: int
    timer: int = 0
    duration: int = 0

    pre: List[BaseGate]
    post: List[BaseGate]
    weight: float = 1
    schedule_weight: float = 0

    transaction: Transaction

    def __init__(
        self,
        t_patch: Patch,
        rotate_ancilla: Patch,
        reg_patch: Patch,
        rotate_for: T_Gate,
        duration: int,
    ):
        super().__init__()

        self.t_patch = t_patch
        self.t_patch.register_rotation(self)

        self.post.append(rotate_for)
        self.targ = rotate_for.targ
        self.duration = duration

        self.weight = rotate_for.weight
        self.schedule_weight = rotate_for.schedule_weight

        self.lock = None
        self.completed_at = None

        self.transaction = Transaction(  # type: ignore
            [t_patch, rotate_ancilla, reg_patch], []
        )

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
