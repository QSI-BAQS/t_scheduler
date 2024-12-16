from typing import List, Tuple
from ..patch import Patch, PatchOrientation, PatchType

class WidgetRegion:
    width: int
    height: int
    sc_patches: List[List[Patch]]

    def __init__(self, width: int, height: int, sc_patches: List[List[Patch]]) -> None:
        self.width = width
        self.height = height
        self.sc_patches = sc_patches

    def update(self) -> None:
        '''
            Updates internal state of the widget region
        '''
        pass

    def __getitem__(self, key: Tuple[int, int] | int) -> Patch:
        if isinstance(key, tuple):
            return self.sc_patches[key[0]][key[1]]
        else:
            return self.sc_patches[key]  # type: ignore
        

    def to_str_output(self) -> str:
        '''
            Prints current state of the region
        '''
        buf = ''
        def bprint(c: str|int ='', end='\n'):
            nonlocal buf
            buf += str(c)
            buf += end

        board = self.sc_patches # type: ignore

        bprint()
        bprint("-" * len(board[0]))
        bprint(' '*len(str(len(board))) + ''.join(map(lambda x: str(x%10),range(len(board[0])))))
        for i, row in enumerate(board):
            bprint(str(i).zfill(len(str(len(board)))), end='')
            for cell in row:
                if cell.patch_type == PatchType.BELL:
                    bprint("$", end="")
                elif cell.locked():
                    num = cell.lock.owner.targ # type: ignore
                    if num >= 10:
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