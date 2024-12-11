from __future__ import annotations
from enum import Enum, IntEnum
from typing import List

from t_scheduler.t_generation import t_cultivator
from t_scheduler.t_generation.t_factories import TFactory_Litinski_3x6


class PatchType(Enum):
    REG = 1
    ROUTE = 2
    ROUTE_BUFFER = 3
    T = 4
    BELL = 5
    CULTIVATOR = 6
    FACTORY_OUTPUT = 7
    RESERVED = 8


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

class BufferPatch(Patch):
    def __init__(
        self, row: int, col: int, starting_orientation=PatchOrientation.Z_TOP
    ):
        super().__init__(PatchType.ROUTE, row, col)

    def store(self):
        if not self.locked():
            self.patch_type = PatchType.T


class TFactoryOutputPatch(Patch):
    def __init__(
        self, row: int, col: int, starting_orientation=PatchOrientation.Z_TOP
    ):
        super().__init__(PatchType.CULTIVATOR, row, col,
                         starting_orientation=starting_orientation)

        self.has_T = False
        self.factory = TFactory_Litinski_3x6()

    def T_available(self):
        return self.has_T and not self.locked()

    def route_available(self):
        return False

    def update(self):
        if not self.has_T and not self.locked():
            output = self.factory()
            if output:
                self.has_T = True
                return True
        return False

    def use(self):
        if self.has_T:
            self.has_T = False
        else:
            raise Exception("No T available to use!")

    def release(self, time):
        self.factory._curr_cycle = 0


class TCultPatch(Patch):
    def __init__(
        self, row: int, col: int, starting_orientation=PatchOrientation.Z_TOP
    ):
        super().__init__(PatchType.CULTIVATOR, row, col,
                         starting_orientation=starting_orientation)

        self.has_T = False
        self.cultivator = t_cultivator.TCultivator()

    def T_available(self):
        return self.has_T and not self.locked()

    def route_available(self):
        return not self.has_T and not self.locked()

    def update(self):
        if not self.has_T and not self.locked():
            self.has_T = self.cultivator() > 0
            if self.has_T:
                return True
        return False

    def use(self):
        if self.has_T:
            self.has_T = False
        else:
            raise Exception("No T available to use!")

    def release(self, time):
        self.cultivator.reset()
