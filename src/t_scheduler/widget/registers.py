from typing import List, Literal, Tuple

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
        return (0, pos)



class CombShapedRegisterRegion(RegisterRegion):
    def __init__(self, width, height, route_width: Literal[1, 2] = 2) -> None:
        """
        .RR..RR..RR
        R  RR  RR  
        R  RR  RR  
        R  RR  RR  
        R  RR  RR  
         ^^
         route_width
        """
        targ_map = {}
        targ_count = 0

        patches = []
        top_row = [Patch(PatchType.RESERVED, 0, 0)]
        for c in range(1, width):
            if (c - 1) % (2 + route_width) < route_width:
                new_reg = Patch(PatchType.REG, 0, c)
                top_row.append(new_reg)
                targ_map[targ_count] = new_reg
                targ_count += 1
            else:
                top_row.append(Patch(PatchType.RESERVED, 0, c))
        patches.append(top_row)
        for r in range(1, height):
            row = []
            for c in range(width):
                if (c - 1) % (2 + route_width) < route_width or ((c - 1) % (2 + route_width) == route_width + 1 and c == width - 1):
                    row.append(Patch(PatchType.ROUTE, r, c))
                else:
                    new_reg = Patch(PatchType.REG, r, c)
                    row.append(new_reg)
                    targ_map[targ_count] = new_reg
                    targ_count += 1
            patches.append(row)
        super().__init__(width, height, patches)

        self.targ_map = targ_map


    def get_physical_pos(self, op_targ):
        reg = self.targ_map[op_targ]
        return (reg.row, reg.col)
