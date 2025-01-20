from ..base import Transaction, Response, ResponseStatus
from ..widget import RouteBus
from .abstract_router import AbstractRouter, export_router

@export_router(RouteBus)
class StandardBusRouter(AbstractRouter):
    region: RouteBus

    def __init__(self, route_bus) -> None:
        self.region = route_bus

    def _request_transaction(self, start_col: int, end_col: int):
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
    
    def generic_transaction(self, source_patch, end_patch = None, target_orientation=None, ):
        start_col = source_patch.x - self.region.offset[1]
        if end_patch is None:
            end_col = start_col
        else:
            end_col = end_patch.x - self.region.offset[1]
        trans = self._request_transaction(start_col, end_col)
        if trans:
            return Response(ResponseStatus.CHECK_DOWNSTREAM, trans)
        else:
            return Response()