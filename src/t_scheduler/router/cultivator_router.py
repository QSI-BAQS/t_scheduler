from t_scheduler.router.transaction import Transaction
from t_scheduler.widget.magic_state_buffer import TCultivatorBufferRegion


class TCultivatorBufferRouter:
    '''
        Note: Works only with passthrough bus router
        Assumption because output_col is used to detect which columns of T to assign
    '''
    buffer: TCultivatorBufferRegion

    def __init__(self, buffer) -> None:
        self.buffer = buffer

    def _make_transaction(self, path, connect=None):
        def on_activate_callback(trans: Transaction):
            self.buffer.available_states.remove(
                trans.magic_state_patch)  # type: ignore

        def on_unlock_callback(trans: Transaction):
            self.buffer.release_cells(trans.lock.holds)  # type: ignore

        return Transaction(path, [path[0]],
                           magic_state_patch=path[0],
                           connect_col=connect,
                           on_activate_callback=on_activate_callback,
                           on_unlock_callback=on_unlock_callback)

    def request_transaction(self, output_col, strict_output_col: bool = True) -> Transaction | None:
        '''
            output_col: which column to output to in routing bus above
        '''

        return self.flat_dense_search(output_col, strict_output_col=strict_output_col)

    def flat_dense_search(self, output_col, strict_output_col: bool):
        queue = sorted(self.buffer.available_states,
                       key=lambda p: (abs(p.col - output_col), p.row))

        for i, T_patch in enumerate(queue):
            if strict_output_col:
                vert = [self.buffer[x, output_col]
                        for x in self.range_directed(T_patch.row, 0)]
            else:
                vert = [self.buffer[x, T_patch.col]
                        for x in self.range_directed(T_patch.row, 0)]

            if all(p.route_available() for p in vert):
                if strict_output_col:
                    horizontal = [self.buffer[T_patch.row, i]
                                  for i in self.range_directed(T_patch.col, output_col)]
                    path = horizontal + vert
                else:
                    path = [T_patch] + vert

                if all(p.route_available() for p in path[1:]):
                    transaction = self._make_transaction(
                        path, connect=path[-1].col)

                    return transaction
        return None

    # TODO: Port flat_sparse router

    @staticmethod
    def range_directed(a, b):
        if a <= b:
            return range(a, b + 1)
        else:
            return range(a, b - 1, -1)
