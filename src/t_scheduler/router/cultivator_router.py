from ..base import Transaction, Response, ResponseStatus
from ..region import TCultivatorBufferRegion
from .abstract_router import AbstractRouter, export_router

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

@export_router(TCultivatorBufferRegion.with_dense_layout)
class DenseTCultivatorBufferRouter(AbstractRouter):
    """
    Note: Works only with passthrough bus router
    Assumption because output_col is used to detect which columns of T to assign
    """

    region: TCultivatorBufferRegion

    def __init__(self, buffer) -> None:
        self.region = buffer.local_view
        for r in range(self.region.height):
            for c in range(self.region.width):
                self.region[r, c].local_y = r
                self.region[r, c].local_x = c
        self.magic_source = True

    def _request_transaction(
        self, output_col, strict_output_col: bool = True
    ) -> Transaction | None:
        """
        output_col: which column to output to in routing bus above

        strict_output_col: if false, we can just output to any column in 
        the routing bus
        """
        output_col = self.clamp(output_col, 0, self.region.width-1)
        queue = sorted(
            self.region.available_states, key=lambda p: 
                (abs(p.local_x - output_col), p.local_y)
        )

        for i, T_patch in enumerate(queue):
            T_patch_y, T_patch_x = (T_patch.local_y, T_patch.local_x)
            if T_patch_x == output_col:
                vert = [
                    self.region[x, output_col]
                    for x in self.range_directed(T_patch_y, 0)
                ][1:]
            elif strict_output_col:
                vert = [
                    self.region[x, output_col]
                    for x in self.range_directed(T_patch_y, 0)
                ]
            else:
                vert = [
                    self.region[x, T_patch.local_x]
                    for x in self.range_directed(T_patch_y, 0)
                ]

            if all(p.route_available() for p in vert):
                if T_patch_x == output_col:
                    path = [T_patch] + vert
                elif strict_output_col:
                    horizontal = [
                        self.region[T_patch_y, i]
                        for i in self.range_directed(T_patch_x, output_col)
                    ]
                    path = horizontal + vert
                else:
                    path = [T_patch] + vert

                if all(p.route_available() for p in path[1:]):
                    transaction = _make_transaction(
                        self.region, path, connect=path[-1].local_x)

                    return transaction
        return None


    def generic_transaction(self, source_patch, *args, target_orientation=None, **kwargs):
        local_y, local_x = self.region.tl((source_patch.y - self.region.offset[0], source_patch.x - self.region.offset[1]))
        trans = self._request_transaction(local_x, *args, **kwargs)
        if trans:
            return Response(ResponseStatus.SUCCESS, trans)
        else:
            return Response()
# TODO: Port flat_sparse router (in separate class)
