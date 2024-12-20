from __future__ import annotations


from ..base import Gate, PatchOrientation, TransactionList, constants

from ..router import StandardBusRouter, BaselineRegisterRouter, AbstractRouter
from ..router.generic.coordinate_adapter import CoordinateAdapter
from ..widget import *
from .strategy import Strategy


class FlatNaiveStrategy(Strategy):
    register_router: BaselineRegisterRouter
    bus_router: StandardBusRouter
    magic_state_router: AbstractRouter

    def __init__(self, register_router, bus_router, buffer_router, include_bell: bool = True):
        self.register_router = register_router
        self.bus_router = bus_router
        self.magic_state_router = buffer_router

        if include_bell:
            self.bus_magic_adapter = CoordinateAdapter([0, bus_router.region.width], [1, buffer_router.region.width + 1])
        else:
            self.bus_magic_adapter = CoordinateAdapter([0, bus_router.region.width], [0, buffer_router.region.width])

    def validate_rotation(
        self, gate, register_transaction, bus_transaction, buffer_transaction
    ) -> Gate | None:
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

        transactions = TransactionList(
            [buffer_transaction, bus_transaction, register_transaction]
        )

        gate.activate(transactions)
        if not matching_rotation:
            gate.duration += constants.ROTATE_DELAY
        if len(buffer_transaction.move_patches) > 1:
            gate.duration += constants.RESET_PLUS_DELAY
        return gate

    def alloc_nonlocal(self, gate) -> Gate | None:
        if not (
            register_transaction := self.register_router.request_transaction(
                gate.targ
            )
        ):
            return None

        reg_col: int = register_transaction.connect_col  # type: ignore

        buffer_request_col = self.bus_magic_adapter.above_to_below(reg_col)

        if not (
            buffer_transaction := self.magic_state_router.request_transaction(
                buffer_request_col
            )
        ):
            return None

        buffer_output_col = self.bus_magic_adapter.below_to_above(buffer_transaction.connect_col)

        bus_transaction = self.bus_router.request_transaction(
            buffer_output_col, reg_col
        )  # type: ignore

        if not bus_transaction:
            return None
        ############################
        #  Process rotation logic
        ############################
        return self.validate_rotation(
            gate, register_transaction, bus_transaction, buffer_transaction
        )

