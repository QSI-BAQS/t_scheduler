import json
import unittest
from itertools import chain
from t_scheduler import gate, util
from t_scheduler.schedule_orchestrator import ScheduleOrchestrator
from t_scheduler.strategy.buffered_naive_strategy import BufferedNaiveStrategy
from t_scheduler.strategy.flat_naive_strategy import FlatNaiveStrategy
from t_scheduler.strategy.tree_strategy import TreeRoutingStrategy
from t_scheduler.strategy.vertical_strategy import RotationStrategyOption, VerticalRoutingStrategy
from t_scheduler.widget.factory_region import MagicStateFactoryRegion


class TikzTest(unittest.TestCase):

    def test_vertical_toffoli(self):
        strat, wid = VerticalRoutingStrategy.with_prefilled_buffer_widget(26, 5, RotationStrategyOption.BACKPROP_INIT)
        obj = util.toffoli_example_input()
        gates = util.make_gates(obj)
        dag_layers, all_gates = util.dag_create(obj, gates)
        dag_roots = dag_layers[0]

        orc = ScheduleOrchestrator(dag_roots, wid, strat, False)
        orc.schedule()

        wid.make_coordinate_adapter()
        out = wid.save_tikz_region_layer()
        print(out)


if __name__ == '__main__':
    unittest.main()
