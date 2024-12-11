from collections import deque
from typing import List
from t_scheduler import gate
from t_scheduler.gate import BaseGate, GateType, T_Gate
from t_scheduler.patch import Patch, PatchOrientation, PatchType, TCultPatch
from t_scheduler.scheduler import RotationStrategy
from t_scheduler.widget import Widget

from t_scheduler.flat_scheduler import obj

wid = Widget.factory_widget(obj['n_qubits'] * 2, 8)




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