from __future__ import annotations
from typing import Callable, List, Tuple

from ..base import Gate, Patch, PatchOrientation, PatchType, TransactionList
from ..base.gate import GateType, MoveGate

from ..router import MagicStateFactoryRouter, RechargableBufferRouter, StandardBusRouter, BaselineRegisterRouter
from ..widget import *

from .strategy import Strategy

class BufferedNaiveStrategy(Strategy):
    register_router: BaselineRegisterRouter
    bus_router: StandardBusRouter
    buffer_router: RechargableBufferRouter
    buffer_bus_router: StandardBusRouter
    factory_router: MagicStateFactoryRouter

    def __init__(
        self,
        register_router,
        bus_router,
        buffer_router,
        buffer_bus_router,
        factory_router,
    ):
        self.register_router = register_router
        self.bus_router = bus_router
        self.buffer_router = buffer_router
        self.buffer_bus_router = buffer_bus_router
        self.factory_router = factory_router
        self.needs_upkeep = True

    def validate_rotation(
        self, gate, buffer_transaction, bus_transaction, *other_transactions
    ) -> Gate | None:
        '''
            Check if the rotation matches what we need.
        '''

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
            [buffer_transaction, bus_transaction, *other_transactions]
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

        if buffer_transaction := self.buffer_router.request_transaction(
            max(0, reg_col - 1)
        ):

            bus_transaction = self.bus_router.request_transaction(
                buffer_transaction.connect_col + 1, reg_col # type: ignore
            )  # type: ignore

            if bus_transaction:
                return self.validate_rotation(
                    gate, buffer_transaction, bus_transaction, register_transaction
                )

        # Need passthrough
        if not (
            buffer_transaction := self.buffer_router.request_passthrough(
                max(0, reg_col - 1)
            )
        ):
            return None

        buffer_bus_col = buffer_transaction.connect_col

        if not (bus_transaction := self.bus_router.request_transaction(buffer_bus_col + 1, reg_col)):  # type: ignore
            return None

        if not (
            factory_transaction := self.factory_router.request_transaction(
                buffer_bus_col
            )
        ):
            return None

        buffer_bus_transaction = self.buffer_bus_router.request_transaction(
            factory_transaction.connect_col, buffer_bus_col # type: ignore
        )
        if not buffer_bus_transaction:
            return None

        return self.validate_rotation(
            gate,
            factory_transaction,
            buffer_bus_transaction,
            buffer_transaction,
            bus_transaction,
            register_transaction,
        )

    def upkeep(self) -> List[Gate]:
        if not any(
            t.T_available() for t in self.factory_router.region.available_states
        ):
            return []

        slots = self.buffer_router.buffer.get_buffer_slots()

        upkeep_gates = []

        for state in list(self.factory_router.region.available_states):
            if not state.T_available():
                continue

            if not (
                factory_transaction := self.factory_router.request_transaction(
                    state.col
                )
            ) or not (free_slot := slots[state.col]):
                continue

            if not (
                buffer_transaction := self.buffer_router.upkeep_transaction(free_slot)
            ):
                continue

            if not (
                bus_transaction := self.buffer_bus_router.request_transaction(
                    factory_transaction.connect_col, buffer_transaction.connect_col # type: ignore
                )
            ):  # type: ignore
                continue

            gate = MoveGate()

            transactions = TransactionList(
                [factory_transaction, bus_transaction, buffer_transaction]
            )

            gate.activate(transactions, buffer_transaction.measure_patches[0]) # type: ignore

            upkeep_gates.append(gate)

        for trans in self.buffer_router.all_local_upkeep_transactions():
            gate = MoveGate(move_duration=1)  # Local move TODO use constants

            gate.activate(trans, trans.measure_patches[0]) # type: ignore
            upkeep_gates.append(gate)
        return upkeep_gates
