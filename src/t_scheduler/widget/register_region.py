from typing import List, Literal, Tuple

from .region_types import region_init, REGISTER_REGION 
from ..base.patch import Patch, PatchOrientation, PatchType
from .widget_region import WidgetRegion

class RegisterRegion(WidgetRegion):
    """
    Abstract register region
    """

    def __init__(self, width: int, height: int, sc_patches: List[List[Patch]], **kwargs) -> None:
        if height in kwargs:
            assert height == kwargs.pop(height)
        super().__init__(width, height, sc_patches, **kwargs)

    def get_physical_pos(self, op_targ: int) -> Tuple[int, int]:
        """
        Gets the physical position of a targ for a gate
        """
        raise NotImplementedError()

@region_init(REGISTER_REGION)
class SingleRowRegisterRegion(RegisterRegion):
    """
    Single row register region
    """

    def __init__(self, width: int, **kwargs) -> None:
        patches = [[Patch(PatchType.REG, 0, c) for c in range(width)]]
        super().__init__(width, 1, patches, **kwargs)
        self.stats['num_registers'] = width // 2

    def get_physical_pos(self, op_targ: int) -> Tuple[int, int]:
        pos = op_targ * 2
        if pos < 0 or pos >= self.width:
            raise ValueError(
                f"Requested op targ out of bounds: Targ {op_targ} ({pos}) not in [0, {self.width})!"
            )
        return (0, pos)

@region_init(REGISTER_REGION)
class CombShapedRegisterRegion(RegisterRegion):
    """
    Comb shaped register region.

    .RR..RR..RR  (optional)
    R  RR  RR
    R  RR  RR
    R  RR  RR
    R  RR  RR
     ^^
     route_width
    """

    def __init__(self, width: int, height: int, route_width: Literal[1, 2] = 2, incl_top = True, **kwargs) -> None:

        targ_map = {}
        targ_count = 0

        patches = []
        if incl_top:
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
        for r in range(incl_top, height):
            row = []
            for c in range(width):
                if (c - 1) % (2 + route_width) < route_width or (
                    (c - 1) % (2 + route_width) == route_width +
                    1 and c == width - 1
                ):
                    row.append(Patch(PatchType.ROUTE, r, c))
                else:
                    new_reg = Patch(PatchType.REG, r, c,
                                    starting_orientation=PatchOrientation.X_TOP)
                    row.append(new_reg)
                    targ_map[targ_count] = new_reg
                    targ_count += 1
            patches.append(row)
        super().__init__(width, height, patches, **kwargs)
        self.stats['num_registers'] = len(targ_map)
        self.targ_map = targ_map

    def get_physical_pos(self, op_targ: int) -> Tuple[int, int]:
        reg = self.targ_map[op_targ]
        return (reg.row, reg.col)
