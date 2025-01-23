from __future__ import annotations
from enum import Enum, IntEnum
from typing import List

from ..tracker import *

from ..t_generation import TCultivator
from ..t_generation import TFactory


class PatchType(Enum):
    UNUSED = 0
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
    '''
        Container class for holding references between a gate
        and patches it is currently acting over
    '''
    def __init__(self, owner, holds: List[Patch]):
        self.owner = owner
        self.holds = holds

    def lock(self):
        '''
        Lock all held patches
        '''
        for patch in self.holds:
            assert patch.lock is None

        for patch in self.holds:
            patch.lock = self

        return True

    def unlock(self):
        '''
        Unlock all held patches
        '''
        for patch in self.holds:
            if patch.lock is self:
                patch.lock = None
        self.owner = None


class Patch:
    '''
    Holds state and purpose of each patch on the device

    Important: row, col are local coordinates in a WidgetRegion!
    '''
    patch_type: PatchType
    local_x: int
    local_y: int
    orientation: PatchOrientation
    x: int # Global positions -- initialised by make_explicit
    y: int

    reg_vol_tag: SpaceTimeVolumeTrackingTag | None = None

    def __init__(
        self,
        patch_type: PatchType,
        local_y: int,
        local_x: int,
        starting_orientation=PatchOrientation.Z_TOP,
    ):
        self.patch_type = patch_type
        self.local_y = local_y
        self.local_x = local_x
        self.lock: None | PatchLock = None
        self.orientation = starting_orientation
        self.used = False
        self.release_time = None
        self.rotation = None

    def __repr__(self):
        return f"P({self.local_y}, {self.local_x})"

    def locked(self):
        return self.lock is not None

    def T_available(self):
        '''
        Available to be used as a T state?
        '''
        return self.patch_type == PatchType.T and not self.used and not self.locked()

    def route_available(self):
        '''
        Available to be used for routing?
        '''
        return (
            self.patch_type in [PatchType.ROUTE, PatchType.ROUTE_BUFFER]
            and not self.locked()
        )

    def register_rotation(self, gate):
        '''
        Track last rotation gate applied to us.
        '''
        self.rotation = gate

    def use(self):
        '''
        Use up our magic state
        '''
        if self.patch_type == PatchType.T:
            self.used = True
        elif self.used:
            raise Exception("T already used!")
        else:
            raise Exception("Can't use non-T!")

    def release(self, time):
        '''
        After use, we are now a |+>, free for routing!
        '''
        if self.patch_type != PatchType.T or not (self.used):
            raise Exception("Can't release non-T or unused T!")
        self.used = False
        self.release_time = time
        self.patch_type = PatchType.ROUTE


class BufferPatch(Patch):
    '''
    Mutable patch that can be transformed into a T patch.
    '''
    def __init__(self, row: int, col: int, starting_orientation=PatchOrientation.Z_TOP):
        self.curr_t_tag = None
        super().__init__(PatchType.ROUTE_BUFFER, row, col, starting_orientation)

    def store(self):
        '''
        Store a T in ourselves.
        '''
        if not self.locked():
            self.patch_type = PatchType.T
    
    def release(self, time):
        '''
        After use, we are now a |+>, free for routing!

        Overrides parent to set patch_type to ROUTE_BUFFER
        '''
        super().release(time)
        self.patch_type = PatchType.ROUTE_BUFFER


class TFactoryOutputPatch(Patch):
    '''
    Note: we need to take care of factory reset in the router.

    Factory updates are taken care of in the component.
    '''
    def __init__(
        self,
        row: int,
        col: int,
        factory: TFactory,
        starting_orientation=PatchOrientation.Z_TOP,
    ):
        '''
        factory is our backing factory
        '''
        super().__init__(
            PatchType.FACTORY_OUTPUT, row, col, starting_orientation=starting_orientation
        )

        self.t_count = 0
        self.factory = factory
        self.curr_t_tag = None

    def T_available(self):
        return (self.t_count > 0) and not self.locked()

    def route_available(self):
        '''
        We are never available for routing
        '''
        return False

    def use(self):
        '''
            Consume a T. We may have more than one.

            (Models an internal connection into the factory buffers)
        '''
        if self.t_count > 0:
            self.t_count -= 1
        else:
            raise Exception("No T available to use!")
    
    def release(self, time):
        '''
            No need to release for Factories!
        '''
        pass

class TCultPatch(Patch):
    '''
    Cultivator patch
    '''
    def __init__(self, row: int, col: int, starting_orientation=PatchOrientation.Z_TOP):
        super().__init__(
            PatchType.CULTIVATOR, row, col, starting_orientation=starting_orientation
        )

        self.has_T = False
        # TODO take this as an argument?
        self.cultivator = TCultivator()
        self.vol_tracker = None
        self.curr_t_tag = None

    def T_available(self):
        return self.has_T and not self.locked()

    def route_available(self):
        '''
        We can use dirty cultivators as a route, however we need to 
        add a reset time. This is taken care of in the router.
        '''
        return not self.has_T and not self.locked()

    def update(self):
        '''
        Ask the cultivator if a T was produced.
        '''
        if not self.has_T and not self.locked():
            self.has_T = self.cultivator() > 0
            if self.has_T:
                self.curr_t_tag = SpaceTimeVolumeTrackingContext(self.vol_tracker)
                self.curr_t_tag.factory_tag = TFactorySpaceTimeVolumeTrackingTag(self.vol_tracker, self.cultivator)
                self.curr_t_tag.source_tag = TSourceTrackingTag(self.vol_tracker, type(self).__qualname__)
                return True
        return False

    def use(self):
        if self.has_T:
            self.has_T = False
        else:
            raise Exception("No T available to use!")

    def release(self, time):
        '''
        When we're done, reset possibly incorrect progress.
        '''
        self.cultivator.reset()
