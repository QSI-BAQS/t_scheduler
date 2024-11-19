from util import *
from itertools import chain

def debug_gates():
    # gate_layers = [[0, 2, 1], [0, 2, 1]]
    gate_layers = [[*chain(*(([x] * 8) for x in [5,0,6,8,7]))], ]
    gate_layers2 = [[Gate(t) for t in layer] for layer in gate_layers]
    print(gate_layers)
    output = schedule_undermine(20, 5, gate_layers2, True)
    print(output)

"""
Perform basic scheduler pass
"""
def schedule_undermine(width, height, gate_layers:list[list["Gate"]], debug: bool=False):
    board = Widget(width, height)

    # global curr_mined_row
    # curr_mined_row = height - 1
    # breakpoint()
    active = []
    deferred = []
    output_layers = []

    for layer in gate_layers + [[]]:
        while deferred:
            output_layer = []
            new_deferred = []
            for gate in deferred:
                success = alloc_gate(board, gate)
                if success:
                    active.append(gate)
                else:
                    new_deferred.append(gate)

            for gate in active:
                output_layer.append(gate.path)
            
            deferred = new_deferred

            if debug:
                print_board(board)
            
            if not active:
                raise Exception("No progress made!")

            for gate in active:
                gate.tick()
                if gate.retirable():
                    gate.retire()

            active = []
            output_layers.append(output_layer)

        output_layer = []
        for gate in layer:
            success = alloc_gate(board, gate)
            if success:
                active.append(gate)
            else:
                deferred.append(gate)


        # print(deferred)

        if debug:
            print_board(board)

        for gate in active:
            output_layer.append(gate.path)

        for gate in active:
            gate.tick()
            if gate.retirable():
                gate.retire()
        active = []
        output_layers.append(output_layer)


    return output_layers


def alloc_gate(widget, gate):
    if gate.gate_type == GateType.T_STATE:
        path = vertical_search(widget, gate.targ)
        if path is None:
            return False
        path[0].use()

        gate.activate(path, path[0])
        return True
    elif gate.gate_type == GateType.NO_RESOURCE:
        reg = widget[0, gate.targ*2]
        if reg.locked():
            return False
        gate.activate([reg])
        return True
    elif gate.gate_type == GateType.ANCILLA:
        reg = widget[0, gate.targ*2]
        anc = widget[1, gate.targ*2]
        if reg.locked() or anc.locked():
            return False
        gate.activate([reg, anc])
        return True

def col_search_order(start_col, width):
    return chain(range(start_col - 1, 0, -1), range(start_col + 1, width - 1))

# def vertical_search(*args):
#     return fix_left_col(vertical_search_main(*args))

def fix_left_col(path):
    if path is None:
        return None
    
    return [(r, max(c,1)) for r,c in path]



def T_search_owning(widget, reg) -> Patch | None:
    for r in range(2, widget.height):
        for c in range(2 * reg, 2 * reg + 2):
            if (patch := widget[r,c]).T_available():
                return patch



def T_path_owning(widget, reg, T_patch):
    if 2 * reg == T_patch.col:
        return [widget[r, T_patch.col] for r in range(T_patch.row, -1,-1)]
    else:
        hor = [widget[1, 2*reg], widget[0, 2*reg]]
        vert =  [widget[r, T_patch.col] for r in range(T_patch.row, 0,-1)]
        return vert + hor


def probe_left_nonowning(widget, reg, prefix):
    start_row = prefix[-1].row
    start_col = prefix[-1].col

    left_path = []

    if start_row > 1:
        for c in range(start_col-1, 0, -1):
            if (patch := widget[start_row,c]).route_available():
                left_path.append(patch)
            elif patch.T_available():
                return [patch] + left_path[::-1] + prefix[::-1]
            else:
                break

    next_left_path = []
    for r in range(start_row - 1, 1, -1):
        for c in range(start_col - 1, 0, -1):
            if (patch := widget[r,c]).route_available():
                next_left_path.append(patch)
            elif patch.T_available() and patch.col >= left_path[-1].col:
                # breakpoint()
                return [patch] + left_path[:start_col - c][::-1] + prefix[:r+2][::-1]
            else:
                break
        left_path = next_left_path

