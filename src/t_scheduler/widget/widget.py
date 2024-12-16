
from __future__ import annotations
from typing import List
from t_scheduler.patch import Patch, PatchOrientation, PatchType
from t_scheduler.widget.widget_region import WidgetRegion

class Widget:
    def __init__(self, width: int, height: int, board: List[List[Patch]], components: List[WidgetRegion] = []):
        self.width: int = width
        self.height: int = height

        self.board = board
        self.components = components

        self.rep_count = 1
        self.last_output = ''

    def update(self):
        for component in self.components:
            component.update()

    def __getitem__(self, index) -> Patch | List[Patch]:
        if isinstance(index, tuple) and len(index) == 2:
            return self.board[index[0]][index[1]]
        elif isinstance(index, int):
            return self.board[index]
        else:
            raise TypeError("Invalid index type for Widget:", type(index))

    def to_str_output(self):
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
                    num = cell.lock.owner.targ # type: ignore
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
    

    def to_str_output_dedup(self):
        buf = self.to_str_output()
        if buf == self.last_output:
            self.rep_count += 1
            return f'\rX{self.rep_count}'
        else:
            self.last_output = buf
            self.rep_count = 1
            return buf + '\n'

