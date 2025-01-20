from typing import List, Literal, Set, Tuple

from ..t_generation.t_factories import (
    TFactory_Litinski_5x3_15_to_1,
    TFactory_Litinski_6x3_20_to_4_dense,
)

from .region_types import export_region, FACTORY_REGION 

from .widget_region import TopEdgePosition, WidgetRegion
from ..base.patch import Patch, PatchType, TCultPatch, TFactoryOutputPatch

import itertools

class AbstractFactoryRegion(WidgetRegion):
    available_states: Set[Patch]
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class MagicStateFactoryRegion(WidgetRegion):
    available_states: Set[Patch]
    
    def __init__(self, width, height, **kwargs):
        sc_patches = [
            [Patch(PatchType.ROUTE, r, c) for c in range(width)] for r in range(height)
        ]
        super().__init__(width, height, sc_patches, **kwargs)
        self.factories = []
        self.active_factories = set()
        self.available_states = set()
        self.waiting_factories = set()

    def _set_local(self, row, col, new_patch):
        assert self.rotation in [TopEdgePosition.TOP, TopEdgePosition.BOTTOM]
        row, col = self.local_view.tl((row, col))
        self.sc_patches[row][col] = new_patch

    def _get_local(self, row, col):
        assert self.rotation in [TopEdgePosition.TOP, TopEdgePosition.BOTTOM]
        row, col = self.local_view.tl((row, col))
        return self.sc_patches[row][col]

    def add_factory(self, row, col, factory):
        if not (
            0 <= row
            and row + factory.height <= self.height
            and 0 <= col
            and col + factory.width <= self.width
        ):
            raise ValueError("Factory out of bounds!")

        for r in range(row, row + factory.height):
            for c in range(col, col + factory.width):
                assert self._get_local(r,c).patch_type == PatchType.ROUTE

                self._get_local(r,c).patch_type = PatchType.RESERVED

        factory.outputs = []

        factory_corners = [
            (row, col), (row, col + factory.width - 1),
            (row + factory.height - 1, col), (row + factory.height - 1, col + factory.width - 1)
        ]
        factory_corners = list(map(self.local_view.tl, factory_corners))
        factory.layout_position = min(factory_corners)

        for r_off, c_off in factory.positions:
            r, c = row + r_off, col + c_off
            if self._get_local(r,c).patch_type == PatchType.RESERVED:
                self._set_local(r, c, TFactoryOutputPatch(r, c, factory))
            factory.outputs.append(self._get_local(r,c))
        self.factories.append(factory)
        self.active_factories.add(factory)

    def update(self):
        completed = set()
        for factory in self.waiting_factories:
            if all(o.t_count == 0 and not o.locked() for o in factory.outputs):  # type: ignore
                factory.reset()
                completed.add(factory)
        self.waiting_factories.difference_update(completed)
        self.active_factories.update(completed)

        completed = set()
        for factory in self.active_factories:
            if factory.update():
                completed.add(factory)
        self.active_factories.difference_update(completed)
        self.waiting_factories.update(completed)
        for factory in completed:
            for output in factory.outputs:
                output.t_count += 1
                self.available_states.add(output)

    def release_cells(self, sc_patches: List[Patch]):
        for cell in sc_patches:
            # TODO time etc.
            cell.release(None)

    @staticmethod
    def with_factory_factory(width, height, factory_width, factory_height, factory, **kwargs):
        if height < factory_height:
            raise ValueError('Height too small for factory!')

        msf_region = MagicStateFactoryRegion(width, height, **kwargs)
        for col in range(0, width - factory_width + 1, factory_width):
            msf_region.add_factory(height - factory_height, col, factory())

        for row in range(height - 2 * factory_height - 1, -1, -factory_height - 1):
            for col in range(0, width - factory_width + 1, factory_width + 1):
                msf_region.add_factory(row, col, factory())

        return msf_region

    @export_region(FACTORY_REGION)
    @staticmethod
    def with_litinski_5x3(width, height, **kwargs):
        return MagicStateFactoryRegion.with_factory_factory(width, height, 3, 5, TFactory_Litinski_5x3_15_to_1, **kwargs)

    @export_region(FACTORY_REGION)
    @staticmethod
    def with_litinski_6x3_dense(width, height, **kwargs):
        return MagicStateFactoryRegion.with_factory_factory(width, height, 3, 6, TFactory_Litinski_6x3_20_to_4_dense, **kwargs)



class TCultivatorBufferRegion(AbstractFactoryRegion):
    available_states: Set[TCultPatch]
    update_cells: List[TCultPatch]

    @export_region(FACTORY_REGION)
    @staticmethod
    def with_dense_layout(*args, buffer_type = 'dense', **kwargs):
        assert buffer_type == 'dense'
        return TCultivatorBufferRegion(*args, buffer_type = 'dense', **kwargs)

    @staticmethod
    def with_sparse_layout(*args, buffer_type = 'sparse', **kwargs):
        assert buffer_type == 'sparse'
        return TCultivatorBufferRegion(*args, buffer_type = 'sparse', **kwargs)

    def __init__(self, width, height, buffer_type: Literal["dense", "sparse"] = 'dense', **kwargs) -> None:
        self.available_states = set()

        if buffer_type == "dense":
            sc_patches = [
                [TCultPatch(r, c) for c in range(width)] for r in range(height)
            ]
            self.update_cells = list(itertools.chain(*sc_patches))  # type: ignore
        elif buffer_type == "sparse":
            sc_patches = []
            self.update_cells = []
            for r in range(height):
                if (height - r) % 3 == 2:
                    row = [Patch(PatchType.ROUTE, r, c) for c in range(width)]
                else:
                    row = [TCultPatch(r, c) for c in range(width)]
                    self.update_cells.extend(row)
                sc_patches.append(row)

        super().__init__(width, height, sc_patches, **kwargs)  # type: ignore

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