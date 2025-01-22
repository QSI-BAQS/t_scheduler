from __future__ import annotations
from typing import List, Literal, Set, Tuple

from .region_types import export_region, BUFFER_REGION 
from .widget_region import WidgetRegion
from ..base import Patch, PatchOrientation, PatchType
from ..base.patch import BufferPatch, TCultPatch

class AbstractMagicStateBufferRegion(WidgetRegion):
    def __init__(self, width, height, sc_patches, **kwargs) -> None:
        super().__init__(width, height, sc_patches, **kwargs)

class PrefilledMagicStateRegion(AbstractMagicStateBufferRegion):
    def __init__(
        self, width, height, rotation: Literal["default", "chessboard"], **kwargs
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
        super().__init__(width, height, sc_patches, **kwargs)

    @export_region(BUFFER_REGION)
    @staticmethod
    def with_default_rotation(*args, rotation = "default", **kwargs) -> PrefilledMagicStateRegion:
        assert rotation == "default"
        return PrefilledMagicStateRegion(*args, rotation = "default", **kwargs)
    
    @export_region(BUFFER_REGION)
    @staticmethod
    def with_chessboard_rotation(*args, rotation = "chessboard", **kwargs) -> PrefilledMagicStateRegion:
        assert rotation == "chessboard"
        return PrefilledMagicStateRegion(*args, rotation = "chessboard", **kwargs)

@export_region(BUFFER_REGION)
class MagicStateBufferRegion(AbstractMagicStateBufferRegion):

    def __init__(self, width, height, **kwargs) -> None:

        self.available_states = set()
        sc_patches = []
        for r in range(height):
            row = [BufferPatch(r, c) for c in range(width)]
            sc_patches.append(row)

        super().__init__(width, height, sc_patches, **kwargs)
        self.stats['num_t_buffers'] = width * height
