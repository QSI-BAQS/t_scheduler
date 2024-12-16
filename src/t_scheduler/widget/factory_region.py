from typing import List, Tuple

from t_scheduler.t_generation.t_factories import TFactory_Litinski_5x3_15_to_1, TFactory_Litinski_6x3_20_to_4_dense

from .widget_region import WidgetRegion
from ..patch import Patch, PatchType, TFactoryOutputPatch


class MagicStateFactoryRegion(WidgetRegion):

    def __init__(self, width, height):
        sc_patches = [
            [
                Patch(PatchType.ROUTE, r, c) for c in range(width)
            ]
            for r in range(height)
        ]
        super().__init__(width, height, sc_patches)
        self.factories = []
        self.active_factories = set()
        self.available_states = set()
        self.waiting_factories = set()

    def add_factory(self, row, col, factory):
        if not (0 <= row and row + factory.height <= self.height and 0 <= col and col + factory.width <= self.width):
            raise ValueError("Factory out of bounds!")

        for r in range(row, row + factory.height):
            for c in range(col, col + factory.width):
                assert self.sc_patches[r][c].patch_type == PatchType.ROUTE

                self.sc_patches[r][c].patch_type = PatchType.RESERVED

        factory.outputs = []

        for r_off, c_off in factory.positions:
            r, c = row + r_off, col + c_off
            if self.sc_patches[r][c].patch_type == PatchType.RESERVED:
                self.sc_patches[r][c] = TFactoryOutputPatch(r, c, factory)
            factory.outputs.append(self.sc_patches[r][c])
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
    def with_litinski_5x3(width, height):
        if height < 5:
            raise ValueError

        msf_region = MagicStateFactoryRegion(width, height)

        for col in range(0, width - 2, 3):
            msf_region.add_factory(
                height - 5, col, TFactory_Litinski_5x3_15_to_1())
            print(height - 5, col)

        for row in range(height - 11, -1, -6):
            for col in range(0, width - 2, 4):
                msf_region.add_factory(
                    row, col, TFactory_Litinski_5x3_15_to_1())
                print(row, col)
        return msf_region

    @staticmethod
    def with_litinski_6x3_dense(width, height):
        if height < 6:
            raise ValueError

        msf_region = MagicStateFactoryRegion(width, height)

        for col in range(0, width - 2, 3):
            msf_region.add_factory(
                height - 6, col, TFactory_Litinski_6x3_20_to_4_dense())
            print(height - 6, col)

        for row in range(height - 13, -1, -7):
            for col in range(0, width - 2, 4):
                msf_region.add_factory(
                    row, col, TFactory_Litinski_6x3_20_to_4_dense())
                print(row, col)
        return msf_region
