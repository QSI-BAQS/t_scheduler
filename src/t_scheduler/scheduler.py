from util import *
from itertools import chain

def debug_gates():
    # gate_layers = [[0, 2, 1], [0, 2, 1]]
    gate_layers = [[*chain(*(([x] * 8) for x in [5,0,6,8,7]))], ]
    gate_layers2 = [[Gate(t) for t in layer] for layer in gate_layers]
    print(gate_layers)
    schedule_undermine(20, 5, gate_layers2, True)

"""
Perform basic scheduler pass
"""
def schedule_undermine(width, height, gate_layers:list[list["Gate"]], debug: bool=False):
    board = create_default_board(width, height)

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
                path = vertical_search(width, height, board, gate.targ*2)
                if path is None:
                    new_deferred.append(gate)
                    continue

                active.append(gate)
                gate.lock = PatchLock(gate, [board[i][j] for i,j in path], 1)
                gate.lock.lock()
                output_layer.append(path)
            
            deferred = new_deferred
            if debug:
                print_board(board)
            
            for gate in active:
                gate.lock.unlock()
            active = []
            output_layers.append(output_layer)

        output_layer = []
        for gate in layer:
            path = vertical_search(width, height, board, gate.targ*2)
            if path is None:
                deferred.append(gate)
                continue
            
            print(gate.targ, path)
            active.append(gate)
            gate.lock = PatchLock(gate, [board[i][j] for i,j in path], 1)
            gate.lock.lock()
            output_layer.append(path)

        # print(deferred)

        if debug:
            print_board(board)
        
        for gate in active:
            gate.lock.unlock()
        active = []
        output_layers.append(output_layer)


    return output_layers
        

def col_search_order(start_col, width):
    return chain(range(start_col - 1, 0, -1), range(start_col + 1, width - 1))

def vertical_search(*args):
    return fix_left_col(vertical_search_main(*args))

def fix_left_col(path):
    if path is None:
        return None
    
    return [(r, max(c,1)) for r,c in path]



def vertical_search_main(width, height, board: list[list["Patch"]], start_col):
    if board[0][start_col].locked() or board[0][start_col + 1].locked():
        return None
    # down_search
    for row in range(1, height):
        if board[row][start_col].locked():
            # Blocked
            break
        elif board[row][start_col].T_available():
            # Use T in column
            board[row][start_col].use()
            return [(r, start_col) for r in range(row, -1, -1)]
        elif board[row][start_col + 1].T_available():
            board[row][start_col + 1].use()
            return [(r, start_col + 1) for r in range(row, 0, -1)] + \
                [(1, start_col + 1), (1, start_col + 0), (0, start_col)]


    # mine sideways (left) 
    for col in range(start_col - 1, 0, -1):
        if board[height - 1][col].T_available():
            down_path = [(r, start_col) for r in range(height - 1, -1, -1)]
            left_path = [(row, c) for c in range(col, start_col)]
            board[height - 1][col].use()
            return left_path + down_path
        elif board[height - 1][col].locked():
            break

    # mine sideways (right)
    for col in range(start_col + 1, width - 1):
        if board[height - 1][col].T_available():
            down_path = [(r, start_col) for r in range(height - 1, -1, -1)]
            right_path = [(row, c) for c in range(col, start_col, -1)]
            board[height - 1][col].use()
            return right_path + down_path
        elif board[height - 1][col].locked():
            break

    # mine sideways and up 1 (left) then (right)
    for row in range(height - 2, 1, -1):
        for col in range(start_col - 1, 0, -1):
            if board[row][col].T_available():
                # Try route
                down_path = [(r, start_col) for r in range(row + 1, -1, -1)]
                left_path = [(row + 1, c) for c in range(col, start_col)]
                target = [(row, col)]
                if any(board[r][c].locked() for r, c in chain(target, left_path, down_path)):
                    # Path blocked
                    break
                board[row][col].use()
                return target + left_path + down_path
 
        for col in range(start_col + 1, width - 1):
            if board[row][col].T_available():
                # Try route
                down_path = [(r, start_col) for r in range(row + 1, -1, -1)]
                left_path = [(row + 1, c) for c in range(col, start_col, -1)]
                target = [(row, col)]
                if any(board[r][c].locked() for r,c in chain(target, left_path, down_path)):
                    # Path blocked
                    break
                board[row][col].use()
                return target + left_path + down_path
    
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