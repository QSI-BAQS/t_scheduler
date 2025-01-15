import itertools
from typing import List, Literal, Set, Tuple

from .region_types import region_init, BUFFER_REGION 
from .widget_region import WidgetRegion
from ..base import Patch, PatchOrientation, PatchType
from ..base.patch import BufferPatch, TCultPatch

class AbstractMagicStateBufferRegion(WidgetRegion):
    def __init__(self, width, height, sc_patches) -> None:
        super().__init__(width, height, sc_patches)

@region_init(BUFFER_REGION)
class PrefilledMagicStateRegion(AbstractMagicStateBufferRegion):
    def __init__(
        self, width, height, rotation: Literal["default", "chessboard"]
    ) -> None:
        if rotation == "default":
            sc_patches = [
                [Patch(PatchType.T, r, c) for c in range(width)] for r in range(height)
            ]
        elif rotation == "chessboard":
            sc_patches = [[Patch(PatchType.T, 0, c) for c in range(width)]]
            sc_patches.extend(
                [
                    [
                        Patch(
                            PatchType.T,
                            r,
                            c,
                            starting_orientation=PatchOrientation(
                                ((r ^ c) & 1) ^ (c < width // 2)
                            ),
                        )
                        for c in range(width)
                    ]
                    for r in range(1, height)
                ]
            )
        super().__init__(width, height, sc_patches)

@region_init(BUFFER_REGION)
class MagicStateBufferRegion(AbstractMagicStateBufferRegion):

    def __init__(self, width, height) -> None:

        self.available_states = set()
        sc_patches = []
        for r in range(height):
            row = [BufferPatch(r, c) for c in range(width)]
            sc_patches.append(row)

        super().__init__(width, height, sc_patches)
        self.stats['num_t_buffers'] = width * height

    def get_buffer_slots(self) -> List[None | Patch]:
        buffer_lanes = []
        for col in range(self.width):
            topmost = None
            for row in range(self.height - 1, -1, -1):
                if (cell := self.sc_patches[row][col]).route_available():
                    topmost = cell
                else:
                    break
            buffer_lanes.append(topmost)
        return buffer_lanes

    def get_buffer_states(self) -> List[None | Patch]:
        buffer_lanes = []
        for col in range(self.width):
            topmost = None
            for row in range(self.height):
                if (cell := self.sc_patches[row][col]).T_available():
                    topmost = cell
                    break
                elif not cell.route_available():
                    break
            buffer_lanes.append(topmost)
        return buffer_lanes
