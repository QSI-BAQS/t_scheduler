from t_scheduler.scheduler import *

def T_search_owning(widget, reg) -> Patch | None:
    for r in range(2, widget.height):
        for c in range(2 * reg, 2 * reg + 2):
            if (patch := widget[r, c]).T_available():
                return patch


def T_path_owning(widget, reg, T_patch):
    if 2 * reg == T_patch.col:
        return [widget[r, T_patch.col] for r in range(T_patch.row, -1, -1)]
    else:
        hor = [widget[1, 2 * reg], widget[0, 2 * reg]]
        vert = [widget[r, T_patch.col] for r in range(T_patch.row, 0, -1)]
        return vert + hor


def probe_left_nonowning(widget, reg, prefix):
    start_row = prefix[-1].row
    start_col = prefix[-1].col

    left_path = []

    if start_row > 1:
        for c in range(start_col, 0, -1):
            if (patch := widget[start_row, c]).route_available():
                left_path.append(patch)
            elif patch.T_available():
                return [patch] + left_path[::-1] + prefix[::-1]
            else:
                break

    next_left_path = []
    for r in range(start_row - 1, 1, -1):
        for c in range(start_col - 1, 0, -1):
            if (patch := widget[r, c]).route_available():
                next_left_path.append(patch)
            elif patch.T_available() and left_path and patch.col >= left_path[-1].col:
                return (
                    [patch]
                    + left_path[: start_col - c + 1][::-1]
                    + prefix[: r + 1][::-1]
                )
            elif patch.T_available():
                return [patch] + next_left_path[::-1] + prefix[: r + 1][::-1]
            else:
                break
        left_path = next_left_path
        next_left_path = []


def probe_right_nonowning(widget, reg, prefix):
    start_row = prefix[-1].row
    start_col = prefix[-1].col

    right_path = []

    if start_row > 1:
        for c in range(start_col, widget.width - 1):
            if (patch := widget[start_row, c]).route_available():
                right_path.append(patch)
            elif patch.T_available():
                return [patch] + right_path[::-1] + prefix[::-1]
            else:
                break

    next_right_path = []
    for r in range(start_row - 1, 1, -1):
        for c in range(start_col + 1, widget.width - 1):
            if (patch := widget[r, c]).route_available():
                next_right_path.append(patch)
            elif patch.T_available() and right_path and patch.col <= right_path[-1].col:
                return (
                    [patch]
                    + right_path[: c - start_col + 1][::-1]
                    + prefix[: r + 1][::-1]
                )
            elif patch.T_available():
                return [patch] + next_right_path[::-1] + prefix[: r + 1][::-1]
            else:
                break
        right_path = next_right_path
        next_right_path = []


def probe_down(widget, reg):
    if widget[0, 2 * reg].locked() or widget[0, 2 * reg + 1].locked():
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
    if not path[0].T_available():
        return False
    if not all(p.route_available() for p in path[1:-1]):
        return False
    if path[-1].locked():
        return False
    return True


def vertical_search(widget, reg):
    if widget[0, 2 * reg].locked():
        return None

    if (T := T_search_owning(widget, reg)) and validate_T_path(
        path := T_path_owning(widget, reg, T)
    ):
        return path

    if not (prefix := probe_down(widget, reg)):
        return None

    if path := probe_left_nonowning(widget, reg, prefix):
        return path

    if path := probe_right_nonowning(widget, reg, prefix):
        return path

    return None

class VerticalScheduler(Scheduler):
    '''
        TODO: Docstring this class
    '''

    def __init__(
            self,
            layers,
            widget,
            rotation_strategy=RotationStrategy.BACKPROP_INIT,
            **kwargs):
        '''
        TODO: Comment on the rotation strategy
        '''
        super().__init__(layers, widget, vertical_search, rotation_strategy, **kwargs)
