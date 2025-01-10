from typing import Literal, Tuple
from collections import deque

from t_scheduler.base.response import Response, ResponseStatus
from ..base import Transaction
from ..widget import CombShapedRegisterRegion, SingleRowRegisterRegion
from .abstract_router import AbstractRouter

class BaselineRegisterRouter(AbstractRouter):
    region: SingleRowRegisterRegion

    def __init__(self, region) -> None:
        self.region = region

    def request_transaction(
        self,
        gate_targ,
        request_type: Literal["local", "nonlocal", "ancilla"] = "nonlocal",
        absolute_position: Literal[False] | Tuple[int, int] = False
    ) -> Transaction | None:
        '''
            Request a register transaction to gate_targ of type
            request_type. 
        '''
        # TODO add logic if 1x1 register cell and ancilla required
        if absolute_position == False:
            physical_position = self.region.get_physical_pos(gate_targ)
        else:
            physical_position = absolute_position

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

    def generic_transaction(self, col, *args, **kwargs):
        trans = self.request_transaction(col // 2, **kwargs)
        if trans:
            return Response(ResponseStatus.CHECK_DOWNSTREAM, trans)
        else:
            return Response()


class CombRegisterRouter(AbstractRouter):
    region: CombShapedRegisterRegion

    def __init__(self, region) -> None:
        self.region = region

    def bfs(self, curr_patch):
        '''
        Search for path along routing net to routing bus below
        '''
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
        absolute_position: Literal[False] | Tuple[int, int] = False
    ) -> Transaction | None:
        '''
            Request a register transaction to gate_targ of type
            request_type. 
        '''
        # TODO add logic if 1x1 register cell and ancilla required
        if absolute_position == False:
            physical_position = self.region.get_physical_pos(gate_targ)
        else:
            physical_position = absolute_position

        reg_patch = self.region[physical_position]

        if reg_patch.locked():
            return None

        # Below relies on 1x2 reg patches
        if request_type == "ancilla":
            row, col = reg_patch.row, reg_patch.col
            for r, c in [
                (row + 1, col),
                (row, col - 1),
                (row, col + 1),
                (row - 1, col),
            ]:
                if 0 <= r < self.region.height and 0 <= c < self.region.width:
                    patch = self.region[r, c]
                    if patch.route_available():
                        anc_patch = patch
                        break
            else:
                return None
            if anc_patch.locked():  # This should never happen
                return None
            lock = [anc_patch, reg_patch]
            return Transaction(lock, [])
        elif request_type == "local":
            return Transaction([reg_patch], [reg_patch])
        else:
            path = self.bfs(reg_patch)

            if not path:
                return None

            return Transaction(path, [reg_patch], connect_col=path[0].col)
