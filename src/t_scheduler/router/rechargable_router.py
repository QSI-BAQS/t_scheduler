from t_scheduler.router.transaction import Transaction
from t_scheduler.widget.magic_state_buffer import MagicStateBufferRegion


class RechargableBufferRouter:
    '''
        Note: Works only with passthrough bus router
        Assumption because output_col is used to detect which columns of T to assign
    '''
    buffer: MagicStateBufferRegion

    def __init__(self, buffer) -> None:
        self.buffer = buffer

    def request_transaction(self, output_col, strict_output_col: bool = True) -> Transaction | None:
        '''
            output_col: which column to output to in routing bus above
        '''
        queue = sorted(range(self.buffer.width),
                       key=lambda p: (abs(p - output_col)))
        buffer_states = self.buffer.get_buffer_states()

        for col in queue:
            if not (T_patch := buffer_states[col]):
                continue

            vert = [self.buffer[x, T_patch.col] for x in range(T_patch.row)]

            path = [T_patch] + vert

            return Transaction(path, [path[0]],
                           magic_state_patch=path[0],
                           connect_col=path[-1].col)
        return None
    
    def request_passthrough(self, output_col) -> Transaction | None:
        buffer_slots = self.buffer.get_buffer_slots()
        cols = [cell.col for cell in buffer_slots if cell and cell.row == 0]
        
        best_col = min((abs(c - output_col), c) for c in cols)[1]

        path = [self.buffer[row, best_col] for row in range(self.buffer.height)][::-1]
        return Transaction(path, [], connect_col=path[-1].col)

    def upkeep_transaction(self, buffer_slot):
        path = [self.buffer[x, buffer_slot.col] for x in range(buffer_slot.row, self.buffer.height)][::-1]
        return Transaction(path, [path[0]], connect_col=path[-1].col)
    
    def all_local_upkeep_transactions(self):

        output_transactions = []
        for row in range(1, self.buffer.height):
            for col in range(0, self.buffer.width):
                if (T:=self.buffer[row,col]).T_available() and (
                    above:=self.buffer[row-1, col]
                ).route_available():
                    output_transactions.append(
                        Transaction([T, above], [above], magic_state_patch=T)
                    )
        return output_transactions