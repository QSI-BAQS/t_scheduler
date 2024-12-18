from __future__ import annotations
from typing import Tuple

from t_scheduler.base.gate import Gate, GateType
from t_scheduler.base.patch import Patch, PatchOrientation, PatchType
from t_scheduler.router.cultivator_router import TCultivatorBufferRouter
from t_scheduler.router.factory_router import MagicStateFactoryRouter
from t_scheduler.router.bus_router import StandardBusRouter
from t_scheduler.router.register_router import BaselineRegisterRouter
from t_scheduler.router.transaction import TransactionList
from t_scheduler.strategy.abstract_strategy import AbstractStrategy
from t_scheduler.widget.factory_region import MagicStateFactoryRegion
from t_scheduler.widget.magic_state_buffer import  TCultivatorBufferRegion
from t_scheduler.widget.registers import SingleRowRegisterRegion
from t_scheduler.widget.route_bus import RouteBus
from t_scheduler.widget.widget import Widget

class FlatNaiveStrategy(AbstractStrategy):
    register_router: BaselineRegisterRouter
    bus_router: StandardBusRouter
    buffer_router: TCultivatorBufferRouter

    @staticmethod
    def with_t_cultivator_widget(width, height) -> Tuple[FlatNaiveStrategy, Widget]:
        register_region = SingleRowRegisterRegion(width)
        route_region = RouteBus(width)
        buffer_region = TCultivatorBufferRegion(
            width - 2, height - 2, 'dense')

        board = [register_region.sc_patches[0], route_region.sc_patches[0]]
        for r in range(height - 2):
            row = [
                Patch(PatchType.BELL, r, 0),
                *buffer_region.sc_patches[r],
                Patch(PatchType.BELL, r, width - 1),
            ]
            board.append(row)
        widget = Widget(width, height, board, components=[
                        register_region, route_region, buffer_region])  # Pseudo-widget for output clarity

        strat = FlatNaiveStrategy(BaselineRegisterRouter(register_region),
                                  StandardBusRouter(route_region),
                                  TCultivatorBufferRouter(buffer_region),
                                  )
        return strat, widget

    @staticmethod
    def with_litinski_5x3_unbuffered_widget(width, height) -> Tuple[FlatNaiveStrategy, Widget]:
        register_region = SingleRowRegisterRegion(width)
        route_region = RouteBus(width)
        buffer_region = MagicStateFactoryRegion.with_litinski_5x3(
            width - 2, height - 2)

        board = [register_region.sc_patches[0], route_region.sc_patches[0]]
        for r in range(height - 2):
            row = [
                Patch(PatchType.BELL, r, 0),
                *buffer_region.sc_patches[r],
                Patch(PatchType.BELL, r, width - 1),
            ]
            board.append(row)
        widget = Widget(width, height, board, components=[
                        register_region, route_region, buffer_region])  # Pseudo-widget for output clarity

        strat = FlatNaiveStrategy(BaselineRegisterRouter(register_region),
                                  StandardBusRouter(route_region),
                                  MagicStateFactoryRouter(buffer_region),
                                  )
        return strat, widget

    @staticmethod
    def with_litinski_6x3_dense_unbuffered_widget(width, height) -> Tuple[FlatNaiveStrategy, Widget]:
        register_region = SingleRowRegisterRegion(width)
        route_region = RouteBus(width)
        buffer_region = MagicStateFactoryRegion.with_litinski_6x3_dense(
            width - 2, height - 2)

        board = [register_region.sc_patches[0], route_region.sc_patches[0]]
        for r in range(height - 2):
            row = [
                Patch(PatchType.BELL, r, 0),
                *buffer_region.sc_patches[r],
                Patch(PatchType.BELL, r, width - 1),
            ]
            board.append(row)
        widget = Widget(width, height, board, components=[
                        register_region, route_region, buffer_region])  # Pseudo-widget for output clarity

        strat = FlatNaiveStrategy(BaselineRegisterRouter(register_region),
                                  StandardBusRouter(route_region),
                                  MagicStateFactoryRouter(buffer_region),
                                  )
        return strat, widget

    def __init__(self, register_router, bus_router, buffer_router):
        self.register_router = register_router
        self.bus_router = bus_router
        self.buffer_router = buffer_router

    def validate_rotation(self, gate, register_transaction, bus_transaction, buffer_transaction) -> Gate | None:
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
            [buffer_transaction, bus_transaction, register_transaction])

        gate.activate(transactions)
        # gate.duration += util.RESET_PLUS_DELAY
        return gate

    def alloc_gate(self, gate) -> Gate | None:
        if gate.gate_type == GateType.T_STATE:

            if not (register_transaction := self.register_router.request_transaction(gate.targ)):
                return None

            reg_col: int = register_transaction.connect_col  # type: ignore

            if not (buffer_transaction := self.buffer_router.request_transaction(max(0,reg_col - 1))):
                return None

            bus_transaction = self.bus_router.request_transaction(
                buffer_transaction.connect_col + 1, reg_col)  # type: ignore

            if not bus_transaction:
                return None
            ############################
            #  Process rotation logic
            ############################
            return self.validate_rotation(gate, register_transaction, bus_transaction, buffer_transaction)

        elif gate.gate_type == GateType.LOCAL_GATE:
            if not (register_transaction := self.register_router.request_transaction(gate.targ, request_type='local')):
                return None

            gate.activate(register_transaction)
            return gate

        elif gate.gate_type == GateType.ANCILLA:
            if not (register_transaction := self.register_router.request_transaction(gate.targ, request_type='ancilla')):
                return None

            gate.activate(register_transaction)
            return gate
