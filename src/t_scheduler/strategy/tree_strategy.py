from __future__ import annotations
from enum import Enum
from typing import Tuple

from t_scheduler.gate import Gate, GateType, RotateGate
from t_scheduler.patch import Patch, PatchOrientation, PatchType
from t_scheduler.router import vertical_buffer_router
from t_scheduler.router.tree_buffer_router import TreeFilledBufferRouter
from t_scheduler.router.vertical_buffer_router import VerticalFilledBufferRouter
from t_scheduler.router.bus_router import StandardBusRouter
from t_scheduler.router.register_router import BaselineRegisterRouter
from t_scheduler.router.transaction import TransactionList
from t_scheduler.widget.magic_state_buffer import PrefilledMagicStateRegion
from t_scheduler.widget.registers import SingleRowRegisterRegion
from t_scheduler.widget.route_bus import RouteBus
from t_scheduler.widget.widget import Widget
import t_scheduler.util as util


class RotationStrategyOption(Enum):
    BACKPROP_INIT = 0
    LOOKBACK = 1
    INJECT = 2
    REJECT = 3


class TreeRoutingStrategy:
    register_router: BaselineRegisterRouter
    bus_router: StandardBusRouter
    buffer_router: TreeFilledBufferRouter

    @staticmethod
    def with_prefilled_buffer_widget(width, height) -> Tuple[TreeRoutingStrategy, Widget]:
        register_region = SingleRowRegisterRegion(width)
        route_region = RouteBus(width)
        buffer_region = PrefilledMagicStateRegion(
            width - 2, height - 2, 'chessboard')

        board = [register_region.patch_grid[0], route_region.patch_grid[0]]
        for r in range(height - 2):
            row = [
                Patch(PatchType.BELL, r, 0),
                *buffer_region.cells[r],
                Patch(PatchType.BELL, r, width - 1),
            ]
            board.append(row)
        widget = Widget(width, height, board) # Pseudo-widget for output clarity

        strat = TreeRoutingStrategy(BaselineRegisterRouter(register_region),
                                        StandardBusRouter(route_region),
                                        TreeFilledBufferRouter(buffer_region),
                                        rot_strat=RotationStrategyOption.INJECT)
        return strat, widget

    def __init__(self, register_router, bus_router, buffer_router, rot_strat: RotationStrategyOption):
        self.register_router = register_router
        self.bus_router = bus_router
        self.buffer_router = buffer_router
        self.rot_strat = rot_strat

    def validate_rotation(self, gate, register_transaction, bus_transaction, buffer_transaction) -> Gate | None:

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
                [buffer_transaction, bus_transaction, register_transaction])

            gate.activate(transactions)
            return gate
        else:
            # Major problems -- bug here
            raise Exception("Invalid rotation for chessboard buffer!")

    def alloc_gate(self, gate) -> Gate | None:
        if gate.gate_type == GateType.T_STATE:

            if not (register_transaction := self.register_router.request_transaction(gate.targ)):
                return None

            reg_col: int = register_transaction.connect_col  # type: ignore

            if not (buffer_transaction := self.buffer_router.request_transaction(reg_col // 2)):
                return None

            bus_transaction = self.bus_router.request_transaction(
                reg_col, buffer_transaction.connect_col + 1)  # type: ignore

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