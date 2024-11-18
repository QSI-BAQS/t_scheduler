from enum import Enum
from abc import ABC



class Gate():
    def __init__(self, targ):
        self.targ: int = targ
        self.lock: None | PatchLock = None

class PatchType(Enum):
    REG = 1
    ROUTE = 2
    T = 3
    BELL = 4

class PatchOrientation(Enum):
    X_TOP = 0
    Z_TOP = 1

class Patch:
    def __init__(self, patch_type: PatchType, row: int, col: int):
        self.patch_type = patch_type
        self.row = row
        self.col = col
        self.lock: None | PatchLock = None
        self.orientation = PatchOrientation.Z_TOP
        self.used = False
    
    def __repr__(self):
        return f"P({self.row}, {self.col})"

    def locked(self): 
        return self.lock is not None

    def T_available(self):
        return self.patch_type == PatchType.T and not self.used
    
    def use(self):
        if self.patch_type == PatchType.T:
            self.used = True
        else:
            raise Exception("Can't use non-T!")

class PatchLock:
    def __init__(self, owner: "Gate", holds: list[Patch], duration: int):
        self.owner = owner
        self.holds = holds
        self.duration = duration

    def lock(self):
        for patch in self.holds:
            patch.lock = self

    def unlock(self):
        for patch in self.holds:
            if patch.lock is self:
                patch.lock = None
        self.owner = None

class Route:
    def __init__(self, gate: Gate, patches: list[Patch]):
        self.gate = gate
        self.path = [(patch.row, patch.col) for patch in patches]


def create_default_board(w: int, h: int):
    # row-major (row, col)
    reg_row = [Patch(PatchType.REG, 0, c) for c in range(w)]
    route_row = [Patch(PatchType.ROUTE, 1, c) for c in range(w)]
    board = [reg_row, route_row]
    for r in range(2, h):
        row = [Patch(PatchType.BELL, r, 0), 
               *(Patch(PatchType.T, r, c) for c in range(1, w-1)),
               Patch(PatchType.BELL, r, w-1)]
        board.append(row)
    return board
