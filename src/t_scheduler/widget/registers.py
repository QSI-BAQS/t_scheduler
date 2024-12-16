from typing import List, Tuple

from ..patch import Patch, PatchType
from .widget_region import WidgetRegion


class RegisterRegion(WidgetRegion):

    def __init__(self, width, height, sc_patches) -> None:
        super().__init__(width, height, sc_patches)

    def get_physical_pos(self, op_targ):
        '''
            Gets the physical position of a targ for a gate
        '''
        raise NotImplementedError()

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
