from __future__ import annotations
from enum import IntEnum
from typing import List, Tuple
from ..base import Patch, PatchOrientation, PatchType

class TopEdgePosition(IntEnum):
    TOP = 0
    RIGHT = 90
    BOTTOM = 180
    LEFT = 270

class RegionStats(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self['num_registers'] = self.get('num_registers', 0)
        self['num_t_buffers'] = self.get('num_t_buffers', 0)
        self['num_bell_buffers'] = self.get('num_bell_buffers', 0)

    def __add__(self, other):
        res = RegionStats(self)
        for key, val in other.items():
            res[key] = res.get(key, 0) + val
        return res

    @property
    def num_registers(self):
        return self['num_registers']

    @property
    def num_t_buffers(self):
        return self['num_t_buffers']

    @property
    def num_bell_buffers(self):
        return self['num_bell_buffers']

class WidgetRegionView:
    def __init__(self, underlying):
        self.underlying = underlying


    def tl(self, local_pos: Tuple[int, int]) -> Tuple[int, int]:
        '''
            Input: Row, col
        '''
        if self.underlying.rotation == TopEdgePosition.TOP:
            new_pos = local_pos
        elif self.underlying.rotation == TopEdgePosition.BOTTOM:
            new_pos = self.underlying.height - 1 - local_pos[0], self.underlying.width - 1 - local_pos[1]
        elif self.underlying.rotation == TopEdgePosition.RIGHT:
            new_pos = local_pos[1], self.underlying.height - 1 - local_pos[0]
        elif self.underlying.rotation == TopEdgePosition.LEFT:
            new_pos = self.underlying.width - 1 - local_pos[1], local_pos[0]
        else:
            raise NotImplementedError()
        return new_pos
        
    def __getitem__(self, key: Tuple[int, int]) -> Patch:
        return self.underlying[self.tl(key)]
    
    def __getattr__(self, name):
        return self.underlying.__getattribute__(name)

class WidgetRegion:
    width: int
    height: int
    sc_patches: List[List[Patch]]
    upstream: WidgetRegion | None
    downstream: List[WidgetRegion]
    stats: RegionStats = None # type: ignore
    offset: Tuple[int, int] # Position of top left cell in global coordinates
    rotation = 0 # Bearing of top edge in [0, 90, 180, 270]

    def __init__(self, width: int, height: int, 
                 sc_patches: List[List[Patch]], 
                 upstream: WidgetRegion | None = None, 
                 downstream: List[WidgetRegion] | None = None,
                 *,
                 x = None,
                 y = None,
                 **kwargs) -> None:
        self.width = width
        self.height = height
        self.sc_patches = sc_patches
        self.upstream = upstream
        if downstream:
            self.downstream = downstream
        else:
            self.downstream = []
        if self.stats == None:
            self.stats = RegionStats()
        self.offset = (y, x) # type: ignore

        # print(self.offset, self.upstream)
        # if self.upstream: print("up:", self.upstream.offset)

        # Calculate rotation
        if self.offset != (None, None) and self.upstream and self.upstream.offset != (None, None):
            # Can calc rotation
            self_row = self.offset[0]
            self_col = self.offset[1]
            upstream_row = self.upstream.offset[0]
            upstream_col = self.upstream.offset[1]
            if self_row >= upstream_row + self.upstream.height:
                # We are below
                self.rotation = TopEdgePosition.TOP
            elif self_row + self.height <= upstream_row:
                # We are above
                self.rotation = TopEdgePosition.BOTTOM
            elif self_col >= upstream_col + self.upstream.width:
                # We are right
                self.rotation = TopEdgePosition.LEFT
            elif self_col + self.width <= upstream_col:
                # We are left
                self.rotation = TopEdgePosition.RIGHT
            # print("got rotation:", self.rotation)

        self.local_view = WidgetRegionView(self)

        # for key in kwargs:
        #     print(f'Ignoring unknown parameter: {key}')

    def update(self) -> None:
        """
        Updates internal state of the widget region
        """
        pass

    def __getitem__(self, key: Tuple[int, int] | int) -> Patch:
        if isinstance(key, tuple) or isinstance(key, list):
            return self.sc_patches[key[0]][key[1]]
        elif isinstance(key, int):
            return self.sc_patches[key]  # type: ignore
        else:
            raise TypeError('Invalid index type:', key)
    
    def tl(self, pos):
        return pos

    def to_str_output(self) -> str:
        """
        Prints current state of the region
        """
        buf = ""

        def bprint(c: str | int = "", end="\n"):
            nonlocal buf
            buf += str(c)
            buf += end

        board = self.sc_patches  # type: ignore

        bprint()
        bprint("-" * len(board[0]))
        bprint(
            " " * len(str(len(board)))
            + "".join(map(lambda x: str(x % 10), range(len(board[0]))))
        )
        for i, row in enumerate(board):
            bprint(str(i).zfill(len(str(len(board)))), end="")
            for cell in row:
                if cell.patch_type == PatchType.BELL:
                    bprint("$", end="")
                elif cell.locked():
                    num = cell.lock.owner.targ  # type: ignore
                    if num >= 10:
                        num = "#"
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
