from ..base import Transaction
from ..widget import RouteBus
from .abstract_router import AbstractRouter

class StandardBusRouter(AbstractRouter):
    route_bus: RouteBus

    def __init__(self, route_bus) -> None:
        self.route_bus = route_bus

    def request_transaction(self, start_col: int, end_col: int):
        '''
        Request the route bus between start_col and end_col
        (both inclusive)
        '''
        if not (0 <= start_col < self.route_bus.width) or not (
            0 <= end_col < self.route_bus.width
        ):
            return None

        path = [self.route_bus[0, c] for c in self.range_directed(start_col, end_col)]

        if any(p.locked() for p in path):
            return None

        return Transaction(path, [])