from __future__ import annotations
from enum import Enum, IntEnum
from typing import List


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


class PatchLock:
    def __init__(self, owner, holds: List[Patch], duration: int):
        self.owner = owner
        self.holds = holds
        self.duration = duration
        # TODO: duration is not used

    def lock(self):
        for patch in self.holds:
            assert patch.lock is None
            # return False

        for patch in self.holds:
            patch.lock = self

        return True

    def unlock(self):
        for patch in self.holds:
            if patch.lock is self:
                patch.lock = None
        self.owner = None


class Patch:
    patch_type: PatchType
    row: int
    col: int
    orientation: PatchOrientation

    def __init__(
        self, patch_type: PatchType, row: int, col: int, starting_orientation=PatchOrientation.Z_TOP
    ):
        self.patch_type = patch_type
        self.row = row
        self.col = col
        self.lock: None | PatchLock = None
        self.orientation = starting_orientation
        self.used = False
        self.release_time = None
        self.rotation = None

    def __repr__(self):
        return f"P({self.row}, {self.col})"

    def locked(self):
        return self.lock is not None

    def T_available(self):
        return self.patch_type == PatchType.T and not self.used and not self.locked()

    def route_available(self):
        return self.patch_type == PatchType.ROUTE and not self.locked()

    def register_rotation(self, gate):
        self.rotation = gate

    def use(self):
        if self.patch_type == PatchType.T:
            self.used = True
        elif self.used:
            raise Exception("T already used!")
        else:
            raise Exception("Can't use non-T!")

    def release(self, time):
        if self.patch_type != PatchType.T or not (self.used):
            raise Exception("Can't release non-T or unused T!")
        self.used = False
        self.release_time = time
        self.patch_type = PatchType.ROUTE
