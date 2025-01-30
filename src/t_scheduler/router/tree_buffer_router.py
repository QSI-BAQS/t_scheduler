from __future__ import annotations
from typing import List

from collections import deque

from ..base.gate import GateType

from ..base import (Patch, 
                    PatchOrientation, 
                    PatchType, 
                    Transaction,
                    Response, 
                    ResponseStatus)
from ..region import PrefilledMagicStateRegion
from .abstract_router import AbstractRouter, export_router

class TreeNode:
    parent: TreeNode | None
    children: List[TreeNode]
    path: List[Patch]
    path_fragment: List[Patch]
    source_lane: int
    reparsed: bool

    def __init__(
        self,
        parent: TreeNode | None,
        path: List[Patch],
        source_lane: int | None = None,
        debug_source="",
    ):
        self.parent = parent
        self.children = []
        self.path = path
        self.reparsed = False

        self.debug_source = debug_source

        if parent is not None:
            self.source_lane = parent.source_lane
            self.path_fragment = path[len(parent.path) :]
        else:
            assert source_lane is not None
            self.source_lane = source_lane
            self.path_fragment = path

    def __repr__(self):
        return f"{{ {self.path} ({self.debug_source}): {{ 'frag': {self.path_fragment}, 'children': {self.children} }} }}"

