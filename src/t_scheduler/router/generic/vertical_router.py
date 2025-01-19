from typing import List
from ...base import Transaction
from ...widget import WidgetRegion
from ..abstract_router import AbstractRouter

class GenericVerticalRouter(AbstractRouter):
    """
    Assumes buffer as follows:

     (output^)
    ----------
      buffer
    ----------
     (input ^)

    """
    buffer: WidgetRegion

    def __init__(self, buffer) -> None:
        self.buffer = buffer

    def _request_transaction(
        self, output_col, input_col
    ) -> Transaction | None:
        
        search_dir = 1 if input_col < output_col else -1

        col = input_col
        row = self.buffer.height - 1


        if not (patch := self.buffer[row, col]).route_available():
            return None

        path = [patch]

        while row > 0:
            if (patch := self.buffer[row - 1, col]).route_available():
                path.append(patch)
                row -= 1
                continue

            new_col = col + search_dir
            if not (input_col <= new_col <= output_col or output_col <= new_col <= input_col):
                return None
            
            if (patch := self.buffer[row, new_col]).route_available():
                path.append(patch)
                col = new_col
            else:
                return None
            
        return Transaction(
            path, [], connect_col=output_col
        )

    