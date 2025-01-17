from __future__ import annotations
from typing import Callable, List, Literal
from functools import partial

from ..schedule_orchestrator import ScheduleOrchestrator

from ..strategy.generic_strategy import GenericStrategy, RotationStrategyOption

from ..base import *
from ..router import *
from ..strategy import *
from ..widget import *

class LayoutNode:
    upstream: None | LayoutNode
    downstream: List[LayoutNode]
    router_factory: Callable[[WidgetRegion], AbstractRouter]
    region_factory: Callable[[], WidgetRegion]

    def __init__(self, region_factory, router_factory, downstream=tuple()):
        self.region_factory = region_factory
        self.router_factory = router_factory
        self.downstream = downstream
        for node in self.downstream:
            node.upstream = self

    def create(self, upstream_region=None, upstream_router=None):
        regions = [self.region_factory()]
        routers = [self.router_factory(regions[0])]

        regions[0].upstream = upstream_region
        routers[0].upstream = upstream_router
        if upstream_region:
            if not upstream_region.downstream:
                upstream_region.downstream = []
            upstream_region.downstream.append(regions[0])
        if upstream_router:
            if not upstream_router.downstream:
                upstream_router.downstream = []
            upstream_router.downstream.append(routers[0])

        for layout in self.downstream:
            downstream_regions, downstream_routers = layout.create(
                regions[0], routers[0])
            regions += downstream_regions
            routers += downstream_routers
        return regions, routers

def estimate_generated_t_count(layout_root, num_prewarm_cycles) -> int:
    regions, routers = layout_root.create()

    board = make_board(regions)
    
    widget = Widget(
        len(board[0]),
        len(board),
        board,
        components=regions,
    )  # Pseudo-widget for output clarity

    strat = GenericStrategy(
        routers,
        # TODO fix
        # rot_strat=rot_strat
    )
    
    # TODO early exit when buffer full

    # TODO remove debug
    orc = ScheduleOrchestrator([], widget, strat, json=True)
    orc.prewarm(num_prewarm_cycles)
    orc.save_json()

    total = 0

    for reg in regions:
        if isinstance(reg, MagicStateBufferRegion):
            for row in reg.sc_patches:
                for cell in row:
                    if cell.T_available(): total += 1
        elif isinstance(reg, MagicStateFactoryRegion):
            for factory in reg.factories:
                total += sum(output.t_count for output in set(factory.outputs))
    total += len(orc.active)
    return total



def make_board(regions):
    board = []

    active = [(regions[0], 0)]
    while active:
        curr_row = []
        next_active = []
        for region, row_idx in active:
            if row_idx < region.height:
                curr_row += region[row_idx]
                next_active.append((region, row_idx + 1))
            else:
                for downstream_region in region.downstream:
                    curr_row += downstream_region[0]
                    next_active.append((downstream_region, 1))
        board.append(curr_row)
        active = next_active
    return board

def make_explicit(layout, width, height):
    regions, routers = layout.create()

    board = [[Patch(PatchType.RESERVED, r, c) for c in range(width)] for r in range(height)]
    for region in regions:
        roff, coff = region.offset
        for r in range(region.height):
            # if board[roff + r][coff:coff + region.width].count(None) != region.width:
            #     raise ValueError('Error when applying region: overlap detected.', region)
            board[roff + r][coff:coff + region.width] = region[r]

    widget = Widget(
        width,
        height,
        board, # type: ignore
        components=regions,
    )  # Pseudo-widget for output clarity

    strat = GenericStrategy(
        routers,
    )
    return strat, widget

def make_widget(func):
    def wrapped(width, height, *args, rot_strat=RotationStrategyOption.ADD_DELAY, **kwargs):
        layout = func(width, height, *args, **kwargs)

        regions, routers = layout.create()

        board = make_board(regions)
        
        widget = Widget(
            width,
            height,
            board,
            components=regions,
        )  # Pseudo-widget for output clarity

        strat = GenericStrategy(
            routers,
            rot_strat=rot_strat
        )
        return strat, widget
    return wrapped

@make_widget
def flat_naive_litinski_5x3_unbuffered_widget(width, height, include_bell=True):
    if include_bell:
        layout = LayoutNode(
            partial(SingleRowRegisterRegion, width),
            BaselineRegisterRouter,
            [LayoutNode(
                partial(RouteBus, width),
                StandardBusRouter,
                [
                    LayoutNode(
                        partial(BellRegion, height - 2),
                        BellRouter
                    ),
                    LayoutNode(
                        partial(MagicStateFactoryRegion.with_litinski_5x3,
                                width - 2, height - 2),
                        MagicStateFactoryRouter,
                    ),
                    LayoutNode(
                        partial(BellRegion, height - 2),
                        BellRouter
                    )

                ]
            )]
        )
    else:
        layout = LayoutNode(
            partial(SingleRowRegisterRegion, width),
            BaselineRegisterRouter,
            [LayoutNode(
                partial(RouteBus, width),
                StandardBusRouter,
                [LayoutNode(
                    partial(MagicStateFactoryRegion.with_litinski_5x3,
                            width, height - 2),
                    MagicStateFactoryRouter,
                )]
            )]
        )
    return layout

@make_widget
def flat_naive_t_cultivator_widget(width, height):
    layout = LayoutNode(
        partial(SingleRowRegisterRegion, width),
        BaselineRegisterRouter,
        [LayoutNode(
            partial(RouteBus, width),
            StandardBusRouter,
            [
                LayoutNode(
                    partial(BellRegion, height - 2),
                    BellRouter
                ),
                LayoutNode(
                    partial(TCultivatorBufferRegion,
                            width - 2, height - 2, "dense"),
                    DenseTCultivatorBufferRouter,
                ),
                LayoutNode(
                    partial(BellRegion, height - 2),
                    BellRouter
                )

            ]
        )]
    )
    return layout

