from __future__ import annotations
from abc import ABC
from typing import List

from t_scheduler.base.response import Response, ResponseStatus
from ..widget import WidgetRegion

class AbstractRouter(ABC):
    upstream: AbstractRouter | None = None
    downstream: List[AbstractRouter] = tuple() # type: ignore
    region: WidgetRegion
    upkeep_accept = False
    magic_source = False

    def request_transaction(self, *args, **kwargs):
        '''
        Request a transaction from the router with specified args.

        Overridden by implementers.
        '''
        raise NotImplementedError()

    @staticmethod
    def range_directed(a, b):
        if a <= b:
            return range(a, b + 1)
        else:
            return range(a, b - 1, -1)

    def to_downstream_col(self, downstream_idx, local_col):
        offset = 0
        for i in range(downstream_idx):
            offset += self.downstream[i].region.width
        return self.clamp(local_col - offset, 0, self.downstream[downstream_idx].region.width - 1)
    
    def to_local_col(self, downstream_idx, downstream_col):
        offset = 0
        for i in range(downstream_idx):
            offset += self.downstream[i].region.width
        return offset + downstream_col
    
    @staticmethod
    def clamp(val, range_low, range_high):
        return max(range_low, min(val, range_high))    
    
    def generic_transaction(self, *args, **kwargs):
        trans = self.request_transaction(*args, **kwargs)
        if trans:
            return Response(ResponseStatus.CHECK_DOWNSTREAM, trans)
        else:
            return Response()
