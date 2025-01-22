from collections import deque
from typing import List
from t_scheduler.base import gate
from t_scheduler.base.gate import BaseGate, GateType, T_Gate
from t_scheduler.base.patch import Patch, PatchOrientation, PatchType, TCultPatch
from t_scheduler.scheduler import RotationStrategy
from t_scheduler.region import Widget

from t_scheduler.flat_scheduler import *


class NaiveBufferScheduler(FlatScheduler):
    def flat_sparse_search(self, widget, gate):
        curr_patch = self.widget[1, gate.targ * 2]
        bfs_queue = deque([(curr_patch.row, curr_patch.col)])
        parent = {}
        seen = {(curr_patch.row, curr_patch.col)}
        results = []
        while bfs_queue:
            row, col = bfs_queue.popleft()
            if (row, col) in parent:
                pass

            for r, c in [
                (row + 1, col),
                (row, col - 1),
                (row, col + 1),
                (row - 1, col),
            ]:
                if 2 <= r < widget.height and 0 <= c < widget.width:
                    patch = widget[r, c]
                    if patch.T_available():
                        parent[r, c] = (row, col)
                        results.append((r, c))
                        break
                    elif patch.route_available() and (r, c) not in seen:
                        parent[r, c] = (row, col)
                        bfs_queue.append((r, c))
                        seen.add((r, c))
            else:
                continue
            break
        else:
            return None
        path = [patch]
        curr = patch.row, patch.col
        while curr in parent:
            curr = parent[curr]
            path.append(widget[curr])
        path.append(self.widget[0, gate.targ * 2])
        return path


if __name__ == '__main__':
    obj = toffoli_example_input()
    wid = Widget.factory_widget(obj['n_qubits'] * 2, 8)
    z = NaiveBufferScheduler(x, wid, True)

last_output = ''
rep_count = 1
buf = ''
def bprint(c='', end='\n'):
    global buf
    buf += str(c)
    buf += end
def print_board(board):
    global last_output, buf, rep_count
    bprint()
    bprint("-" * len(board[0]))
    for row in board:
        for cell in row:
            if cell.patch_type == PatchType.BELL:
                bprint("$", end="")
            elif cell.locked():
                num = cell.lock.owner.targ
                if num >= 10:
                    num = '#'
                bprint(num, end="")
            elif cell.patch_type == PatchType.REG:
                bprint("R", end="")
            elif cell.patch_type == PatchType.ROUTE:
                bprint(" ", end="")
            elif cell.patch_type == PatchType.RESERVED:
                bprint("X", end="")
            elif cell.patch_type == PatchType.FACTORY_OUTPUT:
                bprint("?", end="")
            elif cell.T_available():
                if cell.orientation == PatchOrientation.Z_TOP:
                    bprint("T", end="")
                else:
                    bprint("t", end="")
            elif cell.patch_type == PatchType.CULTIVATOR:
                bprint("@", end="")
            else:
                bprint(".", end="")
        bprint()
    bprint("-" * len(board[0]), end="")
    if buf == last_output:
        rep_count += 1
        print(f'\rX{rep_count}', end='')
        buf = ''
    else:
        print(buf)
        last_output = buf
        buf = ''
        rep_count = 1
