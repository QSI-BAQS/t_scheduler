from ..widget.bell_region import BellRegion
from .abstract_router import AbstractRouter, export_router


@export_router(BellRegion)
class BellRouter(AbstractRouter):
    region: BellRegion

    def __init__(self, bell) -> None:
        self.region = bell

    def _request_transaction(self, *args, **kwargs):
        return None