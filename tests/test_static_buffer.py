import json
import unittest
from itertools import chain
from t_scheduler.base import util
from t_scheduler.base import gate
from t_scheduler.schedule_orchestrator import ScheduleOrchestrator
from t_scheduler.strategy.buffered_naive_strategy import BufferedNaiveStrategy
from t_scheduler.strategy.flat_naive_strategy import FlatNaiveStrategy
from t_scheduler.strategy.tree_strategy import TreeRoutingStrategy
from t_scheduler.strategy.vertical_strategy import RotationStrategyOption, VerticalRoutingStrategy
from t_scheduler.widget.factory_region import MagicStateFactoryRegion

from t_scheduler.templates import *


class StaticBufferTest(unittest.TestCase):
    @unittest.skip('not implemented')
    def test_end_to_end_lookback_vertical(self, tikz=False):
        base_gate_layers = [
            [*chain(*(([x] * 8) for x in [5, 0, 6, 8, 7]))],
        ]
        gate_layers = [[gate.T_Gate(t, 2, 3) for t in layer]
                       for layer in base_gate_layers]

        strat, wid = vertical_strategy_with_prefilled_buffer_widget(
            20, 5, rot_strat=RotationStrategyOption.LOOKBACK)

        orc = ScheduleOrchestrator(gate_layers[0], wid, strat, False, tikz)
        orc.schedule()

    @unittest.skip('not implemented')
    def test_end_to_end_reject_vertical(self, tikz=False):
        gate_layers = [
            [*chain(*(([x] * 8) for x in [5, 0, 6, 8, 7]))],
        ]
        gate_layers = [[gate.T_Gate(t, 2, 3) for t in layer]
                       for layer in gate_layers]

        strat, wid = vertical_strategy_with_prefilled_buffer_widget(
            20, 5, rot_strat=RotationStrategyOption.REJECT)

        orc = ScheduleOrchestrator(gate_layers[0], wid, strat, False, tikz)

        raise NotImplementedError("Infinite loop detection not implemented")

        # try:
        #     # This should fail
        #     # TODO add infinite loop detection
        #     raise Exception()
        #     orc.schedule()
        # except orc.SchedulerException:
        #     pass`

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

        orc = ScheduleOrchestrator(gate_layers[0], wid, strat, True)

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

    def test_vertical_toffoli(self, tikz=False):
        strat, wid = vertical_strategy_with_prefilled_buffer_widget(26, 5, RotationStrategyOption.BACKPROP_INIT)
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

    def test_flat_naive_qft(self, tikz=False):
        with open('tests/qft_test_obj.json') as f:
            obj = json.load(f)
        strat, wid = flat_naive_strategy_with_t_cultivator_widget(10, 5)
        gates = util.make_gates(obj, lambda x: int(x) % 5)
        dag_layers, all_gates = util.dag_create(obj, gates)
        dag_roots = dag_layers[0]

        orc = ScheduleOrchestrator(dag_roots, wid, strat, False, tikz)
        orc.schedule()

    def test_litinski_5x3_qft(self, tikz=False):
        with open('tests/qft_test_obj.json') as f:
            obj = json.load(f)
        strat, wid = flat_naive_strategy_with_litinski_5x3_unbuffered_widget(10, 7)
        gates = util.make_gates(obj, lambda x: int(x) % 5)
        dag_layers, all_gates = util.dag_create(obj, gates)
        dag_roots = dag_layers[0]

        orc = ScheduleOrchestrator(dag_roots, wid, strat, False, tikz)
        orc.schedule()

    def test_litinski_6x3_qft(self, tikz=False):
        with open('tests/qft_test_obj.json') as f:
            obj = json.load(f)
        strat, wid = flat_naive_strategy_with_litinski_6x3_dense_unbuffered_widget(10, 8)
        gates = util.make_gates(obj, lambda x: int(x) % 5)
        dag_layers, all_gates = util.dag_create(obj, gates)
        dag_roots = dag_layers[0]

        orc = ScheduleOrchestrator(dag_roots, wid, strat, False, tikz)
        orc.schedule()

    def test_litinski_6x3_buffered_qft(self, tikz=False):
        with open('tests/qft_test_obj.json') as f:
            obj = json.load(f)
        strat, wid = buffered_naive_strategy_with_buffered_widget(10, 18, 2, factory_factory=MagicStateFactoryRegion.with_litinski_6x3_dense)
        gates = util.make_gates(obj, lambda x: int(x) % 5)
        dag_layers, all_gates = util.dag_create(obj, gates)
        dag_roots = dag_layers[0]

        orc = ScheduleOrchestrator(dag_roots, wid, strat, False, tikz)
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

if __name__ == '__main__':
    unittest.main()
