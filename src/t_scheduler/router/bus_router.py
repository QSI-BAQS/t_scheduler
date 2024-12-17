

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
        path = [self.route_bus[0, c] for c in self.range_directed(start_col, end_col)]
        if any(p.locked() for p in path):
            return None

        return Transaction(path, [])
    
    @staticmethod
    def range_directed(a, b):
        if a <= b:
            return range(a, b + 1)
        else:
            return range(a, b - 1, -1)
