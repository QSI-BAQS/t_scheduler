from __future__ import annotations
from typing import Tuple
from .gate import *

class GSPrepGate(BaseGate):
    targs: Tuple[int, ...]
    timer: int = 0
    duration: int = 0

    pre: List[GSPrepGate]
    post: List[GSPrepGate]

    def __init__(
        self,
        targs: Tuple[int, ...],
        move_duration: int = 2,
        corr_duration: int = 2,
    ):
        """
            Note: targ_orig is only used for repr().
        """
        self.targs = targs

        self.gate_type: GateType = GateType.GRAPH_STATE_PREP
        self.duration = move_duration
        self.correction_duration = corr_duration
        self.state = "JOINT"

        super().__init__()

    def available(self) -> bool:
        return all(g.completed() for g in self.pre)

    def activate(self, transaction: BaseTransaction):
        '''
        Activate this gate with the provided transaction
        '''
        transaction.activate()
        transaction.lock_move(self)
        self.transaction = transaction  # type: ignore

    def cleanup(self, scheduler):
        '''
        Update our state --> setting us to be incomplete if necessary
        '''
        if self.completed():
            self.transaction.unlock()  # type: ignore
            if self.state == "JOINT":
                self.timer = 0
                self.state = "CORRECTION"
                self.duration = self.correction_duration
                self.transaction.lock_measure(self)  # type: ignore
            else:
                self.transaction.release(scheduler.time)  # type: ignore

