

from typing import List
from t_scheduler.patch import Patch, PatchLock
from t_scheduler.router.transaction import Transaction
from t_scheduler.widget.route_bus import RouteBus

class StandardBusRouter:
    route_bus: RouteBus

    def __init__(self, route_bus) -> None:
        self.route_bus = route_bus

    def request_transaction(self, start_col, end_col):
        if not (0 <= start_col < self.route_bus.width) or not (0 <= end_col < self.route_bus.width):
            return None
        bound_min = min(start_col, end_col)
        bound_max = max(start_col, end_col) + 1
        path = [self.route_bus[0, c] for c in range(bound_min, bound_max)]
        if any(p.locked() for p in path):
            return None

        return Transaction(path, [])
