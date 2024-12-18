from collections import deque
from t_scheduler.router.transaction import Transaction
from t_scheduler.widget.factory_region import MagicStateFactoryRegion


class MagicStateFactoryRouter:
    '''
        Note: Works only with passthrough bus router
        Assumption because output_col is used to detect which columns of T to assign
    '''
    region: MagicStateFactoryRegion

    def __init__(self, region) -> None:
        self.region = region

    def _make_transaction(self, path, connect=None):
        def on_activate_callback(trans: Transaction):
            self.region.available_states.remove(
                trans.magic_state_patch)  # type: ignore

        def on_unlock_callback(trans: Transaction):
            # self.region.release_cells(trans.lock.holds)  # type: ignore
            if trans.magic_state_patch.t_count > 0: # type: ignore
                self.region.available_states.add(trans.magic_state_patch)

        return Transaction(path, [path[0]],
                           magic_state_patch=path[0],
                           connect_col=connect,
                           on_activate_callback=on_activate_callback,
                           on_unlock_callback=on_unlock_callback)

    def request_transaction(self, output_col, strict_output_col: bool = False) -> Transaction | None:
        '''
            output_col: which column to output to in routing bus above
        '''
        queue = sorted(self.region.available_states,
                       key=lambda p: (abs(p.col - output_col), p.row))
        for output in queue:
            if not output.T_available():
                continue
            if strict_output_col:
                path = self.bfs(output, strict_col=output_col)
            else:
                path = self.bfs(output)
            
            if path:
                return self._make_transaction(path, connect=path[-1].col)
        return None
    
    def bfs(self, curr_patch, strict_col=None):
        bfs_queue = deque([(curr_patch.row, curr_patch.col)])
        parent = {}
        seen = {(curr_patch.row, curr_patch.col)}
        results = []
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
                    if patch.route_available() and (r,c) not in seen:
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
