from typing import List

from t_scheduler.base.response import Response, ResponseStatus
from ..base import Patch, Transaction
from ..widget import PrefilledMagicStateRegion
from .abstract_router import AbstractRouter

class VerticalFilledBufferRouter(AbstractRouter):
    """
    Note: Works only with passthrough bus router
    Assumption because output_col is used to detect which
        columns of T to assign
    """

    region: PrefilledMagicStateRegion

    def __init__(self, buffer) -> None:
        self.region = buffer

    @staticmethod
    def _make_transaction(path, connect=None):
        return Transaction(
            path, [path[0]], connect_col=connect, magic_state_patch=path[0]
        )

    def request_transaction(self, output_cols: List[int]) -> Transaction | None:
        """
        output_col: which column to output to in routing bus above
        """
        if not output_cols:
            return None
        for output_col in output_cols:
            if (T := self.search_owning(output_col)) and self.validate_T_path(
                path := self.find_path_owning(T)
            ):
                return self._make_transaction(path, connect=output_col)

        output_col = min(output_cols)

        if not (path_prefix := self.probe_down(output_col)):
            return None

        if path := self.probe_left_nonowning(self.region, path_prefix):
            return self._make_transaction(path, connect=output_col)

        if path := self.probe_right_nonowning(self.region, path_prefix):
            return self._make_transaction(path, connect=output_col)

        return None

    def search_owning(self, output_col) -> Patch | None:
        """
        Finds an available T state in the column output_col
        """
        for r in range(self.region.height):
            if (patch := self.region[r, output_col]).T_available():
                return patch

    def find_path_owning(self, T_patch):
        """
        Gets corresponding path for a T state in the column output_col
        """
        return [self.region[r, T_patch.col] for r in range(T_patch.row, -1, -1)]

    def probe_down(self, output_col):
        """
        Search in output_col for a contiguous region of routes

        (consumed magic states -- previously reset to |+>)
        """
        prefix = []
        for i in range(self.region.height):
            if (patch := self.region[i, output_col]).route_available():
                prefix.append(patch)
            else:
                break
        return prefix

    @staticmethod
    def probe_left_nonowning(buffer, prefix):
        """
        Find an available T state in any column to the left of output_col

        Also generate path to the T state:
            First search in row of last cell hit in down probe
                -> can't attack from below, must interface with X boundary
            Search in other rows, bottom to top
                -> attack from bottom (Z boundary) if possible
                    -- (tracked in next_left_path)
                -> otherwise attack from X boundary
        """
        start_row = prefix[-1].row
        start_col = prefix[-1].col

        left_path = []
        # Tracks previous search of contiguous route blocks
        #  -- must be row below due to bottom up search

        if start_row > 0:
            for c in range(start_col - 1, -1, -1):
                if (patch := buffer[start_row, c]).route_available():
                    left_path.append(patch)
                elif patch.T_available():
                    return [patch] + left_path[::-1] + prefix[::-1]
                else:
                    break

        next_left_path = []
        # Tracks current encounters of contiguous route blocks

        for r in range(start_row - 1, -1, -1):
            for c in range(start_col - 1, -1, -1):
                if (patch := buffer[r, c]).route_available():
                    next_left_path.append(patch)
                elif (
                    patch.T_available() and left_path and patch.col >= left_path[-1].col
                ):
                    return (
                        [patch]
                        + left_path[: start_col - c][::-1]
                        + prefix[: r + 2][::-1]
                    )
                elif patch.T_available():
                    return [patch] + next_left_path[::-1] + prefix[: r + 1][::-1]
                else:
                    break
            left_path = next_left_path
            next_left_path = []

    @staticmethod
    def probe_right_nonowning(widget, prefix):
        """
        Same as probe_left, except direction is to the right
        """
        start_row = prefix[-1].row
        start_col = prefix[-1].col

        right_path = []

        if start_row > 1:
            for c in range(start_col + 1, widget.width):
                if (patch := widget[start_row, c]).route_available():
                    right_path.append(patch)
                elif patch.T_available():
                    return [patch] + right_path[::-1] + prefix[::-1]
                else:
                    break

        next_right_path = []
        for r in range(start_row - 1, -1, -1):
            for c in range(start_col + 1, widget.width):
                if (patch := widget[r, c]).route_available():
                    next_right_path.append(patch)
                elif (
                    patch.T_available()
                    and right_path
                    and patch.col <= right_path[-1].col
                ):
                    return (
                        [patch]
                        + right_path[: c - start_col][::-1]
                        + prefix[: r + 2][::-1]
                    )
                elif patch.T_available():
                    return [patch] + next_right_path[::-1] + prefix[: r + 1][::-1]
                else:
                    break
            right_path = next_right_path
            next_right_path = []

    @staticmethod
    def validate_T_path(path):
        """
        Validate that a path is valid
        """
        if not path[0].T_available():
            return False
        if not all(p.route_available() for p in path[1:]):
            return False
        return True


    def generic_transaction(self, reg_col, *args, **kwargs):
        buffer_cols = []
        if reg_col > 0:
            buffer_cols.append(reg_col - 1)
        if (
            reg_col < self.region.width - 2
        ):
            buffer_cols.append(reg_col)
        trans = self.request_transaction(buffer_cols, **kwargs)
        if trans:
            return Response(ResponseStatus.SUCCESS, trans)
        else:
            return Response()