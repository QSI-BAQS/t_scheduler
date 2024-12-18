from typing import Callable, Tuple

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

def flat_naive_strategy_with_t_cultivator_widget(width, height) -> Tuple[FlatNaiveStrategy, Widget]:
    register_region = SingleRowRegisterRegion(width)
    route_region = RouteBus(width)
    buffer_region = TCultivatorBufferRegion(width - 2, height - 2, "dense")

    board = _concat_vertical(register_region.sc_patches, route_region.sc_patches,
                             _squash_and_add_bell_regions(buffer_region))

    widget = Widget(
        width,
        height,
        board,
        components=[register_region, route_region, buffer_region],
    )  # Pseudo-widget for output clarity

    strat = FlatNaiveStrategy(
        BaselineRegisterRouter(register_region),
        StandardBusRouter(route_region),
        DenseTCultivatorBufferRouter(buffer_region),
    )
    return strat, widget

def flat_naive_strategy_with_litinski_5x3_unbuffered_widget(
    width, height
) -> Tuple[FlatNaiveStrategy, Widget]:
    register_region = SingleRowRegisterRegion(width)
    route_region = RouteBus(width)
    buffer_region = MagicStateFactoryRegion.with_litinski_5x3(
        width - 2, height - 2)

    board = _concat_vertical(register_region.sc_patches, route_region.sc_patches,
                             _squash_and_add_bell_regions(buffer_region))
    widget = Widget(
        width,
        height,
        board,
        components=[register_region, route_region, buffer_region],
    )  # Pseudo-widget for output clarity

    strat = FlatNaiveStrategy(
        BaselineRegisterRouter(register_region),
        StandardBusRouter(route_region),
        MagicStateFactoryRouter(buffer_region),
    )
    return strat, widget

def flat_naive_strategy_with_litinski_6x3_dense_unbuffered_widget(
    width, height
) -> Tuple[FlatNaiveStrategy, Widget]:
    register_region = SingleRowRegisterRegion(width)
    route_region = RouteBus(width)
    buffer_region = MagicStateFactoryRegion.with_litinski_6x3_dense(
        width - 2, height - 2
    )

    board = _concat_vertical(register_region.sc_patches, route_region.sc_patches,
                             _squash_and_add_bell_regions(buffer_region))
    widget = Widget(
        width,
        height,
        board,
        components=[register_region, route_region, buffer_region],
    )  # Pseudo-widget for output clarity

    strat = FlatNaiveStrategy(
        BaselineRegisterRouter(register_region),
        StandardBusRouter(route_region),
        MagicStateFactoryRouter(buffer_region),
    )
    return strat, widget

def buffered_naive_strategy_with_buffered_widget(
    width,
    height,
    buffer_height,
    factory_factory: Callable[[int, int], MagicStateFactoryRegion],
) -> Tuple[BufferedNaiveStrategy, Widget]:
    register_region = SingleRowRegisterRegion(width)
    route_region = RouteBus(width)
    buffer_region = MagicStateBufferRegion(width - 2, buffer_height)
    buffer_bus_region = RouteBus(width - 2)
    factory_region = factory_factory(width - 2, height - 3 - buffer_height)

    board = _concat_vertical(register_region.sc_patches, route_region.sc_patches,
                             _squash_and_add_bell_regions(buffer_region, buffer_bus_region, factory_region))

    widget = Widget(
        width,
        height,
        board,
        components=[
            register_region,
            route_region,
            buffer_region,
            buffer_bus_region,
            factory_region,
        ],
    )  # Pseudo-widget for output clarity

    strat = BufferedNaiveStrategy(
        BaselineRegisterRouter(register_region),
        StandardBusRouter(route_region),
        RechargableBufferRouter(buffer_region),
        StandardBusRouter(buffer_bus_region),
        MagicStateFactoryRouter(factory_region),
    )
    return strat, widget


def vertical_strategy_with_prefilled_buffer_widget(
    width, height, rot_strat
) -> Tuple[VerticalRoutingStrategy, Widget]:
    register_region = SingleRowRegisterRegion(width)
    route_region = RouteBus(width)
    buffer_region = PrefilledMagicStateRegion(width - 2, height - 2, "default")

    board = _concat_vertical(register_region.sc_patches, route_region.sc_patches,
                            _squash_and_add_bell_regions(buffer_region))
    widget = Widget(
        width,
        height,
        board,
        components=[register_region, route_region, buffer_region],
    )

    strat = VerticalRoutingStrategy(
        BaselineRegisterRouter(register_region),
        StandardBusRouter(route_region),
        VerticalFilledBufferRouter(buffer_region),
        rot_strat=rot_strat,
    )
    return strat, widget

def vertical_strategy_with_prefilled_comb_widget(
    width, height, rot_strat, comb_height
) -> Tuple[VerticalRoutingStrategy, Widget]:
    register_region = CombShapedRegisterRegion(width, comb_height)
    route_region = RouteBus(width)
    buffer_region = PrefilledMagicStateRegion(
        width - 2, height - 1 - comb_height, "default"
    )

    board = _concat_vertical(register_region.sc_patches, route_region.sc_patches,
                            _squash_and_add_bell_regions(buffer_region))
    widget = Widget(
        width,
        height,
        board,
        components=[register_region, route_region, buffer_region],
    )

    strat = VerticalRoutingStrategy(
        CombRegisterRouter(register_region),
        StandardBusRouter(route_region),
        VerticalFilledBufferRouter(buffer_region),
        rot_strat=rot_strat,
    )
    return strat, widget


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
