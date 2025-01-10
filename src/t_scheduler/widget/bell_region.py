from .widget_region import WidgetRegion
from .region_types import region_init, BELL_REGION 

from ..base import Patch, PatchType

@region_init(BELL_REGION)
class BellRegion(WidgetRegion):
    def __init__(
        self, height, *, width=1
    ) -> None:

        sc_patches = [
            [Patch(PatchType.BELL, r, 0)] for r in range(height)
        ]

        super().__init__(1, height, sc_patches)
        self.stats['num_bell_buffers'] = height
