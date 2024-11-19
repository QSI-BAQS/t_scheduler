from enum import Enum, IntEnum
from abc import ABC
from itertools import cycle, islice


class GateType(Enum):
    NO_RESOURCE = 1
    ANCILLA = 2
    T_STATE = 3

class BaseGate(ABC):
    def available(self):
        return True

    def tick(self):
        pass
    def completed(self) -> bool:
        return False
    def activate(self, *args):
        pass

    def cleanup(self):
        pass
    def next(self, scheduler):
        pass


class Gate(BaseGate):
    def __init__(self, targ, gate_type = GateType.T_STATE, duration = 1):
        self.targ: int = targ
        self.lock: None | PatchLock = None
        self.gate_type = gate_type
        self.duration = duration
        self.timer = 0
        self.resource = None

    def tick(self):
        self.timer += 1
    
    def completed(self):
        return self.timer >= self.duration
    
    def activate(self, path, resource = None):
        self.path = path
        self.lock = PatchLock(self, path, self.duration)
        if resource:
            resource.use()
            self.resource = resource
        self.lock.lock()
    
    def cleanup(self):
        if self.resource:
            self.resource.release()
        assert self.lock is not None
        self.lock.unlock()
    
    def next(self):
        pass

class RotateGate(BaseGate):
    def __init__(self, path, dependent_gate):
        self.t_patch = path[0]
        self.path = [path[0], path[1], path[-1]]
        self.dependent_gate = dependent_gate
        self.timer = 0
        self.lock = None
        self.targ = dependent_gate.targ
    
    def activate(self):
        self.lock = PatchLock(self, self.path, 3)
        self.lock.lock()

    
    def tick(self):
        self.timer += 1
    
    def cleanup(self):
        if self.timer >= 3:
            assert self.lock
            self.lock.unlock()
    
    def completed(self):
        return self.timer >= 3

    def next(self, scheduler):
        if self.completed():
            self.t_patch.orientation = self.t_patch.orientation.inverse()
            scheduler.deferred.append(self.dependent_gate)

class MeasureGate(BaseGate):
    def __init__(self, reg_patch, t_patch):
        self.reg_patch = reg_patch
        self.t_patch = t_patch
    
        self.path = [t_patch, reg_patch]
        self.timer = 0
        self.lock = None
        self.targ = reg_patch.col // 2
    
    def activate(self):
        self.lock = PatchLock(self, self.path, 3)
        self.lock.lock()

    
    def tick(self):
        self.timer += 1
    
    def cleanup(self):
        if self.timer >= 3:
            assert self.lock
            self.lock.unlock()
            self.t_patch.release()

    def completed(self):
        return self.timer >= 3        
    
    

class T_Gate(Gate):
    def __init__(self, targ):
        super().__init__(targ, GateType.T_STATE, 6)

    def activate(self, path, resource: "Patch"):
        self.path = path
        self.resource = resource

        self.resource.use()
      
        self.lock = PatchLock(self, self.path, 3)
        self.lock.lock()
   
    def tick(self):
        self.timer += 1
    
    def cleanup(self):
        if self.timer >= 3:
            assert self.lock
            self.lock.unlock()
    
    def completed(self):
        return self.timer >= 3

    def next(self, scheduler):
        if self.completed():
            m_gate = MeasureGate(self.path[-1], self.path[0])
            m_gate.activate()
            scheduler.next_active.append(m_gate)


class PatchType(Enum):
    REG = 1
    ROUTE = 2
    T = 3
    BELL = 4

class PatchOrientation(IntEnum):
    X_TOP = 0
    Z_TOP = 1

    def inverse(self):
        return PatchOrientation(1 - int(self))

class Patch:
    def __init__(self, patch_type: PatchType, row: int, col: int, ori = PatchOrientation.Z_TOP):
        self.patch_type = patch_type
        self.row = row
        self.col = col
        self.lock: None | PatchLock = None
        self.orientation = ori
        self.used = False
    
    def __repr__(self):
        return f"P({self.row}, {self.col})"

    def locked(self): 
        return self.lock is not None

    def T_available(self):
        return self.patch_type == PatchType.T and not self.used and not self.locked()
    
    def route_available(self):
        return self.patch_type == PatchType.ROUTE and not self.locked()

    def use(self):
        if self.patch_type == PatchType.T:
            self.used = True
        elif self.used == True:
            raise Exception("T already used!")
        else:
            raise Exception("Can't use non-T!")
        
    def release(self):
        if self.patch_type != PatchType.T or not (self.used):
            raise Exception("Can't release non-T or unused T!")
        self.used = False
        self.patch_type = PatchType.ROUTE

class PatchLock:
    def __init__(self, owner: "BaseGate", holds: list[Patch], duration: int):
        self.owner = owner
        self.holds = holds
        self.duration = duration

    def lock(self):
        for patch in self.holds:
            assert patch.lock == None
                # return False

        for patch in self.holds:
            patch.lock = self

        return True

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
    def __init__(self, width, height, board):
        self.width: int = width
        self.height: int = height

        self.board = board

    @classmethod
    def default_widget(cls, width, height):
        reg_row = [Patch(PatchType.REG, 0, c) for c in range(width)]
        route_row = [Patch(PatchType.ROUTE, 1, c) for c in range(width)]
        board = [reg_row, route_row]
        for r in range(2, height):
            row = [Patch(PatchType.BELL, r, 0), 
                *(Patch(PatchType.T, r, c) for c in range(1, width-1)),
                Patch(PatchType.BELL, r, width-1)]
            board.append(row)
        return Widget(width, height, board)
    
    @classmethod
    def chessboard_widget(cls, width, height):
        reg_row = [Patch(PatchType.REG, 0, c) for c in range(width)]
        route_row = [Patch(PatchType.ROUTE, 1, c) for c in range(width)]
        top_T = [Patch(PatchType.BELL, 2, 0), 
                *(Patch(PatchType.T, 2, c,) for c in range(1, width-1)),
                Patch(PatchType.BELL, 2, width-1)]
        board = [reg_row, route_row, top_T]
        for r in range(3, height):
            row = [Patch(PatchType.BELL, r, 0), Patch(PatchType.T, r, 1),
                *(Patch(PatchType.T, r, c, PatchOrientation((r ^ c) & 1) ^ (c >= width // 2)) for c in range(2, width-2)),
                Patch(PatchType.T, r, width-2), Patch(PatchType.BELL, r, width-1)]
            board.append(row)
        return Widget(width, height, board)

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