from t_scheduler.tracker.volume_tracker import SpaceTimeVolumeType
from ..base.transaction import Transaction
from ..base.response import Response, ResponseStatus
from ..base.gate import GateType
from ..region.bell_region import BellRegion
from .abstract_router import AbstractRouter, export_router


@export_router(BellRegion.input_region)
@export_router(BellRegion.output_region)
class BellRouter(AbstractRouter):
    region: BellRegion

    def __init__(self, region) -> None:
        self.region = region.local_view
        self.bell_idle_tag = None

    def _make_transaction(self):
        buffer_patch = self.region[0,0]

        def _activate_callback(trans):
            if not self.bell_idle_tag:
                self.bell_idle_tag = self.vol_tracker.make_tag(tag_type=SpaceTimeVolumeType.BELL_IDLE_VOLUME)
                self.bell_idle_tag.start()
            self.bell_idle_tag.end()
            self.bell_idle_tag.apply()
            self.bell_idle_tag.start_time -= self.region.bell_rate_recip # type: ignore
        
        trans = Transaction([buffer_patch], [buffer_patch], on_activate_callback=_activate_callback)

        return trans

    def generic_transaction(self, *args, gate_type=GateType.T_STATE, **kwargs):
        if gate_type not in [GateType.BELL_IN, GateType.BELL_OUT]:
            return Response()
        
        if gate_type == GateType.BELL_IN and self.region.bell_type != "INPUT":
            return Response()
        elif gate_type == GateType.BELL_OUT and self.region.bell_type != "OUTPUT":
            return Response()

        if not self.region[0,0].locked():
            return Response(ResponseStatus.SUCCESS, self._make_transaction())
        else:
            return Response()