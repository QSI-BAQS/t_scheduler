from abc import ABC
from typing import List

from ..base import Gate

class AbstractStrategy(ABC):
    needs_upkeep: bool = False

    def alloc_gate(self, gate: Gate) -> Gate | None:
        raise NotImplementedError()

    def upkeep(self) -> List[Gate]:
        raise NotImplementedError()