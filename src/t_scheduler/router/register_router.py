from typing import Literal, Tuple
from collections import deque

from ..widget.widget_region import TopEdgePosition

from ..base import Transaction, Response, ResponseStatus, Patch
from ..widget import CombShapedRegisterRegion, SingleRowRegisterRegion
from .abstract_router import AbstractRouter, export_router

@export_router(SingleRowRegisterRegion)
class BaselineRegisterRouter(AbstractRouter):
    region: SingleRowRegisterRegion

    def __init__(self, region) -> None:
        self.region = region

    def request_explicit(self, position, request_type: Literal["local", "ancilla"] = "local"):
        reg_patch = self.region[position]

        if reg_patch.locked():
            return None

        # TODO add logic if 1x1 register cell and ancilla required
        # Below relies on 1x2 reg patches
        if request_type == "ancilla":
            anc = self.region[position[0], position[1] + 1]
            if anc.locked():  # This should never happen for single row regions
                return None
            return Transaction([anc, reg_patch], [])
        else:
            return Transaction([reg_patch], [reg_patch])

    def generic_transaction(self, reg_patch, *args, target_orientation=None, **kwargs):

        if reg_patch.locked():
            return Response()

        return Response(ResponseStatus.CHECK_DOWNSTREAM, Transaction(
            [reg_patch], [reg_patch], connect_col=reg_patch.local_x
        ))

@export_router(CombShapedRegisterRegion)
class CombRegisterRouter(AbstractRouter):
    region: CombShapedRegisterRegion

    def __init__(self, region: CombShapedRegisterRegion) -> None:
        self.region = region

    def request_explicit(
        self,
        position,
        request_type: Literal["local", "ancilla"] = "local"
    ) -> Transaction | None:
        '''
            Request a register transaction to gate_targ of type
            request_type. 
        '''

        reg_patch = self.region[position]

        if reg_patch.locked():
            return None

        if request_type == "ancilla":
            # Check all neighbours for ancilla available
            row, col = reg_patch.local_y, reg_patch.local_x
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
            raise NotImplementedError()

    def bfs(self, curr_patch: Patch, target_orientation):
        '''
        Search for path along routing net to routing bus below
        '''
        bfs_queue = deque([(curr_patch.local_y, curr_patch.local_x)])
        parent = {}
        seen = {(curr_patch.local_y, curr_patch.local_x)}
        while bfs_queue:
            row, col = bfs_queue.popleft()
            if target_orientation is None or target_orientation == TopEdgePosition.TOP:
                if row == self.region.height - 1:
                    break
            elif target_orientation == TopEdgePosition.BOTTOM:
                if row == 0:
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

    def generic_transaction(self, reg_patch, *args, target_orientation=None, **kwargs):

        if reg_patch.locked():
            return Response()

        path = self.bfs(reg_patch, target_orientation=target_orientation)

        if not path:
            return Response()

        return Response(ResponseStatus.CHECK_DOWNSTREAM, Transaction(path, [reg_patch], connect_col=path[0].local_x))