def probe_right_nonowning(widget, reg, prefix):
    start_row = prefix[-1].row
    start_col = prefix[-1].col

    right_path = []

    if start_row > 1:
        for c in range(start_col+1, widget.width - 1):
            if (patch := widget[start_row,c]).route_available():
                right_path.append(patch)
            elif patch.T_available():
                return [patch] + right_path[::-1] + prefix[::-1]
            else:
                break

    next_right_path = []
    for r in range(start_row - 1, 1, -1):
        for c in range(start_col+1, widget.width-1):
            if (patch := widget[r,c]).route_available():
                next_right_path.append(patch)
            elif patch.T_available() and patch.col <= right_path[-1].col:
                return [patch] + right_path[c - start_col :-1:-1] + prefix[r::-1]
            else:
                break
        right_path = next_right_path

# def T_search_nonowning(widget, reg):
#     for r in range(widget.height-1,1,-1):
#         # left col of reg -> left edge
#         for c in range(reg * 2-1,0,-1):
#             if (patch := widget[r,c]).T_available():
#                 return patch
#         for c in range(reg * 2+2,widget.width):
#             if (patch := widget[r,c]).T_available():
#                 return patch

# def T_path_nonowning(widget, reg, T_patch):
#     if T_patch.row == widget.height - 1:
#         # T on left of reg
#         if T_patch.col < 2 * reg:
#             down_path = [widget[r, 2 * reg] for r in range(widget.height - 1, -1, -1)]
#             left_path = [widget[T_patch.row, c] for c in range(T_patch.col, 2 * reg)]
#             return left_path + down_path
#         else:
#             down_path = [widget[r, 2 * reg] for r in range(widget.height - 1, -1, -1)]
#             right_path = [widget[T_patch.row, c] for c in range(T_patch.col, 2 * reg, -1)]
#             return right_path + down_path
#     else:
#         if T_patch.col < 2 * reg:
#             down_path = [widget[r, 2 * reg] for r in range(T_patch.row + 1, -1, -1)]
#             left_path = [widget[T_patch.row + 1, c] for c in range(T_patch.col, 2 * reg)]
#             target = [T_patch]
#             return target + left_path + down_path
#         else:
#             down_path = [widget[r, 2 * reg] for r in range(T_patch.row + 1, -1, -1)]
#             left_path = [widget[T_patch.row + 1, c] for c in range(T_patch.col, 2 * reg, -1)]
#             target = [T_patch]
#             return target + left_path + down_path
        
def probe_down(widget, reg):
    if widget[0, 2*reg].locked() or widget[0, 2*reg + 1].locked():
        return []
    prefix = [widget[0, 2 * reg], widget[1, 2 * reg]]
    probe_col = 2 * reg
    if reg == 0:
        prefix.append(widget[1, 1])
        probe_col = 1
    for i in range(2, widget.height):
        if (patch := widget[i, probe_col]).route_available():
            prefix.append(patch)
        else:
            break
    return prefix

# T --> reg
def validate_T_path(path):
    # print(path)
    if not path[0].T_available():
        return False
    if not all(p.route_available() for p in path[1:-1]):
        return False
    if path[-1].locked():
        return False
    return True

def vertical_search(widget, reg):
    if widget[0,2*reg].locked():
        return None

    if (T := T_search_owning(widget, reg)) and validate_T_path(path := T_path_owning(widget, reg, T)):
        return path
    
    if not (prefix := probe_down(widget, reg)):
        # breakpoint()
        return None

    # breakpoint()

    if path := probe_left_nonowning(widget, reg, prefix):
        return path

    if path := probe_right_nonowning(widget, reg, prefix):
        return path

    return None


# def print_layers(width, height, output_layers):
#     board = create_default_board(width, height)
#     for r in range(height):
#         for c in range(width):


def print_board(board):
    for row in board:
        for cell in row:
            if cell.patch_type == PatchType.BELL:
                print("$", end='')
            elif cell.locked():
                print(cell.lock.owner.targ, end='')
            elif cell.patch_type == PatchType.REG:
                print("R", end='')
            elif cell.patch_type == PatchType.ROUTE:
                print(" ", end='')
            elif cell.T_available():
                print("T", end='')
            else:
                print(".", end='')
        print()
    print('-' * len(board[0]))


debug_gates()