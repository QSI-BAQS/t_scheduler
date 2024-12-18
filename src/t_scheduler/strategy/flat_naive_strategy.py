from __future__ import annotations
from typing import Tuple

from ..base import Gate, Patch, PatchOrientation, PatchType, TransactionList

from ..router import DenseTCultivatorBufferRouter, MagicStateFactoryRouter, StandardBusRouter, BaselineRegisterRouter
from ..widget import *
from .strategy import Strategy


class FlatNaiveStrategy(Strategy):
    register_router: BaselineRegisterRouter
    bus_router: StandardBusRouter
    buffer_router: DenseTCultivatorBufferRouter

    def __init__(self, register_router, bus_router, buffer_router):
        self.register_router = register_router
        self.bus_router = bus_router
        self.buffer_router = buffer_router

    def validate_rotation(
        self, gate, register_transaction, bus_transaction, buffer_transaction
    ) -> Gate | None:
        # TODO currently NOOP
        if len(buffer_transaction.move_patches) == 1:
            # Assume all patches in row below routing layer are Z_TOP orientation
            matching_rotation = True
        else:
            # This depends on implementation details of ordering of move_patches in
            # our router
            T_patch = buffer_transaction.move_patches[0]
            attack_patch = buffer_transaction.move_patches[1]

            matching_rotation = (T_patch.row == attack_patch.row) ^ (
                T_patch.orientation == PatchOrientation.Z_TOP
            )
        # TODO add cultivator reset delay + rotation consideration (time incl in cult reset)

        transactions = TransactionList(
            [buffer_transaction, bus_transaction, register_transaction]
        )

        gate.activate(transactions)
        # gate.duration += util.RESET_PLUS_DELAY
        return gate

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
                max(0, reg_col - 1)
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