@make_widget
def flat_naive_litinski_6x3_dense_unbuffered_widget(
    width, height, include_bell=True
):
    if include_bell:
        layout = LayoutNode(
            partial(SingleRowRegisterRegion, width),
            BaselineRegisterRouter,
            [LayoutNode(
                partial(RouteBus, width),
                StandardBusRouter,
                [
                    LayoutNode(
                        partial(BellRegion, height - 2),
                        BellRouter
                    ),
                    LayoutNode(
                        partial(MagicStateFactoryRegion.with_litinski_6x3_dense,
                                width - 2, height - 2),
                        MagicStateFactoryRouter,
                    ),
                    LayoutNode(
                        partial(BellRegion, height - 2),
                        BellRouter
                    )

                ]
            )]
        )
    else:
        layout = LayoutNode(
            partial(SingleRowRegisterRegion, width),
            BaselineRegisterRouter,
            [LayoutNode(
                partial(RouteBus, width),
                StandardBusRouter,
                [LayoutNode(
                    partial(MagicStateFactoryRegion.with_litinski_6x3_dense,
                            width, height - 2),
                    MagicStateFactoryRouter,
                )]
            )]
        )
    return layout

@make_widget
def buffered_naive_buffered_widget(
    width,
    height,
    buffer_height,
    factory_factory: Callable[[int, int], MagicStateFactoryRegion],
    include_bell: bool = True
):
    if include_bell:
        layout = LayoutNode(
            partial(SingleRowRegisterRegion, width),
            BaselineRegisterRouter,
            [LayoutNode(
                partial(RouteBus, width),
                StandardBusRouter,
                [
                    LayoutNode(
                        partial(BellRegion, height - 2),
                        BellRouter
                    ),
                    LayoutNode(
                        partial(MagicStateBufferRegion,
                                width - 2, buffer_height),
                        RechargableBufferRouter,
                        [LayoutNode(
                            partial(RouteBus, width - 2),
                            StandardBusRouter,
                            [LayoutNode(
                                partial(factory_factory,
                                        width - 2, height - 3 - buffer_height),
                                MagicStateFactoryRouter,
                            )]
                        )]
                    ),
                    LayoutNode(
                        partial(BellRegion, height - 2),
                        BellRouter
                    )
                ]
            )]
        )
    else:
        layout = LayoutNode(
            partial(SingleRowRegisterRegion, width),
            BaselineRegisterRouter,
            [LayoutNode(
                partial(RouteBus, width),
                StandardBusRouter,
                [LayoutNode(
                    partial(MagicStateBufferRegion,
                            width, buffer_height),
                    RechargableBufferRouter,
                    [LayoutNode(
                        partial(RouteBus, width),
                        StandardBusRouter,
                        [LayoutNode(
                            partial(factory_factory,
                                    width, height - 3 - buffer_height),
                            MagicStateFactoryRouter,
                        )]
                    )]
                )]
            )]
        )
    return layout

@make_widget
def vertical_strategy_with_prefilled_buffer_widget(
    width, height
):
    layout = LayoutNode(
        partial(SingleRowRegisterRegion, width),
        BaselineRegisterRouter,
        [LayoutNode(
            partial(RouteBus, width),
            StandardBusRouter,
            [
                LayoutNode(
                    partial(BellRegion, height - 2),
                    BellRouter
                ),
                LayoutNode(
                    partial(PrefilledMagicStateRegion,
                            width - 2, height - 2, 'default'),
                    VerticalFilledBufferRouter,
                ),
                LayoutNode(
                    partial(BellRegion, height - 2),
                    BellRouter
                )

            ]
        )]
    )
    return layout


@make_widget
def vertical_strategy_with_prefilled_comb_widget(
    width, height, comb_height, route_width: Literal[1,2]=2, incl_comb_top=True
):
    layout = LayoutNode(
        partial(CombShapedRegisterRegion, width, comb_height, route_width=route_width, incl_top=incl_comb_top),
        CombRegisterRouter,
        [LayoutNode(
            partial(RouteBus, width),
            StandardBusRouter,
            [
                LayoutNode(
                    partial(BellRegion, height - 1 - comb_height),
                    BellRouter
                ),
                LayoutNode(
                    partial(PrefilledMagicStateRegion,
                            width - 2, height - 1 - comb_height, "default"),
                    VerticalFilledBufferRouter,
                ),
                LayoutNode(
                    partial(BellRegion, height - 1 - comb_height),
                    BellRouter
                )
            ]
        )]
    )
    return layout

def limit_reject(func, *args, **kwargs):
    def wrapped(*args, **kwargs):
        return func(*args, rot_strat=RotationStrategyOption.REJECT, **kwargs)
    return wrapped

@limit_reject
@make_widget
def tree_strategy_with_prefilled_buffer_widget(
    width, height
):
    if width % 4 != 0:
        raise ValueError("Only multiples of 4 supported for width")

    layout = LayoutNode(
        partial(SingleRowRegisterRegion, width),
        BaselineRegisterRouter,
        [LayoutNode(
            partial(RouteBus, width),
            StandardBusRouter,
            [
                LayoutNode(
                    partial(BellRegion, height - 2),
                    BellRouter
                ),
                LayoutNode(
                    partial(PrefilledMagicStateRegion,
                            width - 2, height - 2, "chessboard"),
                    TreeFilledBufferRouter,
                ),
                LayoutNode(
                    partial(BellRegion, height - 2),
                    BellRouter
                )

            ]
        )]
    )
    return layout

