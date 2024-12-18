from __future__ import annotations
from typing import Tuple

from ..base import Gate, Patch, PatchOrientation, PatchType, TransactionList
from ..base.gate import GateType

from ..router import TreeFilledBufferRouter, StandardBusRouter, BaselineRegisterRouter
from ..widget import *

from .strategy import Strategy

class TreeRoutingStrategy(Strategy):
    register_router: BaselineRegisterRouter
    bus_router: StandardBusRouter
    buffer_router: TreeFilledBufferRouter

    def __init__(self, register_router, bus_router, buffer_router):
        self.register_router = register_router
        self.bus_router = bus_router
        self.buffer_router = buffer_router

    def validate_rotation(
        self, gate, register_transaction, bus_transaction, buffer_transaction
    ) -> Gate | None:

        if len(buffer_transaction.move_patches) == 1:
            # Assume all patches in row below routing layer are Z_TOP orientation
            matching_rotation = True
        else:
            # This depends on implementation details of ordering of move_patches in
            # TreeFilledBufferRouter (Currently other routers are not supported
            # for this strategy)
            T_patch = buffer_transaction.move_patches[0]
            attack_patch = buffer_transaction.move_patches[1]

            matching_rotation = (T_patch.row == attack_patch.row) ^ (
                T_patch.orientation == PatchOrientation.Z_TOP
            )

        if matching_rotation:
            # All good

            transactions = TransactionList(
                [buffer_transaction, bus_transaction, register_transaction]
            )

            gate.activate(transactions)
            return gate
        else:
            # Major problems -- bug here
            raise Exception("Invalid rotation for chessboard buffer!")

    def alloc_nonlocal(self, gate) -> Gate | None:
        if not (
            register_transaction := self.register_router.request_transaction(
                gate.targ
            )
        ):
            return None

        reg_col: int = register_transaction.connect_col  # type: ignore

        if not (
            buffer_transaction := self.buffer_router.request_transaction(
                reg_col // 2
            )
        ):
            return None

        bus_transaction = self.bus_router.request_transaction(
            buffer_transaction.connect_col + 1, reg_col
        )  # type: ignore

        if not bus_transaction:
            return None
        ############################
        #  Process rotation logic
        ############################
        return self.validate_rotation(
            gate, register_transaction, bus_transaction, buffer_transaction
        )
