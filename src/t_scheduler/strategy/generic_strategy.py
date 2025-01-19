from __future__ import annotations
from enum import Enum
from typing import List

from ..base.patch import TCultPatch
from ..base.gate import MoveGate, RotateGate
from ..base import constants

from ..base import *

from ..router import AbstractRouter, AbstractFactoryRouter, RechargableBufferRouter
from ..widget import *
from .base_strategy import BaseStrategy

class RotationStrategyOption(Enum):
    BACKPROP_INIT = 0
    LOOKBACK = 1
    INJECT = 2
    REJECT = 3
    ADD_DELAY = 4

class DummyMapper:
    def __init__(self, reg_width = 1):
        self.reg_width = reg_width

    def __getitem__(self, idx:int):
        return idx
    
    def position_xy(self, idx:int):
        return (idx * self.reg_width, 0)

class GenericStrategy(BaseStrategy):
    register_router: AbstractRouter


    def __init__(self, routers, rot_strat = RotationStrategyOption.ADD_DELAY, mapper=DummyMapper()):
        self.register_router = routers[0]
        self.factory_routers: List[AbstractFactoryRouter] = [r for r in routers if r.magic_source]
        self.buffer_routers: List[RechargableBufferRouter] = [r for r in routers if r.upkeep_accept]
        self.needs_upkeep = bool(self.buffer_routers)
        self.rotation_option = rot_strat

        self.mapper = mapper

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
            T_patch: Patch = buffer_transaction.move_patches[0]
            attack_patch: Patch = buffer_transaction.move_patches[1]

            matching_rotation = (T_patch.local_y == attack_patch.local_y) ^ (
                T_patch.orientation == PatchOrientation.Z_TOP
            )

        # Ignoring magic state patch, if any cell is a cultivator patch we must pay for a reset
        if any(any(isinstance(cell, TCultPatch) for cell in trans.move_patches) for trans in transaction_list[1:]) \
            or any(isinstance(cell, TCultPatch) for cell in buffer_transaction.move_patches[1:]):
            gate.duration += constants.RESET_PLUS_DELAY

        if matching_rotation:
            # We're matching. All done!
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


    def return_pass(self, gate, curr_trans, downstream_patch, curr_router, upstream_connect): # type: ignore
        transactions = TransactionList([curr_trans])
        initial = curr_router
        while curr_router in upstream_connect:
            upstream_router, downstream_idx, upstream_patch, *abs_pos = upstream_connect[curr_router]
            # translated_downstream = upstream_router.to_local_col(downstream_idx, downstream_col)
            translated_downstream = downstream_patch.x - upstream_router.region.offset[1]
            upstream_col = upstream_patch.x - upstream_router.region.offset[1]
            if abs_pos:
                resp: Response = upstream_router.generic_transaction(abs_pos, upstream_col)
            else:
                resp: Response = upstream_router.generic_transaction(translated_downstream, upstream_col)
            if not resp.status:
                return None

            transactions.append(resp.transaction)
            curr_router, downstream_col = upstream_router, upstream_col
            downstream_patch = upstream_patch

        self.validate(transactions)

        ############################
        #  Process rotation logic
        ############################
        return self.validate_rotation(
            gate, transactions
        )

    @staticmethod
    def validate(transaction_list):
        path = []
        for transaction in transaction_list:
            path += transaction.move_patches
        # print([(p.x, p.y) for p in path])
        for i in range(len(path) - 1):
            if abs(path[i].x - path[i+1].x) + abs(path[i].y - path[i+1].y) > 1:
                assert False




    def alloc_nonlocal(self, gate) -> Gate | None:
        # curr: tuple('curr_router', 'curr_downstream_idx', 'curr_request_col')
        # upstream_connect: dict[router -> (upstream_router, downstream_idx, upstream_col)]

        target_pos = self.mapper.position_xy(gate.targ)[::-1] # (x, y) -> (row, col)

        upstream_connect = {}

        curr_router = self.register_router
        resp : Response = self.register_router.generic_transaction(target_pos) # type: ignore
        if not resp.status:
            return None
        reg_transaction : Transaction = resp.transaction # type: ignore
        # stack layout: tuple(curr_router, curr_downstream_idx, input_pos, )
        dfs_stack = [(curr_router, 0, resp.upstream_patch, *target_pos)]

        while dfs_stack:
            curr_router, curr_downstream_idx, curr_patch, *abs_pos = dfs_stack.pop()
            if curr_downstream_idx >= len(curr_router.downstream):
                continue

            # Save state to stack!
            dfs_stack.append((curr_router, curr_downstream_idx + 1, curr_patch))

            # Recurse!
            downstream_router = curr_router.downstream[curr_downstream_idx]
            # downstream_request_col = curr_router.to_downstream_col(curr_downstream_idx, curr_request_col)
            downstream_request_col = curr_patch.x - downstream_router.region.offset[1]
            resp : Response = downstream_router.generic_transaction(downstream_request_col)
            if not resp.status:
                # Downstream router rejected!
                continue
            
            upstream_connect[downstream_router] = (curr_router, curr_downstream_idx, curr_patch, *abs_pos)

            
            if resp.status == ResponseStatus.SUCCESS:
                # Resource found in downstream router!
                # Now check if path available...

                return_resp = self.return_pass(gate, resp.transaction, resp.upstream_patch, downstream_router, upstream_connect)
                if return_resp:
                    return return_resp
                
                
            # Downstream router gives OK?
            dfs_stack.append((downstream_router, 0, resp.downstream_patch))

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
            # Currently we always use the topmost buffer
            buffer_router: RechargableBufferRouter | None = None
            curr_router = factory_router.upstream
            while curr_router:
                if curr_router.upkeep_accept:
                    buffer_router = curr_router # type: ignore
                curr_router = curr_router.upstream
            if not buffer_router:
                continue
            
            if not factory_router.region.available_states:
                continue

            slots = buffer_router.region.get_buffer_slots()
            for state in list(factory_router.region.available_states):
                if not state.T_available():
                    continue

                if not (
                    (factory_resp := factory_router.generic_transaction(
                        state.local_x
                    )).status): continue
                factory_transaction = factory_resp.transaction
                local_col = factory_resp.upstream_patch.x - buffer_router.region.offset[1]

                if not (free_slot := self._get_closest(slots, local_col)):
                    continue

                if not (
                    buffer_transaction := buffer_router.upkeep_transaction(free_slot)
                ):
                    continue

                transactions = TransactionList([factory_transaction])

                upstream_router: AbstractRouter = factory_router.upstream # type: ignore
                upstream_patch = factory_resp.upstream_patch
                status = ResponseStatus.SUCCESS
                while upstream_router.upstream != buffer_router:
                    upstream_col = upstream_patch.x - upstream_router.region.offset[1]
                    resp = upstream_router.generic_transaction(upstream_col, upstream_col)
                    if not resp.status:
                        status = resp.status
                        break
                    transactions.append(resp.transaction)
                    upstream_patch = resp.upstream_patch
                    upstream_router = upstream_router.upstream # type: ignore
                if not status:
                    continue
                
                if not (
                    (bus_resp := upstream_router.generic_transaction(
                        upstream_patch.x - upstream_router.region.offset[1], free_slot.x - upstream_router.region.offset[1] # type: ignore
                    )).status
                ):  # type: ignore
                    continue
                bus_transaction = bus_resp.transaction
                
                transactions.append(bus_transaction)
                transactions.append(buffer_transaction)

                self.validate(transactions)

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

