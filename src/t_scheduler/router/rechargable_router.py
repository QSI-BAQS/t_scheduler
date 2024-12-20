from typing import List
from ..base import Transaction
from ..widget import MagicStateBufferRegion


class RechargableBufferRouter:
    """
    Note: Works only with passthrough bus router
    Assumption because output_col is used to detect which columns of T to assign
    """

    region: MagicStateBufferRegion

    def __init__(self, buffer) -> None:
        self.region = buffer

    def request_transaction(
        self, output_col, strict_output_col: bool = True
    ) -> Transaction | None:
        """
        output_col: which column to output to in routing bus above
        """
        queue = sorted(range(self.region.width), key=lambda p: (abs(p - output_col)))
        buffer_states = self.region.get_buffer_states()

        for col in queue:
            if not (T_patch := buffer_states[col]):
                continue

            vert = [self.region[x, T_patch.col] for x in range(T_patch.row)][::-1]

            path = [T_patch] + vert

            return Transaction(
                path, [path[0]], magic_state_patch=path[0], connect_col=path[-1].col
            )
        return None

    def request_passthrough(self, output_col) -> Transaction | None:
        '''
        Request a passthrough column in the buffer for factories below
        '''
        buffer_slots = self.region.get_buffer_slots()
        cols = [cell.col for cell in buffer_slots if cell and cell.row == 0]
        
        if not cols: return None
        
        best_col = min((abs(c - output_col), c) for c in cols)[1]

        path = [self.region[row, best_col] for row in range(self.region.height)][::-1]
        return Transaction(path, [], connect_col=path[-1].col)

    def upkeep_transaction(self, buffer_slot) -> Transaction:
        '''
        Generate a transaction for moving a T_state from routing bus below
        to buffer_slot.
        '''
        path = [
            self.region[x, buffer_slot.col]
            for x in range(buffer_slot.row, self.region.height)
        ][::-1]
        return Transaction(path, [buffer_slot], connect_col=buffer_slot.col)

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
