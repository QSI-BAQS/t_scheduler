from collections import deque

def tree_search_buffer(widget, reg):
    raise NotImplementedError()
    deferred = deque()
    source = tree_search_order(widget, reg)
    req = yield None
    while True:
        if req == "NEW":
            path = next(source)
            while True:
                if path[-1].used:
                    path = next(source)
                elif any(p.locked() for p in path):
                    deferred.append(path)


def tree_search_order(widget, reg):
    raise NotImplementedError()
    if reg == 0:
        raise NotImplementedError()
    elif reg == widget.width - 1:
        raise NotImplementedError()
    else:
        c = 2 * reg
        if c < widget.width // 2:
            yield [widget[0, c], widget[1, c], widget[2, c]]
            yield [widget[0, c], widget[0, c + 1], widget[1, c + 1], widget[2, c + 1]]
            prefix = [widget[0, c], widget[0, c + 1],
                      widget[1, c + 1], widget[2, c + 1]]
        else:
            yield [widget[0, c], widget[0, c + 1], widget[1, c + 1], widget[2, c + 1]]
            yield [widget[0, c], widget[1, c], widget[2, c]]
            prefix = [widget[0, c], widget[1, c], widget[2, c]]

        for r in range(3, widget.height // 2):
            prefix.append(widget[r, prefix[-1].col])
            yield prefix
            prefix.append(widget[r, c + (prefix[-1].col == c)])
            yield prefix

    bfs_fringe = deque()
