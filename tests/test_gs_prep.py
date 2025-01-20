import json
import unittest
from t_scheduler.base import gate, util, util_additional
from t_scheduler.schedule_orchestrator import ScheduleOrchestrator

from t_scheduler.templates.generic_templates import *
from t_scheduler.strategy.generic_strategy import DummyMapper


class GraphStatePrepTest(unittest.TestCase):
    def test_basic(self):
        with open('tests/qft_test_obj.json') as f:
            obj = json.load(f)
        strat, wid = buffered_naive_buffered_widget(10, 18, 2, factory_factory=MagicStateFactoryRegion.with_litinski_6x3_dense, include_bell=False)
        strat.mapper = DummyMapper(2)

        gates = util.make_gates(obj, lambda x: int(x) % 5)
        dag_layers, all_gates = util.dag_create(obj, gates)
        dag_roots = dag_layers[0]

        gsprep_layers = [
            [(0, 1), (2, 3),],
            [(1, 2), (3, 4),],
            [(0, 2)],
            [(1, 3)],
            [(2, 4)],
            [(0, 3)],
            [(1, 4)],
            [(0, 4)],
        ]
        gsprep_layers = util_additional.make_gsprep_layers(gsprep_layers)

        prewarm_cycles: int = len(gsprep_layers) * 6


        orc = ScheduleOrchestrator(dag_roots, wid, strat, False, False, json=True)
        orc.prepare_gs(gsprep_layers[0], sum(gsprep_layers, start=[]), time_limit=prewarm_cycles)

        orc.schedule()
        return orc


if __name__ == '__main__':
    unittest.main()
