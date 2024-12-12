from t_scheduler.router.transaction import Transaction
from t_scheduler.widget.registers import SingleRowRegisterRegion


class BaselineRegisterRouter:
    region: SingleRowRegisterRegion

    def __init__(self, region) -> None:
        self.region = region

    def request_transaction(self, gate_targ) -> Transaction | None:
        physical_position = self.region.get_physical_pos(gate_targ)
        
        reg_patch = self.region[0, physical_position]

        if reg_patch.locked():
            return None
        
        return Transaction([reg_patch], [reg_patch], physical_position)
