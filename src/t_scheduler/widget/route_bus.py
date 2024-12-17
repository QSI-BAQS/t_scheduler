from typing import List, Tuple
from ..patch import Patch, PatchType
from .widget_region import WidgetRegion

class RouteBus(WidgetRegion):
    '''
        Single row routing bus
    '''
    sc_patches: List[List[Patch]]

    def __init__(self, width: int) -> None:
        '''
            Creates a 1 x width routing bus
        '''
        sc_patches = [[Patch(PatchType.ROUTE, 0, c) for c in range(width)]]
        super().__init__(width, 1, sc_patches)

    def route_priority(self, source: int):
        '''
            Generator for columns closest to a source column
        '''
        yield source
        for offset in range(1, self.width):
            if 0 <= source + offset < self.width:
                yield source + offset
            if 0 <= source - offset < self.width:
                yield source - offset
