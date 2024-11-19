from enum import Enum
from abc import ABC
from itertools import cycle, islice


class GateType(Enum):
    NO_RESOURCE = 1
    ANCILLA = 2
    T_STATE = 3

class Gate():
    def __init__(self, targ, gate_type = GateType.T_STATE, duration = 1):
        self.targ: int = targ
        self.lock: None | PatchLock = None
        self.gate_type = gate_type
        self.duration = duration
        self.timer = 0
        self.resource = None

    def tick(self):
        self.timer += 1
    
    def retirable(self):
        return self.timer >= self.duration
    
    def activate(self, path, resource = None):
        self.path = path
        self.lock = PatchLock(self, path, self.duration)
        if resource:
            resource.use()
            self.resource = resource
        self.lock.lock()
    
    def retire(self):
        if self.resource:
            self.resource.release()
        assert self.lock is not None
        self.lock.unlock()
        



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
    
    def route_available(self):
        return self.patch_type == PatchType.ROUTE and not self.locked()

    def use(self):
        if self.patch_type == PatchType.T:
            self.used = True
        else:
            raise Exception("Can't use non-T!")
        
    def release(self):
        if self.patch_type != PatchType.T or not (self.used):
            raise Exception("Can't release non-T or unused T!")
        self.used = False
        self.patch_type = PatchType.ROUTE

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


class Widget:
    def __init__(self, width, height):
        self.width: int = width
        self.height: int = height

        reg_row = [Patch(PatchType.REG, 0, c) for c in range(width)]
        route_row = [Patch(PatchType.ROUTE, 1, c) for c in range(width)]
        board = [reg_row, route_row]
        for r in range(2, height):
            row = [Patch(PatchType.BELL, r, 0), 
                *(Patch(PatchType.T, r, c) for c in range(1, width-1)),
                Patch(PatchType.BELL, r, width-1)]
            board.append(row)
        self.board = board

    def __getitem__(self, index):
        if isinstance(index, tuple):
            return self.board[index[0]][index[1]]
        return self.board[index]
    




def roundrobin(*iterables):
    "Visit input iterables in a cycle until each is exhausted."
    # roundrobin('ABC', 'D', 'EF') → A D E B F C
    # Algorithm credited to George Sakkis
    iterators = map(iter, iterables)
    for num_active in range(len(iterables), 0, -1):
        iterators = cycle(islice(iterators, num_active))
        yield from map(next, iterators)