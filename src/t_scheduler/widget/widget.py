from __future__ import annotations
from typing import Dict, List, Tuple

from t_scheduler.widget import route_bus


from .widget_region import WidgetRegion
from ..base.patch import Patch, PatchOrientation, PatchType

class Widget:
    def __init__(self, width: int, height: int, board: List[List[Patch]], components: List[WidgetRegion] = []):
        '''
            width: width of widget
            height: height of widget
            board: backing cells of widget
            component: component regions of widget
        '''
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

    def __getitem__(self, index: Tuple[int, int] | int) -> Patch | List[Patch]:
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

    def get_component_info(self):
        '''
            Get info about substituent components (such as regions occupied)
        '''
        info = []
        for component in self.components:
            component_typename = component.__class__.__name__
            coords = (self.adapter[component.sc_patches[0][0]],
                      self.adapter[component.sc_patches[-1][-1]])
            info.append((component, component_typename, coords))
        return info

    @staticmethod
    def _to_tikz_coords(start, end, sep: float = 0):
        return start[1] + sep, -start[0] - sep, end[1] + 1 - sep, -end[0] - 1 + sep

    @staticmethod
    def _component_to_style(component):
        from t_scheduler.widget.registers import RegisterRegion
        from t_scheduler.widget.route_bus import RouteBus
        from t_scheduler.widget.magic_state_buffer import AbstractMagicStateBufferRegion
        from t_scheduler.widget.factory_region import MagicStateFactoryRegion
        from lattice_surgery_draw.primitives.style import TikzStyle

        if isinstance(component, RegisterRegion):
            return TikzStyle(fill='red!10')
        elif isinstance(component, RouteBus):
            return TikzStyle(fill='green!10')
        elif isinstance(component, AbstractMagicStateBufferRegion):
            return TikzStyle(fill='blue!10')
        elif isinstance(component, MagicStateFactoryRegion):
            return TikzStyle(fill='blue!10')

    @staticmethod
    def _patch_to_char(cell):
        if cell.patch_type == PatchType.BELL:
            return "$"
        elif cell.locked():
            num = cell.lock.owner.targ  # type: ignore
            if not isinstance(num, str) and num >= 10:
                num = '#'
            return str(num)
        elif cell.patch_type == PatchType.REG:
            return "R"
        elif cell.route_available():
            return "="
        elif cell.patch_type == PatchType.ROUTE:
            return " "
        elif cell.T_available():
            if cell.orientation == PatchOrientation.Z_TOP:
                return "T"
            else:
                return "t"
        elif cell.patch_type == PatchType.CULTIVATOR:
            return "@"
        elif cell.patch_type == PatchType.RESERVED:
            return ' '
        elif cell.patch_type == PatchType.FACTORY_OUTPUT:
            return '@'
        else:
            return "."

    def save_tikz_region_layer(self):
        from lattice_surgery_draw.region import Region
        from t_scheduler.widget.factory_region import MagicStateFactoryRegion
        from lattice_surgery_draw.primitives.style import TikzStyle

        regions = self.get_component_info()

        output_rects = []

        for component, component_name, coords in regions:
            output_rects.append(Region(
                *self._to_tikz_coords(*coords), region_style=self._component_to_style(component)))
            if isinstance(component, MagicStateFactoryRegion):
                for factory in component.factories:
                    top_left = self.adapter[component[factory.layout_position]]
                    bottom_right = (
                        top_left[0] + factory.height - 1, top_left[1] + factory.width - 1)

                    output_rects.append(Region(
                        *self._to_tikz_coords(top_left, bottom_right, sep=0.05), region_style=TikzStyle(fill='blue!30')))

        return output_rects

    def save_tikz_patches_layer(self):

        from lattice_surgery_draw.primitives.tikz_obj import TikzRectangle, TikzNode, TikzCircle
        from lattice_surgery_draw.primitives.style import TikzStyle
        from lattice_surgery_draw.img import SurfaceCodePatch, SurfaceCodePatchWide
        from t_scheduler.widget.registers import SingleRowRegisterRegion, CombShapedRegisterRegion
        from itertools import chain

        output_objs = []

        for component in self.components:
            if isinstance(component, SingleRowRegisterRegion):
                for cell_idx in range(0, component.width, 2):
                    cell = component.sc_patches[0][cell_idx]
                    coord = self.adapter[cell]
                    output_objs.append(TikzRectangle(
                        *self._to_tikz_coords(coord, (coord[0], coord[1] + 1), sep=0.1)
                    ))
                    output_objs.append(SurfaceCodePatchWide(
                        coord[1] + 1, -coord[0] - 0.5
                    ))
                    output_objs.append(TikzCircle(
                        coord[1] + 1, -coord[0] - 0.5, 0.4, label=str(cell_idx // 2), tikz_style=TikzStyle(fill='red!50')))
            elif isinstance(component, CombShapedRegisterRegion):
                for r, row in enumerate(component.sc_patches):
                    for c, cell in enumerate(row):
                        if cell.patch_type == PatchType.REG:
                            coord = self.adapter[cell]
                            output_objs.append(TikzRectangle(
                                *self._to_tikz_coords(coord, (coord[0], coord[1]), sep=0.1)
                            ))
                            output_objs.append(SurfaceCodePatch(
                                coord[1] + 0.5, -coord[0] - 0.5
                            ))
                            # output_objs.append(TikzCircle(
                            #     coord[1] + 0.5, -coord[0] - 0.5, 0.4, label=str(cell_idx // 2), tikz_style=TikzStyle(fill='red!50')))
                        else:
                            coord = self.adapter[cell]
                            output_objs.append(TikzNode(coord[1] + 0.5, -coord[0] - 0.5, label=self._patch_to_char(cell)
                                                        ))
            else:
                for cell in chain(*component.sc_patches):
                    coord = self.adapter[cell]
                    output_objs.append(TikzRectangle(
                        *self._to_tikz_coords(coord, coord, sep=0.1)
                    ))
                    if cell.T_available():
                        angle = 90 if cell.orientation == PatchOrientation.Z_TOP else 0
                        output_objs.append(SurfaceCodePatch(
                            coord[1] + 0.5, -coord[0] - 0.5, angle=angle))
                        output_objs.append(TikzCircle(coord[1] + 0.5, -coord[0] - 0.5, 0.4, label=self._patch_to_char(cell),
                                                      tikz_style=TikzStyle(fill='blue!50', text='white')))
                    else:
                        output_objs.append(TikzNode(coord[1] + 0.5, -coord[0] - 0.5, label=self._patch_to_char(cell)
                                                    ))

        return output_objs

    def make_tikz_routes(self, output_layer):
        from lattice_surgery_draw.primitives.tikz_obj import TikzRectangle, TikzNode, TikzCircle
        from lattice_surgery_draw.primitives.style import TikzStyle

        def _manhattan(pos1, pos2):
            return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])

        output_rects = []

        for gate_path in output_layer:
            gate_path = list(map(self.adapter.get, gate_path))
            if None in gate_path: raise Exception('Invalid cell in adapter')
            if len(gate_path) == 2 and _manhattan(gate_path[0], gate_path[1]) > 1:
                # Measure activation!
                pass
            else:
                for first, second in zip(gate_path[:-1], gate_path[1:]):
                    if _manhattan(first, second) > 1:
                        if self[first].lock.owner.__class__.__name__ == 'RotateGate': # type: ignore
                            continue
                        # Error! TODO remove after debugging
                        with open('check.out', 'a') as check:
                            print(self.to_str_output(), file=check)
                            print(gate_path, file=check)
                        # raise Exception('debug')
                        return []
                    else:
                        output_rects.append(TikzRectangle(*self._to_tikz_coords(*sorted((first, second)), sep=0.2), # type: ignore
                                            tikz_style=TikzStyle(draw='none', fill='orange', opacity='0.3')))  
        return output_rects

    def save_tikz_frame(self, additional=tuple()):
        from lattice_surgery_draw.primitives.composers import TikzFrame
        return TikzFrame(*self.save_tikz_region_layer(), *self.save_tikz_patches_layer(), *additional)
