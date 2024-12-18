from typing import Literal
from collections import deque
from ..base import Transaction
from ..widget.registers import CombShapedRegisterRegion, SingleRowRegisterRegion


class BaselineRegisterRouter:
    region: SingleRowRegisterRegion

    def __init__(self, region) -> None:
        self.region = region

    def request_transaction(
        self,
        gate_targ,
        request_type: Literal["local", "nonlocal", "ancilla"] = "nonlocal",
    ) -> Transaction | None:
        # TODO add logic if 1x1 register cell and ancilla required

        physical_position = self.region.get_physical_pos(gate_targ)

        reg_patch = self.region[0, physical_position[1]]

        if reg_patch.locked():
            return None

        # Below relies on 1x2 reg patches
        if request_type == "ancilla":
            anc = self.region[0, physical_position[1] + 1]
            if anc.locked():  # This should never happen
                return None
            lock = [anc, reg_patch]
            return Transaction(lock, [])
        else:
            return Transaction(
                [reg_patch], [reg_patch], connect_col=physical_position[1]
            )


class CombRegisterRouter:
    region: CombShapedRegisterRegion

    def __init__(self, region) -> None:
        self.region = region

    def bfs(self, curr_patch, strict_col=None):
        bfs_queue = deque([(curr_patch.row, curr_patch.col)])
        parent = {}
        seen = {(curr_patch.row, curr_patch.col)}
        while bfs_queue:
            row, col = bfs_queue.popleft()
            if row == self.region.height - 1:
                break

            for r, c in [
                (row + 1, col),
                (row, col - 1),
                (row, col + 1),
                (row - 1, col),
            ]:
                if 0 <= r < self.region.height and 0 <= c < self.region.width:
                    patch = self.region[r, c]
                    if patch.route_available() and (r, c) not in seen:
                        parent[r, c] = (row, col)
                        bfs_queue.append((r, c))
                        seen.add((r, c))
        else:
            return None
        fragment = [self.region[row, col]]
        while (row, col) in parent:
            row, col = parent[row, col]
            fragment.append(self.region[row, col])
        # fragment.reverse()
        return fragment

    def request_transaction(
        self,
        gate_targ,
        request_type: Literal["local", "nonlocal", "ancilla"] = "nonlocal",
    ) -> Transaction | None:
        # TODO add logic if 1x1 register cell and ancilla required

        physical_position = self.region.get_physical_pos(gate_targ)

        reg_patch = self.region[physical_position]

        if reg_patch.locked():
            return None

        # Below relies on 1x2 reg patches
        if request_type == "ancilla":
            raise NotImplementedError()
            anc = self.region[0, physical_position + 1]
            if anc.locked():  # This should never happen
                return None
            lock = [anc, reg_patch]
            return Transaction(lock, [])
        elif request_type == "local":
            return Transaction([reg_patch], [reg_patch])
        else:
            path = self.bfs(reg_patch)

            if not path:
                return None

            return Transaction(path, [reg_patch], connect_col=path[0].col)
