from __future__ import annotations
from typing import List
from t_scheduler.patch import Patch, PatchOrientation, PatchType


class TreeNode:
    def __init__(self, parent: TreeNode | None, path: List[Patch], reg: int | None = None):
        self.parent = parent
        self.children = []
        self.path = path
        self.reparsed = False

        if parent is not None:
            self.reg = parent.reg
            self.path_fragment = path[len(parent.path):]
        else:
            assert reg is not None
            self.reg = reg
            self.path_fragment = path


class Widget:
    def __init__(self, width: int, height: int, board: List[List[Patch]], depth_offset: float = 2 / 3):
        if depth_offset < 0 or depth_offset > 1:
            raise Exception("Depth offset out of bounds")

        self.width: int = width
        self.height: int = height

        self.board = board
        self.reg_t_frontier = [TreeNode(None, [], q)
                               for q in range(width // 2)]

        self.dig_depth = int(self.height * depth_offset)

    @classmethod
    def default_widget(cls, width, height) -> Widget:
        reg_row = [Patch(PatchType.REG, 0, c) for c in range(width)]
        route_row = [Patch(PatchType.ROUTE, 1, c) for c in range(width)]
        board = [reg_row, route_row]
        for r in range(2, height):
            row = [
                Patch(PatchType.BELL, r, 0),
                *(Patch(PatchType.T, r, c) for c in range(1, width - 1)),
                Patch(PatchType.BELL, r, width - 1),
            ]
            board.append(row)
        return Widget(width, height, board)

    @classmethod
    def chessboard_widget(cls, width, height) -> Widget:
        reg_row = [Patch(PatchType.REG, 0, c) for c in range(width)]
        route_row = [Patch(PatchType.ROUTE, 1, c) for c in range(width)]
        top_T = [
            Patch(PatchType.BELL, 2, 0),
            *(
                Patch(
                    PatchType.T,
                    2,
                    c,
                )
                for c in range(1, width - 1)
            ),
            Patch(PatchType.BELL, 2, width - 1),
        ]
        board = [reg_row, route_row, top_T]
        for r in range(3, height):
            row = [
                Patch(PatchType.BELL, r, 0),
                *(
                    Patch(
                        PatchType.T,
                        r,
                        c,
                        PatchOrientation((r ^ c) & 1) ^ (c < width // 2),
                    )
                    for c in range(1, width - 1)
                ),
                Patch(PatchType.BELL, r, width - 1),
            ]
            board.append(row)
        return Widget(width, height, board)

    def __getitem__(self, index) -> Patch | List[Patch]:
        if isinstance(index, tuple) and len(index) == 2:
            return self.board[index[0]][index[1]]
        elif isinstance(index, int):
            return self.board[index]
        else:
            raise TypeError("Invalid index type for Widget:", type(index))
