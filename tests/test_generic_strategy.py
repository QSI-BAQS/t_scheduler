from itertools import chain
import json
import unittest
from t_scheduler.base import gate, util
from t_scheduler.schedule_orchestrator import ScheduleOrchestrator

from t_scheduler.templates.generic_templates import *

'''
import json
import unittest
from t_scheduler.base import util
from t_scheduler.schedule_orchestrator import ScheduleOrchestrator

from t_scheduler.templates.templates import *
tikz=False
with open('tests/qft_test_obj.json') as f:
    obj = json.load(f)
strat, wid = generic_flat_naive_strategy_with_litinski_5x3_unbuffered_widget(10, 7)
gates = util.make_gates(obj, lambda x: int(x) % 5)
dag_layers, all_gates = util.dag_create(obj, gates)
dag_roots = dag_layers[0]
orc = ScheduleOrchestrator(dag_roots, wid, strat, False, tikz)
orc.prewarm(100)
orc.queued.extend(orc.waiting)


'''


class GenericStrategyTest(unittest.TestCase):
    def test_flat_naive_qft(self, tikz=False, save_json=False):
        with open('tests/qft_test_obj.json') as f:
            obj = json.load(f)
        strat, wid = flat_naive_t_cultivator_widget(10, 5)
        gates = util.make_gates(obj, lambda x: int(x) % 5)
        dag_layers, all_gates = util.dag_create(obj, gates)
        dag_roots = dag_layers[0]

        orc = ScheduleOrchestrator(dag_roots, wid, strat, False, tikz, save_json)
        orc.schedule()
        return orc

    def test_filled_t_cult(self, tikz=False, save_json=False):
        with open('tests/qft_test_obj.json') as f:
            obj = json.load(f)
        strat, wid = flat_naive_t_cultivator_widget(10, 5)
        gates = util.make_gates(obj, lambda x: int(x) % 5)
        dag_layers, all_gates = util.dag_create(obj, gates)
        dag_roots = dag_layers[0]

        for row in wid.components[-2].sc_patches:
            for cell in row:
                cell.has_T = True # type: ignore
                wid.components[-2].available_states.add(cell)

        orc = ScheduleOrchestrator(dag_roots, wid, strat, False, tikz, save_json)
        orc.schedule()
        return orc

    def test_litinski_5x3_qft(self, tikz=False, save_json=False):
        with open('tests/qft_test_obj.json') as f:
            obj = json.load(f)
        strat, wid = flat_naive_litinski_5x3_unbuffered_widget(10, 7)
        gates = util.make_gates(obj, lambda x: int(x) % 5)
        dag_layers, all_gates = util.dag_create(obj, gates)
        dag_roots = dag_layers[0]

        orc = ScheduleOrchestrator(dag_roots, wid, strat, False, tikz, save_json)
        orc.schedule()
        return orc
    
    def test_litinski_5x3_qft_nobell(self, tikz=False, save_json=False):
        with open('tests/qft_test_obj.json') as f:
            obj = json.load(f)
        strat, wid = flat_naive_litinski_5x3_unbuffered_widget(10, 7, False)
        gates = util.make_gates(obj, lambda x: int(x) % 5)
        dag_layers, all_gates = util.dag_create(obj, gates)
        dag_roots = dag_layers[0]

        orc = ScheduleOrchestrator(dag_roots, wid, strat, False, tikz, save_json)
        orc.schedule()
        return orc


    def test_litinski_6x3_qft(self, tikz=False, save_json=False):
        with open('tests/qft_test_obj.json') as f:
            obj = json.load(f)
        strat, wid = flat_naive_litinski_6x3_dense_unbuffered_widget(10, 8)
        gates = util.make_gates(obj, lambda x: int(x) % 5)
        dag_layers, all_gates = util.dag_create(obj, gates)
        dag_roots = dag_layers[0]

        orc = ScheduleOrchestrator(dag_roots, wid, strat, False, tikz, save_json)
        orc.schedule()
        return orc

    def test_litinski_6x3_qft_nobell(self, tikz=False, save_json=False):
        with open('tests/qft_test_obj.json') as f:
            obj = json.load(f)
        strat, wid = flat_naive_litinski_6x3_dense_unbuffered_widget(10, 8, False)
        gates = util.make_gates(obj, lambda x: int(x) % 5)
        dag_layers, all_gates = util.dag_create(obj, gates)
        dag_roots = dag_layers[0]

        orc = ScheduleOrchestrator(dag_roots, wid, strat, False, tikz, save_json)
        orc.schedule()
        return orc

    def test_litinski_6x3_buffered_qft(self, tikz=False, save_json=False):
        with open('tests/qft_test_obj.json') as f:
            obj = json.load(f)
        strat, wid = buffered_naive_buffered_widget(10, 18, 2, factory_factory=MagicStateFactoryRegion.with_litinski_6x3_dense)
        gates = util.make_gates(obj, lambda x: int(x) % 5)
        dag_layers, all_gates = util.dag_create(obj, gates)
        dag_roots = dag_layers[0]

        orc = ScheduleOrchestrator(dag_roots, wid, strat, False, tikz, save_json)
        orc.schedule()
        return orc
    
    def test_litinski_6x3_buffered_qft_nobell(self, tikz=False):
        with open('tests/qft_test_obj.json') as f:
            obj = json.load(f)
        strat, wid = buffered_naive_buffered_widget(10, 18, 2, factory_factory=MagicStateFactoryRegion.with_litinski_6x3_dense, include_bell=False)
        gates = util.make_gates(obj, lambda x: int(x) % 5)
        dag_layers, all_gates = util.dag_create(obj, gates)
        dag_roots = dag_layers[0]

        orc = ScheduleOrchestrator(dag_roots, wid, strat, False, tikz)
        orc.schedule()

    def test_end_to_end_inject_vertical(self, tikz=False):
        gate_layers = [
            [*chain(*(([x] * 8) for x in [5, 0, 6, 8, 7]))],
        ]
        gate_layers = [[gate.T_Gate(t, 2, 3) for t in layer]
                       for layer in gate_layers]

        strat, wid = vertical_strategy_with_prefilled_buffer_widget(
            20, 5, rot_strat=RotationStrategyOption.INJECT)

        orc = ScheduleOrchestrator(gate_layers[0], wid, strat, False, tikz)

        orc.schedule()

    def test_comb_vertical(self, tikz=False):
        gate_layers = [
            [*chain(*(([x] * 8) for x in [5, 0, 16, 8, 26]))],
        ]
        gate_layers = [[gate.T_Gate(t, 2, 3) for t in layer]
                       for layer in gate_layers]

        strat, wid = vertical_strategy_with_prefilled_comb_widget(
            20, 10, rot_strat=RotationStrategyOption.BACKPROP_INIT, comb_height=5)

        orc = ScheduleOrchestrator(gate_layers[0], wid, strat, False, tikz)

        orc.schedule()

    def test_comb_vertical_qft(self, tikz=False):
        with open('tests/qft_8_test_obj.json') as f:
            obj = json.load(f)
        strat, wid = vertical_strategy_with_prefilled_comb_widget(
            20, 10, rot_strat=RotationStrategyOption.BACKPROP_INIT, comb_height=3)
        gates = util.make_gates(obj, lambda x: int(x) * 13 % 11 + 12)
        dag_layers, all_gates = util.dag_create(obj, gates)
        dag_roots = dag_layers[0]

        orc = ScheduleOrchestrator(dag_roots, wid, strat, False, tikz)
        orc.schedule()
    
    def test_comb_vertical_qft_route_one(self, tikz=False):
        with open('tests/qft_8_test_obj.json') as f:
            obj = json.load(f)
        strat, wid = vertical_strategy_with_prefilled_comb_widget(
            20, 10, rot_strat=RotationStrategyOption.BACKPROP_INIT, comb_height=3, route_width=1)
        gates = util.make_gates(obj, lambda x: int(x) * 13 % 11 + 12)
        dag_layers, all_gates = util.dag_create(obj, gates)
        dag_roots = dag_layers[0]

        orc = ScheduleOrchestrator(dag_roots, wid, strat, False, tikz)
        orc.schedule()
    def test_litinski_6x3_buffered_qft_with_prewarm(self, tikz=False):
        with open('tests/qft_test_obj.json') as f:
            obj = json.load(f)
        strat, wid = buffered_naive_buffered_widget(10, 20, 4, factory_factory=MagicStateFactoryRegion.with_litinski_6x3_dense)
        gates = util.make_gates(obj, lambda x: int(x) % 5)
        dag_layers, all_gates = util.dag_create(obj, gates)
        dag_roots = dag_layers[0]

        orc = ScheduleOrchestrator(dag_roots, wid, strat, False, tikz)
        orc.prewarm(100)
        orc.schedule()
    def test_end_to_end_backprop_vertical(self, tikz=False):
        gate_layers = [
            [*chain(*(([x] * 8) for x in [5, 0, 6, 8, 7]))],
        ]
        gate_layers = [[gate.T_Gate(t, 2, 3) for t in layer]
                       for layer in gate_layers]

        strat, wid = vertical_strategy_with_prefilled_buffer_widget(
            20, 5, rot_strat=RotationStrategyOption.BACKPROP_INIT)

        orc = ScheduleOrchestrator(gate_layers[0], wid, strat, False, tikz)

        orc.schedule()
    
    def test_end_to_end_backprop_vertical_comb(self):
        gate_layers = [
            [*chain(*(([x] * 8) for x in [5, 0, 16, 8, 26]))],
        ]
        gate_layers = [[gate.T_Gate(t, 2, 3) for t in layer]
                       for layer in gate_layers]

        strat, wid = vertical_strategy_with_prefilled_comb_widget(
            20, 10, rot_strat=RotationStrategyOption.BACKPROP_INIT, comb_height=5)

        orc = ScheduleOrchestrator(gate_layers[0], wid, strat, False)

        orc.schedule()

    
    def test_end_to_end_2(self, tikz=False):
        gate_layers = [
            [*chain(*(([x] * 10) for x in [5, 0, 6, 8, 7]))],
        ]
        gate_layers = [[gate.T_Gate(t, 1, 1) for t in layer]
                       for layer in gate_layers]

        strat, wid = tree_strategy_with_prefilled_buffer_widget(20, 5)
        
        orc = ScheduleOrchestrator(gate_layers[0], wid, strat, False, tikz)

        orc.schedule()

    
    def test_vertical_toffoli(self, tikz=False):
        strat, wid = vertical_strategy_with_prefilled_buffer_widget(26, 5, rot_strat=RotationStrategyOption.BACKPROP_INIT)
        obj = util.toffoli_example_input()
        gates = util.make_gates(obj)
        dag_layers, all_gates = util.dag_create(obj, gates)
        dag_roots = dag_layers[0]

        orc = ScheduleOrchestrator(dag_roots, wid, strat, False, tikz)
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
