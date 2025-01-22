from .widget_region import WidgetRegion
from .region_types import export_region, BELL_REGION 

from ..base import Patch, PatchType

@export_region(BELL_REGION)
class BellRegion(WidgetRegion):
    def __init__(
        self, height, *, width=1, **kwargs
    ) -> None:

        sc_patches = [
            [Patch(PatchType.BELL, r, c) for c in range(width)] for r in range(height)
        ]

        super().__init__(width, height, sc_patches, **kwargs)
        self.stats['num_bell_buffers'] = height * width
