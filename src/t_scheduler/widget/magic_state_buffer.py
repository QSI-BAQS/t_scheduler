import itertools
from typing import List, Literal, Set, Tuple

from .widget_region import WidgetRegion
from ..patch import Patch, PatchOrientation, PatchType, TCultPatch
# from ..router import Router


class AbstractMagicStateBufferRegion(WidgetRegion):
    def __init__(self, width, height, sc_patches) -> None:
        super().__init__(width, height, sc_patches)

class PrefilledMagicStateRegion(AbstractMagicStateBufferRegion):
    def __init__(self, width, height, rotation: Literal['default', 'chessboard']) -> None:
        if rotation == 'default':
            sc_patches = [
                [
                    Patch(PatchType.T, r, c)
                    for c in range(width)
                ]
                for r in range(height)
            ]
        elif rotation == 'chessboard':
            sc_patches = [[Patch(PatchType.T, 0, c) for c in range(width)]]
            sc_patches.extend([
                [
                    Patch(PatchType.T, r, c,
                          starting_orientation=PatchOrientation(
                              ((r ^ c) & 1) ^ (c < width // 2))
                          )
                    for c in range(width)
                ]
                for r in range(1, height)
            ])
        super().__init__(width, height, sc_patches)


class TCultivatorBufferRegion(AbstractMagicStateBufferRegion):
    available_states: Set[TCultPatch]
    update_cells: List[TCultPatch]

    def __init__(self, width, height, buffer_type: Literal['dense', 'sparse']) -> None:
        self.available_states = set()

        if buffer_type == 'dense':
            sc_patches = [
                [
                    TCultPatch(r, c)
                    for c in range(width)
                ]
                for r in range(height)
            ]
            self.update_cells = list(
                itertools.chain(*sc_patches))  # type: ignore
        elif buffer_type == 'sparse':
            sc_patches = []
            self.update_cells = []
            for r in range(height):
                if (height - r) % 3 == 2:
                    row = [Patch(PatchType.ROUTE, r, c) for c in range(width)]
                else:
                    row = [TCultPatch(r, c) for c in range(width)]
                    self.update_cells.extend(row)
                sc_patches.append(row)

        super().__init__(width, height, sc_patches)  # type: ignore

    def update(self):
        for cell in self.update_cells:
            if cell.update():
                self.available_states.add(cell)

    def release_cells(self, sc_patches: List[TCultPatch]):
        for cell in sc_patches:
            # TODO time etc.
            cell.release(None)

    def __getitem__(self, key: Tuple[int, int] | int) -> Patch:
        if isinstance(key, tuple):
            return self.sc_patches[key[0]][key[1]]
        else:
            return self.sc_patches[key]  # type: ignore


class MagicStateBufferRegion(AbstractMagicStateBufferRegion):

    def __init__(self, width, height) -> None:

        self.available_states = set()
        sc_patches = []
        for r in range(height):
            row = [Patch(PatchType.ROUTE_BUFFER, r, c) for c in range(width)]
            sc_patches.append(row)

        super().__init__(width, height, sc_patches)

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
