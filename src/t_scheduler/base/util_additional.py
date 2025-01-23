from typing import List, Tuple

from t_scheduler.schedule_orchestrator import ScheduleOrchestrator
from .gate_additional import GSPrepGate


def make_gsprep_layers(gs_prep_layers: List[List[Tuple[int, int]]]):
    gs_gate_layers = [
        [GSPrepGate(targs) for targs in layer] for layer in gs_prep_layers
    ]
    for i in range(len(gs_gate_layers)):
        for gate in gs_gate_layers[i]:
            if i > 0:
                gate.pre = gs_gate_layers[i - 1]
            if i < len(gs_gate_layers) - 1:
                gate.post = gs_gate_layers[i + 1]
    print(gs_gate_layers)
    return gs_gate_layers

# # Example
# orch: ScheduleOrchestrator = ... # type: ignore
# gsprep_layers = make_gsprep_layers(...) # type: ignore
# prewarm_cycles:int = ... # type: ignore
# orch.prepare_gs(gsprep_layers[0], sum(gsprep_layers, start=[]), time_limit=prewarm_cycles)