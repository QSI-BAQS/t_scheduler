from t_scheduler.scheduler import *

def tree_search(widget, reg, retry=True):
    if widget[0, 2 * reg].locked():
        return None

    stack = deque([(widget.reg_t_frontier[reg], 0)])
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
            reparse_tree(widget, curr_child)

        stack.append((curr_child, 0))
    if retry:
        reparse_tree(widget, widget.reg_t_frontier[reg].children[0])
        widget.reg_t_frontier[reg].children[0].children.sort(
            key=lambda x: abs(x.path[-1].row - widget.dig_depth)
            + abs(x.path[-1].col - reg * 2)
        )
        tree_search(widget, reg, False)

    return None


def reparse_tree(widget, tree_node):
    curr_patch = tree_node.path[-1]

    row, col = curr_patch.row, curr_patch.col
    new_patches = []

    # if curr_patch.col -

    for r, c in [(row + 1, col), (row, col - 1), (row, col + 1), (row - 1, col)]:
        if 2 <= r < widget.height and 0 <= c < widget.width:
            if (patch := widget[r, c]).patch_type == PatchType.T:
                new_patches.append(patch)

    new_children = []
    if new_patches:
        for patch in new_patches:
            matching_rotation = (patch.row == curr_patch.row) ^ (
                patch.orientation == PatchOrientation.Z_TOP
            )
            if matching_rotation:
                new_children.append(
                    TreeNode(tree_node, tree_node.path + [patch]))
        tree_node.children = new_children

    if not new_children:
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
            fragment = [widget[r, c]]
            while (r, c) in parent:
                r, c = parent[r, c]
                fragment.append(widget[r, c])
            fragment.pop()
            new_children.append(
                TreeNode(tree_node, tree_node.path + fragment[::-1]))
        tree_node.children = new_children



class TreeScheduler(Scheduler):
    '''
        TODO: Docstring this class
    '''

    def __init__(
            self,
            layers,
            widget,
            **kwargs):
        '''
        TODO: Comment on the rotation strategy
        '''
        super().__init__(layers, widget, tree_search, RotationStrategy.REJECT, **kwargs)

        for q in range(widget.width // 2):
            root = widget.reg_t_frontier[q]
            if q != 0:
                c = 2 * q
                root.children.append(
                    TreeNode(root, [widget[0, c], widget[1, c], widget[2, c]])
                )
            if q != widget.width // 2 - 1:
                c = 2 * q + 1
                root.children.append(
                    TreeNode(
                        root,
                        [widget[0, c - 1], widget[0, c],
                            widget[1, c], widget[2, c]],
                    )
                )
            root.children.sort(
                key=lambda x: abs(x.path[-1].col - widget.width // 2), reverse=True
            )
            if q != 0 and q != widget.width // 2 - 1:
                self.generate_mining(root.children[1])

    def generate_mining(self, root):
        depth = self.widget.dig_depth
        curr = root
        q = root.reg
        for r in range(3, depth):
            curr.reparsed = True
            child = TreeNode(root, curr.path +
                             [self.widget[r, curr.path[-1].col]])
            curr.children.append(child)
            curr = child
            curr.reparsed = True
            child = TreeNode(
                root, curr.path +
                [self.widget[r, 2 * q + (curr.path[-1].col == 2 * q)]]
            )
            curr.children.append(child)
            curr = child
