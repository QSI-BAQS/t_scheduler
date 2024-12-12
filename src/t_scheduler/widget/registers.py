from typing import List, Tuple

from ..patch import Patch, PatchType
from .widget_region import WidgetRegion


class RegisterRegion(WidgetRegion):
    patch_grid: List[List[Patch]]

    def __init__(self, width, height, patch_grid) -> None:
        self.patch_grid = patch_grid
        super().__init__(width, height)

    def get_physical_pos(self, op_targ):
        raise NotImplementedError()

    def __getitem__(self, key: Tuple[int, int] | int) -> Patch:
        if isinstance(key, tuple):
            return self.patch_grid[key[0]][key[1]]
        else:
            return self.patch_grid[key]  # type: ignore


class SingleRowRegisterRegion(RegisterRegion):
    def __init__(self, width) -> None:
        patches = [[Patch(PatchType.REG, 0, c) for c in range(width)]]
        super().__init__(width, 1, patches)

    def get_physical_pos(self, op_targ):
        pos = op_targ * 2
        if pos < 0 or pos >= self.width:
            raise ValueError(f"Requested op targ out of bounds: Targ {op_targ} ({pos}) not in [0, {self.width})!")
        return pos



class CombShapedRegisterRegion(RegisterRegion):
    def __init__(self, width) -> None:
        raise NotImplementedError()

    def get_physical_pos(self, op_targ):
        raise NotImplementedError()
