from typing import Callable, Literal, Tuple

from ..base import *
from ..router import *
from ..strategy import *
from ..widget import *

def _squash_and_add_bell_regions(*regions):
    output = []
    for region in regions:
        for row in region.sc_patches:
            output.append([
                Patch(PatchType.BELL, 0, 0),
                *row,
                Patch(PatchType.BELL, 0, -1),
            ])
    return output

def _concat_vertical(*rowlists):
    return sum(rowlists, start=[])



@staticmethod
def tree_strategy_with_prefilled_buffer_widget(
    width, height
) -> Tuple[TreeRoutingStrategy, Widget]:
    if width % 4 != 0:
        raise ValueError("Only multiples of 4 supported for width")

    register_region = SingleRowRegisterRegion(width)
    route_region = RouteBus(width)
    buffer_region = PrefilledMagicStateRegion(
        width - 2, height - 2, "chessboard")

    board = _concat_vertical(register_region.sc_patches, route_region.sc_patches,
                            _squash_and_add_bell_regions(buffer_region))

    widget = Widget(
        width,
        height,
        board,
        components=[register_region, route_region, buffer_region],
    )  # Pseudo-widget for output clarity

    strat = TreeRoutingStrategy(
        BaselineRegisterRouter(register_region),
        StandardBusRouter(route_region),
        TreeFilledBufferRouter(buffer_region),
    )
    return strat, widget
