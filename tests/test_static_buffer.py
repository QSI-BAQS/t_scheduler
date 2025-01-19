import json
import unittest
from itertools import chain
from t_scheduler.base import util
from t_scheduler.base import gate
from t_scheduler.schedule_orchestrator import ScheduleOrchestrator
from t_scheduler.templates import *


class StaticBufferTest(unittest.TestCase):
   
    def test_end_to_end_2(self, tikz=False):
        gate_layers = [
            [*chain(*(([x] * 10) for x in [5, 0, 6, 8, 7]))],
        ]
        gate_layers = [[gate.T_Gate(t, 1, 1) for t in layer]
                       for layer in gate_layers]

        strat, wid = tree_strategy_with_prefilled_buffer_widget(20, 5)
        
        orc = ScheduleOrchestrator(gate_layers[0], wid, strat, False, tikz)

        orc.schedule()

    @unittest.skip('too slow')
    def test_end_to_end_3(self, tikz=False):
        gate_layers = [
            [*chain(*(([x] * 100) for x in [6, 7, 9]))],
        ]
        gate_layers = [[gate.T_Gate(t, 1, 1) for t in layer]
                       for layer in gate_layers]

        strat, wid = tree_strategy_with_prefilled_buffer_widget(40, 20)
        
        orc = ScheduleOrchestrator(gate_layers[0], wid, strat, False, tikz)

        orc.schedule()

    def test_tree_qft(self, tikz=False):
        with open('tests/qft_test_obj.json') as f:
            obj = json.load(f)
        strat, wid = tree_strategy_with_prefilled_buffer_widget(12, 10)
        gates = util.make_gates(obj, lambda x: int(x) % 5)
        dag_layers, all_gates = util.dag_create(obj, gates)
        dag_roots = dag_layers[0]

        orc = ScheduleOrchestrator(dag_roots, wid, strat, False, tikz)
        orc.schedule()



if __name__ == '__main__':
    unittest.main()
