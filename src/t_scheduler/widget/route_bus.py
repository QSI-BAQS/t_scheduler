from typing import List, Tuple
from t_scheduler.patch import Patch, PatchType
from .widget_region import WidgetRegion


class RouteBus(WidgetRegion):
    patch_grid: List[List[Patch]]
    def __init__(self, width) -> None:
        super().__init__(width, 1)
        self.patch_grid = [[Patch(PatchType.ROUTE, 0, c) for c in range(width)]]

    def route_priority(self, source):
        yield source
        for offset in range(1, self.width):
            if 0 <= source + offset < self.width:
                yield source + offset
            if 0 <= source - offset < self.width:
                yield source - offset
    
    def __getitem__(self, key: Tuple[int, int] | int) -> Patch:
        if isinstance(key, tuple):
            return self.patch_grid[key[0]][key[1]]
        else:
            return self.patch_grid[key]  # type: ignore