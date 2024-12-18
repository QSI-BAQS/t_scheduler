from __future__ import annotations
from typing import Callable, List, Tuple

from ..base import Gate, Patch, PatchOrientation, PatchType, TransactionList
from ..base.gate import GateType, MoveGate

from ..router.factory_router import MagicStateFactoryRouter
from ..router.rechargable_router import RechargableBufferRouter
from ..router.bus_router import StandardBusRouter
from ..router.register_router import BaselineRegisterRouter
from ..widget.factory_region import MagicStateFactoryRegion
from ..widget.magic_state_buffer import MagicStateBufferRegion
from ..widget.register_region import SingleRowRegisterRegion
from ..widget.route_bus import RouteBus
from ..widget.widget import Widget

from .strategy import Strategy

class BufferedNaiveStrategy(Strategy):
    register_router: BaselineRegisterRouter
    bus_router: StandardBusRouter
    buffer_router: RechargableBufferRouter
    buffer_bus_router: StandardBusRouter
    factory_router: MagicStateFactoryRouter

    @staticmethod
    def with_buffered_widget(
        width,
        height,
        buffer_height,
        factory_factory: Callable[[int, int], MagicStateFactoryRegion],
    ) -> Tuple[BufferedNaiveStrategy, Widget]:
        register_region = SingleRowRegisterRegion(width)
        route_region = RouteBus(width)
        buffer_region = MagicStateBufferRegion(width - 2, buffer_height)
        buffer_bus_region = RouteBus(width - 2)
        factory_region = factory_factory(width - 2, height - 3 - buffer_height)

        board = [register_region.sc_patches[0], route_region.sc_patches[0]]
        for r in range(buffer_height):
            row = [
                Patch(PatchType.BELL, r, 0),
                *buffer_region.sc_patches[r],
                Patch(PatchType.BELL, r, width - 1),
            ]
            board.append(row)

        board.append(
            [
                Patch(PatchType.BELL, r, 0),
                *buffer_bus_region.sc_patches[0],
                Patch(PatchType.BELL, r, width - 1),
            ]
        )

        for r in range(factory_region.height):
            row = [
                Patch(PatchType.BELL, r, 0),
                *factory_region.sc_patches[r],
                Patch(PatchType.BELL, r, width - 1),
            ]
            board.append(row)
        widget = Widget(
            width,
            height,
            board,
            components=[
                register_region,
                route_region,
                buffer_region,
                buffer_bus_region,
                factory_region,
            ],
        )  # Pseudo-widget for output clarity

        strat = BufferedNaiveStrategy(
            BaselineRegisterRouter(register_region),
            StandardBusRouter(route_region),
            RechargableBufferRouter(buffer_region),
            StandardBusRouter(buffer_bus_region),
            MagicStateFactoryRouter(factory_region),
        )
        return strat, widget

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
                buffer_transaction.connect_col + 1, reg_col
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
            factory_transaction.connect_col, buffer_bus_col
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
                    factory_transaction.connect_col, buffer_transaction.connect_col
                )
            ):  # type: ignore
                continue

            gate = MoveGate()

            transactions = TransactionList(
                [factory_transaction, bus_transaction, buffer_transaction]
            )

            gate.activate(transactions, buffer_transaction.measure_patches[0])

            upkeep_gates.append(gate)

        for trans in self.buffer_router.all_local_upkeep_transactions():
            gate = MoveGate(move_duration=1)  # Local move TODO use constants

            gate.activate(trans, trans.measure_patches[0])
            upkeep_gates.append(gate)
        return upkeep_gates
