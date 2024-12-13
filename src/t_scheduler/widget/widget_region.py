from t_scheduler.patch import PatchOrientation, PatchType


class WidgetRegion:
    width: int
    height: int

    def __init__(self, width, height) -> None:
        self.width = width
        self.height = height

    def update(self):
        pass

    def to_str_output(self):
        buf = ''
        def bprint(c: str|int ='', end='\n'):
            nonlocal buf
            buf += str(c)
            buf += end

        board = self.cells # type: ignore

        bprint()
        bprint("-" * len(board[0]))
        bprint(' ' + ''.join(map(str,range(len(board[0])))))
        for i, row in enumerate(board):
            bprint(i, end='')
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