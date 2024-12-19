from __future__ import annotations
from enum import Enum
from typing import Literal, Tuple

from ..base import constants
from ..base import Gate, Patch, PatchOrientation, PatchType, TransactionList
from ..base.gate import RotateGate

from ..router import VerticalFilledBufferRouter, StandardBusRouter, BaselineRegisterRouter, CombRegisterRouter
from ..widget import *

from .strategy import Strategy

class RotationStrategyOption(Enum):
    BACKPROP_INIT = 0
    LOOKBACK = 1
    INJECT = 2
    REJECT = 3


class VerticalRoutingStrategy(Strategy):
    register_router: BaselineRegisterRouter
    bus_router: StandardBusRouter
    buffer_router: VerticalFilledBufferRouter

    def __init__(
        self,
        register_router,
        bus_router,
        buffer_router,
        rot_strat: RotationStrategyOption,
        register_width: Literal[1, 2] = 2,
        has_bell_states: bool = True
    ):
        self.register_router = register_router
        self.bus_router = bus_router
        self.buffer_router = buffer_router
        self.rot_strat = rot_strat
        self.register_width = register_width
        self.has_bell_states = has_bell_states
        # TODO impl no bell state 

        if rot_strat == RotationStrategyOption.LOOKBACK:
            raise NotImplementedError()

    def process_rotation(
        self, gate, register_transaction, bus_transaction, buffer_transaction
    ) -> Gate | None:

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
                [buffer_transaction, bus_transaction, register_transaction]
            )

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
                [buffer_transaction, bus_transaction, register_transaction]
            )

            gate.activate(transactions)
            return gate

        elif self.rot_strat == RotationStrategyOption.BACKPROP_INIT:
            # We'll pretend the magic state was generated in the right orientation
            # initially. Track this in the patch.

            T_patch.orientation = T_patch.orientation.inverse()
            transactions = TransactionList(
                [buffer_transaction, bus_transaction, register_transaction]
            )

            gate.activate(transactions)
            return gate

        elif self.rot_strat == RotationStrategyOption.INJECT:
            # Inject a rotation gate

            rot_gate = RotateGate(
                T_patch,
                attack_patch,
                register_transaction.measure_patches[0],
                gate,
                constants.ROTATE_DELAY,
            )
            rot_gate.activate()
            return rot_gate  # type: ignore

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

    def alloc_nonlocal(self, gate) -> Gate | None:
        if not (
            register_transaction := self.register_router.request_transaction(
                gate.targ
            )
        ):
            return None

        reg_col: int = register_transaction.connect_col  # type: ignore

        # TODO remove assumption of 2-wide registers and add enum
        if self.register_width == 2:
            buffer_cols = []
            if reg_col > 0 and self.bus_router.request_transaction(reg_col, reg_col):
                buffer_cols.append(reg_col - 1)
            if (
                reg_col < self.bus_router.route_bus.width - 2
                and self.bus_router.request_transaction(reg_col, reg_col + 1)
            ):
                buffer_cols.append(reg_col)
        else:
            buffer_cols = [self.clamp(reg_col - 1, 0, self.bus_router.route_bus.width - 3)]



        if not (
            buffer_transaction := self.buffer_router.request_transaction(
                buffer_cols
            )
        ):
            return None

        bus_transaction = self.bus_router.request_transaction(
            buffer_transaction.connect_col + 1, reg_col
        )  # type: ignore

        ############################
        #  Process rotation logic
        ############################
        return self.process_rotation(
            gate, register_transaction, bus_transaction, buffer_transaction
        )

        # return self.process_rotation(path, gate)