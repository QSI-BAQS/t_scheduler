from __future__ import annotations
from typing import Dict, List, Tuple

from t_scheduler.widget.registers import RegisterRegion, SingleRowRegisterRegion

from .widget_region import WidgetRegion
from ..patch import Patch, PatchOrientation, PatchType

class Widget:
    def __init__(self, width: int, height: int, board: List[List[Patch]], components: List[WidgetRegion] = []):
        self.width: int = width
        self.height: int = height

        self.board = board
        self.components = components

        self.rep_count = 1
        self.last_output = ''

    def update(self) -> None:
        '''
            Executes update() on all consituent components
        '''
        for component in self.components:
            component.update()

    def __getitem__(self, index) -> Patch | List[Patch]:
        if isinstance(index, tuple) and len(index) == 2:
            return self.board[index[0]][index[1]]
        elif isinstance(index, int):
            return self.board[index]
        else:
            raise TypeError("Invalid index type for Widget:", type(index))

    def to_str_output(self) -> str:
        '''
            Get pretty printed output of board states
        '''
        buf = ''

        def bprint(c='', end='\n'):
            nonlocal buf
            buf += str(c)
            buf += end

        board = self.board

        bprint()
        bprint("-" * len(board[0]))
        for row in board:
            for cell in row:
                if cell.patch_type == PatchType.BELL:
                    bprint("$", end="")
                elif cell.locked():
                    num = cell.lock.owner.targ  # type: ignore
                    if not isinstance(num, str) and num >= 10:
                        num = '#'
                    bprint(num, end="")
                elif cell.patch_type == PatchType.REG:
                    bprint("R", end="")
                elif cell.patch_type == PatchType.ROUTE:
                    bprint(" ", end="")
                elif cell.T_available():
                    if cell.orientation == PatchOrientation.Z_TOP:
                        bprint("T", end="")
                    else:
                        bprint("t", end="")
                elif cell.patch_type == PatchType.CULTIVATOR:
                    bprint("@", end="")
                else:
                    bprint(".", end="")
            bprint()
        bprint("-" * len(board[0]), end="")

        return buf

    def to_str_output_dedup(self) -> str:
        '''
            Get pretty printed output of board states. 

            If output is same as last output (in calls to this), print instead how many times
            the same output has been generated. Also updates an internal print repetition counter 
        '''
        buf = self.to_str_output()
        if buf == self.last_output:
            self.rep_count += 1
            return f'\rX{self.rep_count}'
        else:
            self.last_output = buf
            self.rep_count = 1
            return buf + '\n'

    def make_coordinate_adapter(self) -> None:
        '''
            Generate a coordinate adapter for local patches to global coordinates
        '''
        self.adapter = {}
        for r, cell_row in enumerate(self.board):
            for c, cell in enumerate(cell_row):
                self.adapter[cell] = (r, c)

    def get_component_info(self) -> Dict[str, Tuple[Tuple[int, int], Tuple[int, int]]]:
        '''
            Get info about substituent components (such as regions occupied)
        '''
        info = {}
        for component in self.components:
            component_typename = component.__class__.__name__
            coords = (self.adapter[component.sc_patches[0][0]],
                      self.adapter[component.sc_patches[-1][-1]])
            info[component_typename] = coords
        return info

    @staticmethod
    def _to_tikz_coords(start, end, sep: float = 0):
        return start[1] + sep, -start[0] - sep, end[1] + 1 - sep, -end[0] - 1 + sep

    def save_tikz_region_layer(self):
        from lattice_surgery_draw.tikz_obj import TikzRectangle

        regions = self.get_component_info()

        output_rects = []

        for component_name, coords in regions.items():
            output_rects.append(TikzRectangle(*self._to_tikz_coords(*coords)))

        return output_rects

    def save_tikz_patches_layer(self):
        from lattice_surgery_draw.tikz_obj import TikzRectangle, TikzNode
        from itertools import chain
        regions = self.get_component_info()

        output_objs = []

        for component in self.components:
            if isinstance(component, SingleRowRegisterRegion):
                for cell_idx in range(0, component.width, 2):
                    cell = component.sc_patches[0][cell_idx]
                    coord = self.adapter[cell]
                    output_objs.append(TikzRectangle(
                        *self._to_tikz_coords(coord, (coord[0], coord[1] + 1), sep=0.1)
                    ))
                    output_objs.append(TikzNode(
                        coord[1] + 0.5, -coord[0] - 0.5, label=str(cell_idx // 2)))
            else:
                for cell in chain(*component.sc_patches):
                    coord = self.adapter[cell]
                    output_objs.append(TikzRectangle(
                        *self._to_tikz_coords(coord, coord, sep=0.1)
                    ))
                    if cell.T_available():
                        output_objs.append(TikzNode(coord[1] + 0.5, -coord[0] - 0.5, label = "T"
                        ))
                    if cell.route_available():
                        output_objs.append(TikzNode(coord[1] + 0.5, -coord[0] - 0.5, label = "="
                        ))

        return output_objs