@export_router(PrefilledMagicStateRegion.with_chessboard_rotation)
class TreeFilledBufferRouter(AbstractRouter):
    """
    Note: Works only with passthrough bus router
    Assumption because output_col is used to detect which columns of T to assign
    Also only works with chessboard shape PrefilledMagicStateRegion
    """

    region: PrefilledMagicStateRegion

    consumption_frontier: List[TreeNode]

    def __init__(self, buffer, depth_offset=2 / 3) -> None:
        self.region = buffer

        self.consumption_frontier = [
            TreeNode(None, [], q) for q in range(self.region.width // 2 + 1)
        ]
        # TODO adapt for missing bell state columns

        self.dig_depth = int(self.region.height * depth_offset)

        self.init_frontier()

    @staticmethod
    def _make_transaction(path, connect=None):
        return Transaction(
            path, [path[0]], connect_col=connect, magic_state_patch=path[0]
        )

    def _request_transaction(self, lane: int) -> Transaction | None:
        """
        lane: which lane to search from
        """
        if not (path := self.tree_search(lane)):
            return None
        reduced_path = self.path_reduce(path)
        # if lane == 1:
        #     breakpoint()
        return self._make_transaction(reduced_path, connect=reduced_path[-1].local_x)

    @staticmethod
    def adjacent(cell1: Patch, cell2: Patch):
        return abs(cell1.local_y - cell2.local_y) + abs(cell1.local_x - cell2.local_x) == 1

    @staticmethod
    def path_reduce(path: List[Patch]):
        prev_len = float("inf")
        curr_len = len(path)
        while curr_len < prev_len:
            prev_len = curr_len
            new_path = [path[0]]

            i = 1
            while i < len(path):
                new_path.append(path[i])
                if path[i].local_y == 0:
                    break
                if i + 3 < len(path) and TreeFilledBufferRouter.adjacent(
                    path[i], path[i + 3]
                ):
                    i += 3
                else:
                    i += 1
            path = new_path
            new_path = []
            curr_len = len(new_path)
        return path

    def init_frontier(self):
        # TODO add support for no bell state columns
        for lane in range(self.region.width // 2 + 1):
            root = self.consumption_frontier[lane]
            if lane != 0:
                c = 2 * lane - 1  # Left col of lane with shifted offset
                root.children.append(
                    TreeNode(root, [self.region[0, c]], debug_source="init")
                )
            else:
                c = 2 * lane + 1  # Left col of lane with shifted offset
                root.children.append(
                    TreeNode(root, [self.region[0, c]], debug_source="init")
                )
            if lane != len(self.consumption_frontier) - 1:
                c = 2 * lane  # right col of lane with shifted offset
                root.children.append(
                    TreeNode(root, [self.region[0, c]], debug_source="init")
                )
            else:
                c = 2 * lane - 2  # Left col of lane with shifted offset
                root.children.append(
                    TreeNode(root, [self.region[0, c]], debug_source="init")
                )

            root.children.sort(
                key=lambda x: abs(x.path[-1].local_x - self.region.width // 2),
                reverse=False,
            )
            if lane != 0 and lane != len(self.consumption_frontier) - 1:
                self.generate_mining(root.children[1])

    def generate_mining(self, root: TreeNode):
        depth = self.dig_depth
        curr = root
        source_lane = root.source_lane
        for r in range(1, depth):
            curr.reparsed = True
            child = TreeNode(
                curr,
                curr.path + [self.region[r, curr.path[-1].local_x]],
                debug_source="mine",
            )
            curr.children.append(child)

            curr = child
            curr.reparsed = True
            child = TreeNode(
                curr,
                curr.path
                + [
                    self.region[
                        r, 2 * source_lane - (curr.path[-1].local_x == 2 * source_lane)
                    ]
                ],
                debug_source="mine",
            )
            curr.children.append(child)
            curr = child

    def tree_search(self, lane: int, retry=True):
        stack = deque([(self.consumption_frontier[lane], 0)])
        while stack:
            curr, child_idx = stack.popleft()
            if child_idx >= len(curr.children):
                continue
            stack.append((curr, child_idx + 1))
            curr_child = curr.children[child_idx]
            if any(p.locked() for p in curr_child.path_fragment):
                continue

            if curr_child.path[-1].T_available():
                return curr_child.path[::-1]

            if not curr_child.reparsed:
                curr_child.reparsed = True
                self.reparse_tree(curr_child)

            stack.append((curr_child, 0))
        if retry:
            self.reparse_tree(self.consumption_frontier[lane].children[0])
            self.consumption_frontier[lane].children[0].children.sort(
                key=lambda x: abs(x.path[-1].local_y - self.dig_depth)
                + abs(x.path[-1].local_x - lane * 2)
            )
            return self.tree_search(lane, False)

        return None

    def reparse_tree(self, tree_node: TreeNode):
        curr_patch = tree_node.path[-1]

        row, col = curr_patch.local_y, curr_patch.local_x
        new_patches: List[Patch] = []

        for r, c in [(row + 1, col), (row, col - 1), (row, col + 1), (row - 1, col)]:
            if 0 <= r < self.region.height and 0 <= c < self.region.width:
                if (patch := self.region[r, c]).patch_type == PatchType.T:
                    new_patches.append(patch)

        new_children = []
        if new_patches:
            for patch in new_patches:
                matching_rotation = (patch.local_y == curr_patch.local_y) ^ (
                    patch.orientation == PatchOrientation.Z_TOP
                )
                if matching_rotation and patch.T_available():
                    new_children.append(TreeNode(tree_node, tree_node.path + [patch]))
            tree_node.children = new_children

        if not new_children:
            bfs_queue = deque([(curr_patch.local_y, curr_patch.local_x)])
            parent = {}
            seen = {(curr_patch.local_y, curr_patch.local_x)}
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
                    if 0 <= r < self.region.height and 0 <= c < self.region.width:
                        patch = self.region[r, c]
                        matching_rotation = (row == r) ^ (
                            patch.orientation == PatchOrientation.Z_TOP
                        )
                        if patch.patch_type == PatchType.T and matching_rotation:
                            parent[r, c] = (row, col)
                            results.append((r, c))
                        elif patch.patch_type == PatchType.ROUTE and (r, c) not in seen:
                            parent[r, c] = (row, col)
                            bfs_queue.append((r, c))
                            seen.add((r, c))
            for r, c in results:
                fragment = [self.region[r, c]]
                while (r, c) in parent:
                    r, c = parent[r, c]
                    fragment.append(self.region[r, c])
                fragment.pop()
                new_children.append(
                    TreeNode(tree_node, tree_node.path + fragment[::-1])
                )
            tree_node.children = new_children
    def generic_transaction(self, source_patch, *args, target_orientation=None, gate_type = GateType.T_STATE, **kwargs):
        if gate_type != GateType.T_STATE:
            return Response()
        reg_col = self.clamp(source_patch.x - self.region.offset[1], 0, self.region.width - 1)
        trans = self._request_transaction(reg_col // 2, **kwargs)
        if trans:
            return Response(ResponseStatus.SUCCESS, trans)
        else:
            return Response()