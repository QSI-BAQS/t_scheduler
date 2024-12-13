from typing import List, Literal, Tuple

from .widget_region import WidgetRegion
from ..patch import Patch, PatchOrientation, PatchType
# from ..router import Router


class AbstractMagicStateBufferRegion(WidgetRegion):
    def __init__(self, width, height) -> None:
        super().__init__(width, height)

    def request_magic_state(self, pos):
        raise NotImplementedError()


class PrefilledMagicStateRegion(AbstractMagicStateBufferRegion):
    # router: Router
    cells: List[List[Patch]]

    def __init__(self, width, height, rotation: Literal['default', 'chessboard']) -> None:
        super().__init__(width, height)
        # self.router = router

        if rotation == 'default':
            self.cells = [
                [
                    Patch(PatchType.T, r, c) 
                    for c in range(self.width)
                ]
                for r in range(self.height)
            ]
        elif rotation == 'chessboard':
            self.cells = [[Patch(PatchType.T, 0, c) for c in range(self.width)]]
            self.cells.extend([
                [
                    Patch(PatchType.T, r, c, 
                          starting_orientation=PatchOrientation(((r ^ c) & 1) ^ (c < width // 2))
                    )
                    for c in range(self.width) 
                ]
                for r in range(1, self.height)
            ])

    def request_magic_state(self, pos):
        pass

    def __getitem__(self, key: Tuple[int, int] | int) -> Patch:
        if isinstance(key, tuple):
            return self.cells[key[0]][key[1]]
        else:
            return self.cells[key]  # type: ignore

class TCultivatorBufferRegion(AbstractMagicStateBufferRegion):
    def __init__(self, width, height) -> None:
        super().__init__(width, height)
    
    def request_magic_state(self, pos):
        pass


class MagicStateBufferRegion(AbstractMagicStateBufferRegion):
    def __init__(self, width, height) -> None:
        super().__init__(width, height)
    
    def request_magic_state(self, pos):
        pass