from typing import Callable, Literal, Tuple

from ..base import *
from ..router import *
from ..strategy import *
from ..widget import *

def _squash_and_add_bell_regions(*regions):
    output = []
    for region in regions:
        for row in region.sc_patches:
            output.append([
                Patch(PatchType.BELL, 0, 0),
                *row,
                Patch(PatchType.BELL, 0, -1),
            ])
    return output

def _concat_vertical(*rowlists):
    return sum(rowlists, start=[])

