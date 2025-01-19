import unittest
from t_scheduler.base import util
from t_scheduler.schedule_orchestrator import ScheduleOrchestrator
from t_scheduler.templates.generic_templates import *
from t_scheduler.strategy.generic_strategy import RotationStrategyOption

class TikzTest(unittest.TestCase):

    def test_vertical_toffoli(self):
        strat, wid = vertical_strategy_with_prefilled_buffer_widget(26, 5, rot_strat=RotationStrategyOption.BACKPROP_INIT)
        obj = util.toffoli_example_input()
        gates = util.make_gates(obj)
        dag_layers, all_gates = util.dag_create(obj, gates)
        dag_roots = dag_layers[0]

        orc = ScheduleOrchestrator(dag_roots, wid, strat, False)
        orc.schedule()

        wid.make_coordinate_adapter()
        out = wid.save_tikz_region_layer()
        out += wid.save_tikz_patches_layer()
        print(''.join(map(str,out)))


if __name__ == '__main__':
    import sys
    if len(sys.argv) >= 2 and sys.argv[1] == 'debug': 
        strat, wid = vertical_strategy_with_prefilled_buffer_widget(26, 5, rot_strat=RotationStrategyOption.BACKPROP_INIT)
        wid.make_coordinate_adapter()
        out = wid.save_tikz_region_layer()
    else:
        unittest.main()
