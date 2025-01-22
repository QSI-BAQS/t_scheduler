from __future__ import annotations
from abc import ABC
from typing import List

from ..base.response import Response, ResponseStatus
from ..region import WidgetRegion, AbstractFactoryRegion
from ..tracker import *

region_router_exports = {}
router_constructors = {}


def export_router(region_constructor, is_default=True, region_name = None):
    '''
    Exports router to region_router_exports and router_constructors

    Set either region_constructor for auto-detection or region_name to override

    region_name takes priority

    Last invocation with is_default=True takes priority
    '''
    if region_name is None:
        region_name = region_constructor.__qualname__

    if region_name not in region_router_exports:
        region_router_exports[region_name] = {'options': [], 'default': None}

    def _init(router_constructor):
        router_name = router_constructor.__qualname__

        router_constructors[router_name] = router_constructor 
        region_router_exports[region_name]['options'].append(router_name)
        if is_default:
            region_router_exports[region_name]['default'] = router_name


        return router_constructor
    return _init


class AbstractRouter(ABC):
    upstream: AbstractRouter | None = None
    downstream: List[AbstractRouter] = tuple() # type: ignore
    region: WidgetRegion
    upkeep_accept = False
    magic_source = False
    vol_tracker: SpaceTimeVolumeTracker

    def _request_transaction(self, *args, **kwargs):
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
    
    def generic_transaction(self, source_patch, *args, target_orientation=None, **kwargs):
        trans = self._request_transaction(source_patch.x - self.region.offset[1], *args, **kwargs)
        if trans:
            return Response(ResponseStatus.CHECK_DOWNSTREAM, trans)
        else:
            return Response()

class AbstractFactoryRouter(AbstractRouter):
    region: AbstractFactoryRegion