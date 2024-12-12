from __future__ import annotations
from enum import Enum
from typing import Tuple

from t_scheduler.gate import Gate, GateType, RotateGate
from t_scheduler.patch import Patch, PatchOrientation, PatchType
from t_scheduler.router import buffer_router
from t_scheduler.router.buffer_router import VerticalFilledBufferRouter
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


class VerticalRoutingStrategy:
    register_router: BaselineRegisterRouter
    bus_router: StandardBusRouter
    buffer_router: VerticalFilledBufferRouter

    @staticmethod
    def with_prefilled_buffer_widget(width, height) -> Tuple[VerticalRoutingStrategy, Widget]:
        register_region = SingleRowRegisterRegion(width)
        route_region = RouteBus(width)
        buffer_region = PrefilledMagicStateRegion(
            width - 2, height - 2, 'default')

        board = [register_region.patch_grid[0], route_region.patch_grid[0]]
        for r in range(height - 2):
            row = [
                Patch(PatchType.BELL, r, 0),
                *buffer_region.cells[r],
                Patch(PatchType.BELL, r, width - 1),
            ]
            board.append(row)
        widget = Widget(width, height, board)

        strat = VerticalRoutingStrategy(BaselineRegisterRouter(register_region),
                                        StandardBusRouter(route_region),
                                        VerticalFilledBufferRouter(buffer_region),
                                        rot_strat=RotationStrategyOption.INJECT)
        return strat, widget

    def __init__(self, register_router, bus_router, buffer_router, rot_strat: RotationStrategyOption):
        self.register_router = register_router
        self.bus_router = bus_router
        self.buffer_router = buffer_router
        self.rot_strat = rot_strat

    def process_rotation(self, gate, register_transaction, bus_transaction, buffer_transaction) -> Gate | None:

        if len(buffer_transaction.move_patches) == 1:
            # Assume all patches in row below routing layer are Z_TOP orientation
            matching_rotation = True
        else:
            # This depends on implementation details of ordering of move_patches in 
            # VerticalFilledBufferRouter (Currently other routers are not supported
            # for this strategy)
            T_patch = buffer_transaction.move_patches[0]
            attack_patch = buffer_transaction.move_patches[1]

            matching_rotation = (T_patch.row == attack_patch.row) ^ (
                T_patch.orientation == PatchOrientation.Z_TOP
            )
        
        if matching_rotation:
            # We are done here -- no need to rotate

            transactions = TransactionList(
                [buffer_transaction, bus_transaction, register_transaction])

            gate.activate(transactions)
            return gate
        

        if T_patch.rotation:
            # We rotated before. Redundant -- so undo rotation


            # TODO: Prune output layers to remove redundant rotation
            # T_patch.orientation = T_patch.orientation.inverse()
            # rotate_gate = T_patch.rotation
            # for layer in range(
            #     rotate_gate.completed_at,
            #     rotate_gate.completed_at - rotate_gate.duration,
            #     -1,
            # ):
            #     self.output_layers[layer].remove(rotate_gate.path)

            T_patch.rotation = None
            transactions = TransactionList(
                [buffer_transaction, bus_transaction, register_transaction])

            gate.activate(transactions)
            return gate
        
        elif self.rot_strat == RotationStrategyOption.BACKPROP_INIT:
            # We'll pretend the magic state was generated in the right orientation 
            # initially. Track this in the patch.

            T_patch.orientation = T_patch.orientation.inverse()
            transactions = TransactionList(
                [buffer_transaction, bus_transaction, register_transaction])

            gate.activate(transactions)
            return gate
        
        elif self.rot_strat == RotationStrategyOption.INJECT:
            # Inject a rotation gate

            rot_gate = RotateGate(T_patch, attack_patch, register_transaction.measure_patches[0], gate, util.ROTATE_DELAY)
            rot_gate.activate()
            return rot_gate # type: ignore
        
        # elif self.rot_strat == RotationStrategyOption.LOOKBACK:
        #     if not attack_patch.release_time or (
        #         lookback_cycles := self.time - attack_patch.release_time - 1 <= 0
        #     ):
        #         # reg_patch = self.widget[0, gate.targ * 2]
        #         rot_gate = RotateGate(path, gate, self.ROTATION_DURATION)
        #         rot_gate.activate()
        #         self.active.append(rot_gate)
        #     else:
        #         lookback_cycles = min(lookback_cycles, self.ROTATION_DURATION)
        #         rot_gate = RotateGate(path, gate, self.ROTATION_DURATION)
        #         rot_gate.timer += lookback_cycles
        #         rot_gate.activate()
        #         for i in range(lookback_cycles):
        #             self.output_layers[-i - 1].append(rot_gate)
        #         if rot_gate.completed():
        #             rot_gate.cleanup(self)
        #             rot_gate.next(self)
        #         else:
        #             self.active.append(rot_gate)
        # TODO inject current cycle time / interfact for past injection
        elif self.rot_strat == RotationStrategyOption.REJECT:
            return None
        else:
            raise NotImplementedError()

    def alloc_gate(self, gate) -> Gate | None:
        if gate.gate_type == GateType.T_STATE:

            if not (register_transaction := self.register_router.request_transaction(gate.targ)):
                return None

            reg_col: int = register_transaction.connect_col  # type: ignore

            # TODO remove assumption of 2-wide registers and add enum
            buffer_cols = []
            if reg_col > 0 and self.bus_router.request_transaction(reg_col, reg_col):
                buffer_cols.append(reg_col - 1)
            if reg_col < self.bus_router.route_bus.width - 1 and self.bus_router.request_transaction(reg_col, reg_col + 1):
                buffer_cols.append(reg_col)

            if not (buffer_transaction := self.buffer_router.request_transaction(buffer_cols)):
                return None

            bus_transaction = self.bus_router.request_transaction(
                reg_col, buffer_transaction.connect_col + 1)  # type: ignore

           
            ############################
            #  Process rotation logic
            ############################
            return self.process_rotation(gate, register_transaction, bus_transaction, buffer_transaction)

            # return self.process_rotation(path, gate)

    #     elif gate.gate_type == GateType.LOCAL_GATE:
    #         reg = self.widget[0, gate.targ * 2]
    #         if reg.locked():
    #             return False
    #         gate.activate([reg])
    #         self.active.append(gate)
    #         return True
    #     elif gate.gate_type == GateType.ANCILLA:
    #         reg = self.widget[0, gate.targ * 2]
    #         anc = self.widget[0, gate.targ * 2 + 1]
    #         if reg.locked() or anc.locked():
    #             return False
    #         gate.activate([reg, anc])
    #         self.active.append(gate)
    #         return True
