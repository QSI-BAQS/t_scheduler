from typing import List, Tuple
from t_scheduler.patch import Patch, PatchType
from .widget_region import WidgetRegion

class RouteBus(WidgetRegion):
    sc_patches: List[List[Patch]]

    def __init__(self, width) -> None:
        sc_patches = [[Patch(PatchType.ROUTE, 0, c) for c in range(width)]]
        super().__init__(width, 1, sc_patches)

    def route_priority(self, source):
        yield source
        for offset in range(1, self.width):
            if 0 <= source + offset < self.width:
                yield source + offset
            if 0 <= source - offset < self.width:
                yield source - offset
