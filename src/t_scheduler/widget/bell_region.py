
from .widget_region import WidgetRegion
from ..base import Patch, PatchType


class BellRegion(WidgetRegion):
    def __init__(
        self, height
    ) -> None:

        sc_patches = [
            [Patch(PatchType.BELL, r, 0)] for r in range(height)
        ]

        super().__init__(1, height, sc_patches)
        self.stats['num_bell_buffers'] = height
