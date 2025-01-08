from __future__ import annotations
from enum import Enum
from typing import List

from t_scheduler.base.gate import MoveGate, RotateGate
from t_scheduler.base.patch import TCultPatch
from t_scheduler.base.response import Response, ResponseStatus
from t_scheduler.base.transaction import Transaction

# TODO move into templates
from ..widget.bell_region import BellRegion
from ..router.bell_router import BellRouter

from ..base import Gate, PatchOrientation, TransactionList, constants

from ..router import AbstractRouter
from ..widget import *
from .strategy import Strategy

class RotationStrategyOption(Enum):
    BACKPROP_INIT = 0
    LOOKBACK = 1
    INJECT = 2
    REJECT = 3
    ADD_DELAY = 4


class GenericStrategy(Strategy):
    register_router: AbstractRouter


    def __init__(self, routers, rot_strat = RotationStrategyOption.ADD_DELAY):
        self.register_router = routers[0]
        self.factory_routers = [r for r in routers if r.magic_source]
        self.buffer_routers = [r for r in routers if r.upkeep_accept]
        self.needs_upkeep = bool(self.buffer_routers)
        self.rotation_option = rot_strat


    def validate_rotation(
        self, gate, transaction_list
    ) -> Gate | None:
        buffer_transaction, bus_transaction = transaction_list[:2]
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

        if any(any(isinstance(cell, TCultPatch) for cell in trans.move_patches) for trans in transaction_list[1:]) \
            or any(isinstance(cell, TCultPatch) for cell in buffer_transaction.move_patches[1:]):
            gate.duration += constants.RESET_PLUS_DELAY

        if matching_rotation:
            gate.activate(transaction_list)
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

            gate.activate(transaction_list)
            return gate
        elif self.rotation_option == RotationStrategyOption.ADD_DELAY:
            gate.duration += constants.ROTATE_DELAY

            gate.activate(transaction_list)
            return gate
        elif self.rotation_option == RotationStrategyOption.BACKPROP_INIT:
            # We'll pretend the magic state was generated in the right orientation
            # initially. Track this in the patch.

            T_patch.orientation = T_patch.orientation.inverse()

            gate.activate(transaction_list)
            return gate

        elif self.rotation_option == RotationStrategyOption.INJECT:
            # Inject a rotation gate

            rot_gate = RotateGate(
                T_patch,
                attack_patch,
                transaction_list[-1].measure_patches[0],
                gate,
                constants.ROTATE_DELAY,
            )
            rot_gate.activate()
            return rot_gate  # type: ignore

        # elif self.rotation_option == RotationStrategyOption.LOOKBACK:
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
        elif self.rotation_option == RotationStrategyOption.REJECT:
            return None
        else:
            raise NotImplementedError()


    def return_pass(self, gate, curr_trans, curr_router, upstream_connect): # type: ignore
        transactions = TransactionList([curr_trans])
        downstream_col = curr_trans.connect_col

        while curr_router in upstream_connect:
            upstream_router, downstream_idx, upstream_col = upstream_connect[curr_router]
            # breakpoint()
            translated_downstream = upstream_router.to_local_col(downstream_idx, downstream_col)
            resp: Response = upstream_router.generic_transaction(translated_downstream, upstream_col)
            if not resp.status:
                return None

            transactions.append(resp.transaction)
            curr_router, downstream_col = upstream_router, upstream_col
    
        ############################
        #  Process rotation logic
        ############################
        return self.validate_rotation(
            gate, transactions
        )




    def alloc_nonlocal(self, gate) -> Gate | None:
        # curr: tuple('curr_router', 'curr_downstream_idx', 'curr_request_col')
        # upstream_connect: dict[router -> (upstream_router, downstream_idx, upstream_col)]

        upstream_connect = {}

        curr_router = self.register_router
        resp : Response = self.register_router.generic_transaction(gate.targ) # type: ignore
        if not resp.status:
            return None
        curr_transaction : Transaction = resp.transaction # type: ignore
        dfs_stack = [(curr_router, 0, curr_transaction.connect_col)]

        while dfs_stack:
            curr_router, curr_downstream_idx, curr_request_col = dfs_stack.pop()
            if curr_downstream_idx >= len(curr_router.downstream):
                continue

            # Save state to stack!
            dfs_stack.append((curr_router, curr_downstream_idx + 1, curr_request_col))

            # Recurse!
            downstream_router = curr_router.downstream[curr_downstream_idx]
            downstream_request_col = curr_router.to_downstream_col(curr_downstream_idx, curr_request_col)
            resp : Response = downstream_router.generic_transaction(downstream_request_col)
            if not resp.status:
                # Downstream router rejected!
                continue
            
            upstream_connect[downstream_router] = (curr_router, curr_downstream_idx, curr_request_col)

            
            if resp.status == ResponseStatus.SUCCESS:
                # Resource found in downstream router!
                # Now check if path available...

                return_resp = self.return_pass(gate, resp.transaction, downstream_router, upstream_connect)
                if return_resp:
                    return return_resp
                
                
            # Downstream router gives OK?
            dfs_stack.append((downstream_router, 0, downstream_request_col))

        return None
    
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

        if not self.needs_upkeep:
            return []

        for factory_router in self.factory_routers:
            # TODO cascade down -> buffer reparse if topmost buffer full etc.
            buffer_router = None
            curr_router = factory_router.upstream
            while curr_router:
                if curr_router.upkeep_accept:
                    buffer_router = curr_router
                curr_router = curr_router.upstream
            if not buffer_router:
                continue

            slots = buffer_router.region.get_buffer_slots()
            for state in list(factory_router.region.available_states):
                if not state.T_available():
                    continue

                if not (
                    factory_transaction := factory_router.request_transaction(
                        state.col
                    )
                ) or not (free_slot := self._get_closest(slots, factory_transaction.connect_col)):
                    continue

                if not (
                    buffer_transaction := buffer_router.upkeep_transaction(free_slot)
                ):
                    continue

                transactions = TransactionList([factory_transaction])

                upstream_router = factory_router.upstream
                upstream_col = factory_router.to_local_col(upstream_router.downstream.index(factory_router), factory_transaction.connect_col)
                status = ResponseStatus.SUCCESS
                while upstream_router.upstream != buffer_router:
                    resp = upstream_router.generic_transaction(upstream_col, upstream_col)
                    if not resp.status:
                        status = resp.status
                        break
                    transactions.append(resp.transaction)
                if not status:
                    continue
                
                slot_col = buffer_router.to_downstream_col(buffer_router.downstream.index(upstream_router), buffer_transaction.connect_col)

                if not (
                    bus_transaction := upstream_router.request_transaction(
                        factory_transaction.connect_col, buffer_transaction.connect_col # type: ignore
                    )
                ):  # type: ignore
                    continue
                
                transactions.append(bus_transaction)
                transactions.append(buffer_transaction)

                gate = MoveGate()

                gate.activate(transactions, buffer_transaction.measure_patches[0]) # type: ignore

                upkeep_gates.append(gate)

                slots[buffer_transaction.connect_col] = None # type: ignore

        for buffer_router in self.buffer_routers:
            for trans in buffer_router.all_local_upkeep_transactions():
                gate = MoveGate(move_duration=1)  # Local move TODO use constants

                gate.activate(trans, trans.measure_patches[0]) # type: ignore
                upkeep_gates.append(gate)

        return upkeep_gates

