from util import PatchType, PatchOrientation

class BoardPatch:
    def __init__(self, patch_type: PatchType, above=None, left=None):
        self.patch_type = patch_type
        self.above: BoardPatch | None
        self.below: BoardPatch | None
        self.left:  BoardPatch | None
        self.right: BoardPatch | None
        self.row: int
        self.col: int
        self.orientation = PatchOrientation.Z_TOP

        if above:
            self.above = above
            above.below = self
            self.row = above.row + 1
            self.col = above.col
        elif left:
            self.row = left.row
            self.col = left.col + 1
        else:
            self.row = 0
            self.col = 0

        if left:
            self.left = left
            left.right = self


def widget_factory(width, height):
    reg_row = [BoardPatch(PatchType.REG)]