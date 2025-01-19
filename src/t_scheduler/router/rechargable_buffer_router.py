from typing import List

from .abstract_router import AbstractRouter
from ..base import Transaction, Response, ResponseStatus, Patch
from ..widget import MagicStateBufferRegion


class RechargableBufferRouter(AbstractRouter):
    """
    Note: Works only with passthrough bus router
    Assumption because output_col is used to detect which columns of T to assign
    """

    region: MagicStateBufferRegion

    def __init__(self, buffer) -> None:
        self.region = buffer.local_view
        for r in range(self.region.height):
            for c in range(self.region.width):
                self.region[r, c].local_y = r
                self.region[r, c].local_x = c
        self.upkeep_accept = True

    def get_buffer_slots(self) -> List[None | Patch]:
        buffer_lanes = []
        for col in range(self.region.width):
            topmost = None
            for row in range(self.region.height - 1, -1, -1):
                if (cell := self.region[row, col]).route_available():
                    topmost = cell
                else:
                    break
            buffer_lanes.append(topmost)
        return buffer_lanes

    def get_buffer_states(self) -> List[None | Patch]:
        buffer_lanes = []
        for col in range(self.region.width):
            topmost = None
            for row in range(self.region.height):
                if (cell := self.region[row, col]).T_available():
                    topmost = cell
                    break
                elif not cell.route_available():
                    break
            buffer_lanes.append(topmost)
        return buffer_lanes



    def _request_transaction(
        self, output_col, strict_output_col: bool = False
    ) -> Transaction | None:
        """
        output_col: which column to output to in routing bus above
        """
        queue = sorted(range(self.region.width), key=lambda p: (abs(p - output_col)))
        buffer_states = self.get_buffer_states()

        for col in queue:
            if not (T_patch := buffer_states[col]):
                continue

            vert = [self.region[x, T_patch.local_x] for x in range(T_patch.local_y)][::-1]

            path = [T_patch] + vert

            return Transaction(
                path, [path[0]], magic_state_patch=path[0], connect_col=path[-1].local_x
            )
        return None

    def request_passthrough(self, output_col) -> Transaction | None:
        '''
        Request a passthrough column in the buffer for factories below
        '''
        buffer_slots = self.get_buffer_slots()
        cols = [cell.local_x for cell in buffer_slots if cell and cell.local_y == 0]
        
        if not cols: return None
        
        best_col = min((abs(c - output_col), c) for c in cols)[1]

        path = [self.region[row, best_col] for row in range(self.region.height)][::-1]
        return Transaction(path, [], connect_col=path[-1].local_x)

    def generic_transaction(self, source_patch, *args, target_orientation=None, **kwargs):
        local_y, local_x = self.region.tl((source_patch.y - self.region.offset[0], source_patch.x - self.region.offset[1]))

        trans = self._request_transaction(local_x, **kwargs)
        if trans:
            return Response(ResponseStatus.SUCCESS, trans)
        trans = self.request_passthrough(local_x, **kwargs)
        if trans:
            return Response(ResponseStatus.CHECK_DOWNSTREAM, trans)
        else:
            return Response()

    def upkeep_transaction(self, buffer_slot: Patch) -> Transaction:
        '''
        Generate a transaction for moving a T_state from routing bus below
        to buffer_slot.
        '''
        path = [
            self.region[x, buffer_slot.local_x]
            for x in range(buffer_slot.local_y, self.region.height)
        ][::-1]
        return Transaction(path, [buffer_slot], connect_col=buffer_slot.local_x)

    def all_local_upkeep_transactions(self) -> List[Transaction]:
        '''
        Generate all local moves to shuffle T_state along column queues
        '''
        output_transactions = []
        for row in range(1, self.region.height):
            for col in range(0, self.region.width):
                if (T := self.region[row, col]).T_available() and (
                    above := self.region[row - 1, col]
                ).route_available():
                    output_transactions.append(
                        Transaction([T, above], [above], magic_state_patch=T)
                    )
        return output_transactions
