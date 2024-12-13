from __future__ import annotations
from re import S
from typing import Callable, List
from t_scheduler.patch import Patch, PatchLock


class Transaction:
    move_patches: List[Patch]
    measure_patches: List[Patch]
    magic_state_patch: Patch | None
    lock: None | PatchLock
    connect_col: None | int

    on_unlock_callback: None | Callable[[Transaction]]
    on_activate_callback: None | Callable[[Transaction]]

    def __init__(self, move_patches, measure_patches, connect_col=None, magic_state_patch=None, on_unlock_callback=None, on_activate_callback=None):
        self.move_patches = move_patches
        self.measure_patches = measure_patches
        self.lock = None
        self.connect_col = connect_col
        self.magic_state_patch = magic_state_patch

        self.on_unlock_callback = on_unlock_callback
        self.on_activate_callback = on_activate_callback

    def activate(self):
        if self.magic_state_patch:
            self.magic_state_patch.use()
        
        if self.on_activate_callback:
            self.on_activate_callback(self)
            del self.on_activate_callback

    def release(self, time):
        if self.magic_state_patch:
            self.magic_state_patch.release(time)

    def lock_move(self, gate):
        assert self.lock is None

        self.lock = PatchLock(gate, self.move_patches, None)  # type: ignore
        self.lock.lock()

    def lock_measure(self, gate):
        assert self.lock is None

        self.lock = PatchLock(gate, self.measure_patches, None)  # type: ignore
        self.lock.lock()

    def unlock(self):
        assert self.lock is not None

        if self.on_unlock_callback:
            self.on_unlock_callback(self)

        self.lock.unlock()
        self.lock = None

    def check_unlocked(self):
        return all(not p.locked() for p in self.measure_patches)


class TransactionList(list):
    def lock_move(self: List[Transaction], gate):
        for t in self:
            t.lock_move(gate)

    def lock_measure(self: List[Transaction], gate):
        for t in self:
            t.lock_measure(gate)

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
