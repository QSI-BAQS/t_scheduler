from collections import deque

from ..base import Transaction, Response, ResponseStatus, Patch
from ..widget import MagicStateFactoryRegion

from .abstract_router import AbstractRouter, export_router

@export_router(MagicStateFactoryRegion.with_litinski_6x3_dense)
class MagicStateFactoryRouter(AbstractRouter):
    """
    Note: Works only with passthrough bus router
    Assumption because output_col is used to detect which columns of T to assign
    """

    region: MagicStateFactoryRegion

    def __init__(self, region) -> None:
        self.region = region.local_view
        for r in range(self.region.height):
            for c in range(self.region.width):
                self.region[r, c].local_y = r
                self.region[r, c].local_x = c
        self.magic_source = True

    def _make_transaction(self, path, connect=None):
        def on_activate_callback(trans: Transaction):
            self.region.available_states.remove(trans.magic_state_patch)  # type: ignore

        def on_unlock_callback(trans: Transaction):
            # self.region.release_cells(trans.lock.holds)  # type: ignore
            if trans.magic_state_patch.t_count > 0:  # type: ignore
                self.region.available_states.add(trans.magic_state_patch) # type: ignore

        return Transaction(
            path,
            [path[0]],
            magic_state_patch=path[0],
            connect_col=connect,
            on_activate_callback=on_activate_callback,
            on_unlock_callback=on_unlock_callback,
        )

    def _request_transaction(
        self, output_col, strict_output_col: bool = False
    ) -> Transaction | None:
        """
        output_col: which column to output to in routing bus above

        strict_output_col: whether we can just output to any column in 
        the routing bus
        """
        output_col = self.clamp(output_col, 0, self.region.width-1)
        queue = sorted(
            self.region.available_states, key=lambda p: (abs(p.local_x - output_col), p.local_y)
        )
        for output in queue:
            if not output.T_available():
                continue
            if strict_output_col:
                path = self.bfs(output, strict_col=output_col)
            else:
                path = self.bfs(output)

            if path:
                return self._make_transaction(path, connect=path[-1].local_x)
        return None

    def bfs(self, curr_patch: Patch, strict_col=None):
        '''
        BFS from a T state along routing net to top row
        '''
        bfs_queue = deque([(curr_patch.local_y, curr_patch.local_x)])
        parent = {}
        seen = {(curr_patch.local_y, curr_patch.local_x)}
        while bfs_queue:
            row, col = bfs_queue.popleft()
            if row == 0:
                if strict_col is None or strict_col == col:
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
        fragment.reverse()
        return fragment


    def generic_transaction(self, source_patch, *args, target_orientation=None, **kwargs):
        local_y, local_x = self.region.tl((source_patch.y - self.region.offset[0], source_patch.x - self.region.offset[1]))
        trans = self._request_transaction(local_x, *args, **kwargs)
        if trans:
            return Response(ResponseStatus.SUCCESS, trans)
        else:
            return Response()