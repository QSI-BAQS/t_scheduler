from ..base import Transaction
from ..widget import TCultivatorBufferRegion
from .abstract_router import AbstractRouter

def _make_transaction(buffer: TCultivatorBufferRegion, path, connect=None):
    '''
    Helper to make a transaction with appropriate callbacks
    '''
    def on_activate_callback(trans: Transaction):
        buffer.available_states.remove(trans.magic_state_patch)  # type: ignore

    def on_unlock_callback(trans: Transaction):
        buffer.release_cells(trans.lock.holds)  # type: ignore

    return Transaction(
        move_patches=path,
        measure_patches=[path[0]],
        magic_state_patch=path[0],
        connect_col=connect,
        on_activate_callback=on_activate_callback,
        on_unlock_callback=on_unlock_callback,
    )

class DenseTCultivatorBufferRouter(AbstractRouter):
    """
    Note: Works only with passthrough bus router
    Assumption because output_col is used to detect which columns of T to assign
    """

    region: TCultivatorBufferRegion

    def __init__(self, buffer) -> None:
        self.region = buffer

    def request_transaction(
        self, output_col, strict_output_col: bool = True
    ) -> Transaction | None:
        """
        output_col: which column to output to in routing bus above

        strict_output_col: whether we can just output to any column in 
        the routing bus
        """
        queue = sorted(
            self.region.available_states, key=lambda p: (
                abs(p.col - output_col), p.row)
        )

        for i, T_patch in enumerate(queue):
            if strict_output_col:
                vert = [
                    self.region[x, output_col]
                    for x in self.range_directed(T_patch.row, 0)
                ]
            else:
                vert = [
                    self.region[x, T_patch.col]
                    for x in self.range_directed(T_patch.row, 0)
                ]

            if all(p.route_available() for p in vert):
                if strict_output_col:
                    horizontal = [
                        self.region[T_patch.row, i]
                        for i in self.range_directed(T_patch.col, output_col)
                    ]
                    path = horizontal + vert
                else:
                    path = [T_patch] + vert

                if all(p.route_available() for p in path[1:]):
                    transaction = _make_transaction(
                        self.region, path, connect=path[-1].col)

                    return transaction
        return None

# TODO: Port flat_sparse router (in separate class)
