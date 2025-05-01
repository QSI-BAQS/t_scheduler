from __future__ import annotations
from enum import Enum
from typing import List

from ..tracker import *

from ..base.patch import TCultPatch
from ..base.gate import MoveGate, RotateGate
from ..base import constants

from ..base import *

from ..router import AbstractRouter, AbstractFactoryRouter, RechargableBufferRouter, StandardBusRouter
from ..region import *
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

        self.routers = routers

        self.vol_tracker: SpaceTimeVolumeTracker | None = None

    def register_vol_tracker(self, vol_tracker):
        for r in self.routers:
            r.vol_tracker = vol_tracker
        self.vol_tracker = vol_tracker
        for r in self.factory_routers:
            for f in r.region.factories:
                f.vol_tracker = vol_tracker

    def validate_rotation(
        self, gate, transaction_list
    ) -> Gate | None:
        # print([(p.y,p.x) for p in transaction_list[0].move_patches])
        buffer_transaction, bus_transaction = transaction_list[:2]
        if len(buffer_transaction.move_patches) == 1:
            # Assume all patches in row below routing layer are Z_TOP orientation
            matching_rotation = True
        else:
            # This depends on implementation details of ordering of move_patches in
            # our router
            T_patch: Patch = buffer_transaction.move_patches[0]
            attack_patch: Patch = buffer_transaction.move_patches[1]

            matching_rotation = (T_patch.y == attack_patch.y) ^ (
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


        # stack layout: tuple(curr_router, curr_downstream_idx, input_pos | source)
        dfs_stack = [(self.register_router, 0, self.register_router.region[target_pos])] # type: ignore

        while dfs_stack:
            curr_router, curr_downstream_idx, source_patch = dfs_stack.pop()
            if len(curr_router.downstream) == 0:
                resp : Response = curr_router.generic_transaction(source_patch, gate_type=gate.gate_type)

                if resp.status == ResponseStatus.SUCCESS:
                    # Resource found in curr router!
                    # Now check if path available...

                    return_resp = self.return_pass(gate, resp.transaction, resp.upstream_patch, downstream_router, upstream_connect)
                    if return_resp:
                        return return_resp
                continue
            elif curr_downstream_idx >= len(curr_router.downstream):
                continue

            # Save state to stack!
            dfs_stack.append((curr_router, curr_downstream_idx + 1, source_patch))

            # Recurse!
            downstream_router = curr_router.downstream[curr_downstream_idx]

            resp : Response = curr_router.generic_transaction(source_patch, target_orientation=downstream_router.region.rotation, gate_type=gate.gate_type) # type: ignore
            if resp.status == ResponseStatus.SUCCESS:
                # Resource found in curr router!
                # Now check if path available...

                return_resp = self.return_pass(gate, resp.transaction, resp.upstream_patch, curr_router, upstream_connect)
                if return_resp:
                    return return_resp

            elif not resp.status:
                continue

            dfs_stack.append((downstream_router, 0, resp.downstream_patch))

            upstream_connect[downstream_router] = (curr_router, curr_downstream_idx, source_patch)

        return None



    def return_pass(self, gate, curr_trans, downstream_patch, curr_router, upstream_connect): # type: ignore
        # print()
        transactions = TransactionList([curr_trans])
        initial = curr_router
        while curr_router in upstream_connect:
            upstream_router, downstream_idx, upstream_patch, *abs_pos = upstream_connect[curr_router]
            # translated_downstream = upstream_router.to_local_col(downstream_idx, downstream_col)
            translated_downstream = downstream_patch.x - upstream_router.region.offset[1]
            upstream_col = upstream_patch.x - upstream_router.region.offset[1]
            # print(upstream_router, translated_downstream, (downstream_patch.x, downstream_patch.y), upstream_col, (upstream_patch.x, upstream_patch.y))
            if upstream_router == self.register_router:
                resp: Response = upstream_router.generic_transaction(upstream_patch, upstream_col, target_orientation=curr_router.region.rotation, gate_type=gate.gate_type)
            else:
                resp: Response = upstream_router.generic_transaction(downstream_patch, upstream_patch, gate_type=gate.gate_type)
            
            if resp.status == ResponseStatus.SUCCESS:
                transactions = TransactionList()

            if not resp.status:
                return None

            transactions.append(resp.transaction)
            curr_router, downstream_col = upstream_router, upstream_col
            downstream_patch = resp.upstream_patch

        self.validate(transactions)

        ############################
        #  Process rotation logic
        ############################
        result = self.validate_rotation(
            gate, transactions
        )
        if result:
            reg_trans = transactions[-1]
            def _reg_callback(trans):
                if trans.measure_patches[0].reg_vol_tag is not None:
                    trans.measure_patches[0].reg_vol_tag.end(offset=1)
            reg_trans.on_release_callback = _reg_callback

        return result


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

            slots = buffer_router.get_buffer_slots()
            for state in list(factory_router.region.available_states):
                if not state.T_available():
                    continue

                if not (
                    (factory_resp := factory_router.generic_transaction(
                        state
                    )).status): continue
                factory_transaction = factory_resp.transaction
                local_col = buffer_router.region.tl((factory_resp.upstream_patch.y - buffer_router.region.offset[0],
                                                    factory_resp.upstream_patch.x - buffer_router.region.offset[1]))[1]

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
                    resp = upstream_router.generic_transaction(upstream_patch, upstream_patch)
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
                        upstream_patch, free_slot # type: ignore
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


    def alloc_gsprep_gate(self, gate):
        # curr: tuple('curr_router', 'curr_downstream_idx', 'curr_request_col')
        # upstream_connect: dict[router -> (upstream_router, downstream_idx, upstream_col)]

        targs_pos = [self.mapper.position_xy(t)[::-1] for t in gate.targs]
        # (x, y) -> (row, col)

        targs_patches = [self.register_router.region[pos] for pos in targs_pos] # type: ignore

        bus_router = self.register_router.downstream[0]
        assert isinstance(bus_router, StandardBusRouter)

        resps : List[Response] = [self.register_router.generic_transaction(patch, target_orientation=bus_router.region.rotation) 
                                  for patch in targs_patches]

        if any(not r.status for r in resps):
            return None

        # resp2.transaction.move_patches = resp2.transaction.move_patches[::-1] # type: ignore
        
        bus_source = min((r.downstream_patch for r in resps), key=lambda x: x.x)
        bus_dest = max((r.downstream_patch for r in resps), key=lambda x: x.x)

        bus_resp: Response = bus_router.generic_transaction(bus_source, bus_dest)

        if not bus_resp.status:
            return None

        new_move_patches = []
        seen_patches = set()
        new_measure_patches = []
        for r in resps:
            new_measure_patches += r.transaction.measure_patches  # type: ignore
            for p in r.transaction.move_patches: # type: ignore
                if p in seen_patches: continue
                seen_patches.add(p)
                new_move_patches.append(p)

        # Hack in a display override
        new_move_patches.extend(bus_resp.transaction.move_patches)
        new_measure_patches.extend(bus_resp.transaction.measure_patches)

        pseudo_transaction = Transaction(new_move_patches, new_measure_patches)

        for r in resps:
            for p in r.transaction.move_patches[::-1]:
                pseudo_transaction.layout_override.append((p.y, p.x))

            # Calculate layout for bus transaction
            if r.downstream_patch.y == self.register_router.region.offset[0]:
                # routing up
                pseudo_transaction.layout_override.append((r.downstream_patch.y - 1, r.downstream_patch.x))
            elif r.downstream_patch.y == self.register_router.region.offset[0] + self.register_router.region.height - 1:
                # routing down
                pseudo_transaction.layout_override.append((r.downstream_patch.y + 1, r.downstream_patch.x))
            pseudo_transaction.layout_override.append((None, None))

        for p in bus_resp.transaction.move_patches:
            pseudo_transaction.layout_override.append((p.y, p.x))


        transactions = TransactionList([pseudo_transaction])

        # self.validate(transactions)
        # print("Prep at", self.vol_tracker.timer_source.time, gate)
        for reg_patch in targs_patches:
            if reg_patch.reg_vol_tag is None:
                assert self.vol_tracker
                reg_patch.reg_vol_tag = self.vol_tracker.make_tag(SpaceTimeVolumeType.REGISTER_VOLUME)
                reg_patch.reg_vol_tag.start()
        gate.activate(transactions)
        return gate
