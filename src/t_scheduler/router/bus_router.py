from ..base import Transaction, Response, ResponseStatus
from ..widget import RouteBus
from .abstract_router import AbstractRouter

class StandardBusRouter(AbstractRouter):
    region: RouteBus

    def __init__(self, route_bus) -> None:
        self.region = route_bus

    def request_transaction(self, start_col: int, end_col: int):
        '''
        Request the route bus between start_col and end_col
        (both inclusive)
        '''
        if not (0 <= start_col < self.region.width) or not (
            0 <= end_col < self.region.width
        ):
            return None

        path = [self.region[0, c] for c in self.range_directed(start_col, end_col)]

        if any(p.locked() for p in path):
            return None

        return Transaction(path, [])
    
    def generic_transaction(self, start_col, end_col = None):
        if end_col is None:
            end_col = start_col
        trans = self.request_transaction(start_col, end_col)
        if trans:
            return Response(ResponseStatus.CHECK_DOWNSTREAM, trans)
        else:
            return Response()