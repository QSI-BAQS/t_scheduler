from typing import Any, List

from ..base.gate import GateType
from ..base import Gate, TransactionList
from ..router import BaselineRegisterRouter, StandardBusRouter



class BaseStrategy:
    register_router: BaselineRegisterRouter
    needs_upkeep: bool = False

    def __init__(self, register_router) -> None:
        self.register_router = register_router

    def alloc_nonlocal(self, gate: Gate) -> Gate | None:
        '''
        Alloc a non-local gate
        '''
        raise NotImplementedError("Override this method in a subclass!")
    
    def alloc_gsprep_gate(self, gate):
        raise NotImplementedError()

    def alloc_gate(self, gate: Gate) -> Gate | None:
        '''
        Alloc a gate.
        
        Logic for local and ancilla gates is handled internally.

        If nonlocal, then we dispatch to alloc_nonlocal.
        '''

        if gate.gate_type == GateType.T_STATE:
            return self.alloc_nonlocal(gate)
        elif gate.gate_type == GateType.GRAPH_STATE_PREP:
            return self.alloc_gsprep_gate(gate)
        
        target_pos: Tuple[int, int] = self.mapper.position_xy(gate.targ)[::-1] # type: ignore 
        # (x, y) -> (row, col)

        if gate.gate_type == GateType.LOCAL_GATE:
            if not (
                register_transaction := self.register_router.request_explicit(
                    target_pos, request_type="local"
                )
            ):
                return None

            gate.activate(register_transaction)
            return gate

        elif gate.gate_type == GateType.ANCILLA:
            # See if ancilla can be allocated within the register region
            if (
                register_transaction := self.register_router.request_explicit(
                    target_pos, request_type="ancilla"
                )
            ):
                gate.activate(register_transaction)
                return gate

            return None

            # TODO: Reimplement fallback
            # # Fallback: allocate an ancilla within the route region

            # register_transaction = self.register_router.request_transaction(
            #     gate.targ, request_type="nonlocal")
            # if not register_transaction:
            #     return None

            # reg_col = register_transaction.connect_col

            # route_transaction = self.bus_router.request_transaction(
            #     reg_col, reg_col)  # type: ignore
            # if not route_transaction:
            #     return None
            
            # transaction = TransactionList(route_transaction, register_transaction)
            # gate.activate(transaction)
            # return gate


    def upkeep(self) -> List[Gate]:
        raise NotImplementedError()
    
    @staticmethod
    def clamp(val, low, high):
        return max(low, min(val, high))
