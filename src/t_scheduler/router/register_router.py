from typing import Literal
from t_scheduler.router.transaction import Transaction
from t_scheduler.widget.registers import SingleRowRegisterRegion


class BaselineRegisterRouter:
    region: SingleRowRegisterRegion

    def __init__(self, region) -> None:
        self.region = region

    def request_transaction(self, gate_targ, request_type: Literal['local', 'nonlocal', 'ancilla'] = 'nonlocal') -> Transaction | None:
        # TODO add logic if 1x1 register cell and ancilla required
        
        physical_position = self.region.get_physical_pos(gate_targ)
        
        reg_patch = self.region[0, physical_position]

        if reg_patch.locked():
            return None



        # Below relies on 1x2 reg patches
        if request_type == 'ancilla':
            anc = self.region[0, physical_position + 1]
            if anc.locked(): # This should never happen
                return None
            lock = [anc, reg_patch]
            return Transaction(lock, [])
        else:
            return Transaction([reg_patch], [reg_patch], physical_position)
