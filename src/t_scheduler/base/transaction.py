from __future__ import annotations
from abc import ABC
from typing import Callable, List

from .patch import Patch, PatchLock


class BaseTransaction(ABC):
    def lock_move(self, gate) -> None:
        """
        Lock a transaction based on move_patches.
        """
        raise NotImplementedError()

    def lock_measure(self, gate) -> None:
        """
        Lock a transaction based on measure_patches
        """
        raise NotImplementedError()

    def unlock(self) -> None:
        """
        Unlock locked patches
        """
        raise NotImplementedError()

    def release(self, time: int) -> None:
        """
        Call release on magic_state_patch (rotation tracking)
        """
        raise NotImplementedError()

    def activate(self) -> None:
        """
        Activate transaction (i.e. commit) and execute on_activate_callback
        """
        raise NotImplementedError()

    def check_unlocked(self) -> bool:
        """
        Check if we are locked.
        """
        raise NotImplementedError()


class Transaction(BaseTransaction):
    '''
    Holds a set of patches for a gate to operate on.

    Some convenience methods here.
    '''
    move_patches: List[Patch]
    measure_patches: List[Patch]
    magic_state_patch: Patch | None
    lock: None | PatchLock
    connect_col: None | int

    on_unlock_callback: None | Callable[[Transaction]]
    on_activate_callback: None | Callable[[Transaction]]

    def __init__(
        self,
        move_patches,
        measure_patches,
        connect_col=None,
        magic_state_patch=None,
        on_unlock_callback=None,
        on_activate_callback=None,
    ):
        self.move_patches = move_patches
        self.measure_patches = measure_patches
        self.lock = None
        self.connect_col = connect_col
        self.magic_state_patch = magic_state_patch

        self.on_unlock_callback = on_unlock_callback
        self.on_activate_callback = on_activate_callback
        self.on_release_callback = None

        self.layout_override = []

        self.active_cells = []

    def activate(self):
        if self.magic_state_patch:
            self.magic_state_patch.use()

        if self.on_activate_callback:
            self.on_activate_callback(self)
            del self.on_activate_callback

    def release(self, time):
        if self.magic_state_patch:
            self.magic_state_patch.release(time)

        if self.on_release_callback is not None:
            self.on_release_callback(self)
            del self.on_release_callback

    def lock_move(self, gate):
        assert self.lock is None

        self.lock = PatchLock(gate, self.move_patches)  # type: ignore
        self.lock.lock()
        self.active_cells = self.move_patches

    def lock_measure(self, gate):
        assert self.lock is None

        self.lock = PatchLock(gate, self.measure_patches)  # type: ignore
        self.lock.lock()
        self.active_cells = self.measure_patches
        self.layout_override = []

    def unlock(self):
        assert self.lock is not None

        if self.on_unlock_callback:
            self.on_unlock_callback(self)

        self.lock.unlock()
        self.lock = None

    def check_unlocked(self):
        return all(not p.locked() for p in self.measure_patches)

    def route_count(self):
        return len(self.move_patches) - len(self.measure_patches)

class TransactionList(list, BaseTransaction):
    '''
    List of Transactions, with dispatches to children

    This composes.
    '''
    active_cells: List[Patch]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.active_cells = []

        # TODO hack
        self.layout_override = []

    def lock_move(self: List[Transaction], gate):
        self.layout_override = []

        self.active_cells = []  # type: ignore
        for t in self:
            t.lock_move(gate)
            self.active_cells.extend(t.active_cells)  # type: ignore
            self.layout_override.extend(t.layout_override)

    def lock_measure(self: List[Transaction], gate):
        self.layout_override = []

        self.active_cells = []  # type: ignore
        for t in self:
            t.lock_measure(gate)
            self.active_cells.extend(t.active_cells)  # type: ignore
            self.layout_override.extend(t.layout_override)

    def unlock(self: List[Transaction]):
        for t in self:
            t.unlock()

    def release(self: List[Transaction], time):
        for t in self:
            t.release(time)

    def activate(self: List[Transaction]):
        for t in self:
            t.activate()

    def check_unlocked(self):
        return all(t.check_unlocked() for t in self)

    def route_count(self):
        return sum(t.route_count() for t in self)