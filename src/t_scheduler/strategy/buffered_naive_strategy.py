from __future__ import annotations
from typing import List

from ..router.generic.coordinate_adapter import CoordinateAdapter

from ..base import Gate, PatchOrientation, TransactionList, Patch
from ..base.gate import MoveGate

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
        include_bell: bool = True
    ):
        self.register_router = register_router
        self.bus_router = bus_router
        self.buffer_router = buffer_router
        self.buffer_bus_router = buffer_bus_router
        self.factory_router = factory_router
        self.needs_upkeep = True

        if include_bell:
            self.register_buffer_adapter = CoordinateAdapter([0, bus_router.region.width], [1, buffer_router.region.width + 1])
        else:
            self.register_buffer_adapter = CoordinateAdapter([0, bus_router.region.width], [0, buffer_router.region.width])


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
            T_patch: Patch = buffer_transaction.move_patches[0]
            attack_patch: Patch = buffer_transaction.move_patches[1]

            matching_rotation = (T_patch.local_y == attack_patch.local_y) ^ (
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
        # Check if register is available
        if not (
            register_transaction := self.register_router.request_transaction(
                gate.targ
            )
        ):
            return None

        reg_col: int = register_transaction.connect_col  # type: ignore

        buffer_request_col = self.register_buffer_adapter.above_to_below(reg_col)

        # Check if T is available in the buffer
        if buffer_transaction := self.buffer_router.request_transaction(
            buffer_request_col
        ):

            buffer_output_col = self.register_buffer_adapter.below_to_above(buffer_transaction.connect_col)

            # Try to connect through the bus
            bus_transaction = self.bus_router.request_transaction(
                buffer_output_col, reg_col # type: ignore
            )  # type: ignore

            if bus_transaction:
                return self.validate_rotation(
                    gate, buffer_transaction, bus_transaction, register_transaction
                )

        # Need passthrough column, buffer is empty or blocked.
        if not (
            buffer_transaction := self.buffer_router.request_passthrough(
                buffer_request_col
            )
        ):
            return None

        buffer_bus_col = buffer_transaction.connect_col

        buffer_output_col = self.register_buffer_adapter.below_to_above(buffer_transaction.connect_col)

        # Connect to the register bank 
        if not (bus_transaction := self.bus_router.request_transaction(buffer_output_col, reg_col)):  # type: ignore
            return None


        # See if the passthrough channel can get a T from a factory
        if not (
            factory_transaction := self.factory_router.request_transaction(
                buffer_bus_col
            )
        ):
            return None

        # Connect up through lower routing layer
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

    @staticmethod
    def _get_closest(slots, col):
        if slots[col]: return slots[col]

        for offset in range(1, len(slots)):
            if 0 <= col + offset < len(slots) and slots[col + offset]:
                return slots[col + offset]
            if 0 <= col - offset < len(slots) and slots[col - offset]:
                return slots[col - offset]
        
        return None

    def upkeep(self) -> List[Gate]:
        upkeep_gates = []


        if any(
            t.T_available() for t in self.factory_router.region.available_states
        ):
            
            slots = self.buffer_router.region.get_buffer_slots()

            for state in list(self.factory_router.region.available_states):
                if not state.T_available():
                    continue

                if not (
                    factory_transaction := self.factory_router.request_transaction(
                        state.local_x
                    )
                ) or not (free_slot := self._get_closest(slots, factory_transaction.connect_col)):
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

                slots[buffer_transaction.connect_col] = None # type: ignore

        for trans in self.buffer_router.all_local_upkeep_transactions():
            gate = MoveGate(move_duration=1)  # Local move TODO use constants

            gate.activate(trans, trans.measure_patches[0]) # type: ignore
            upkeep_gates.append(gate)

        return upkeep_gates
