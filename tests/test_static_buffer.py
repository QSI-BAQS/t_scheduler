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


class StaticBufferTest(unittest.TestCase):
    def test_end_to_end_lookback_vertical(self):
        base_gate_layers = [
            [*chain(*(([x] * 8) for x in [5, 0, 6, 8, 7]))],
        ]
        gate_layers = [[gate.T_Gate(t, 2, 3) for t in layer]
                       for layer in base_gate_layers]

        strat, wid = VerticalRoutingStrategy.with_prefilled_buffer_widget(
            20, 5, rot_strat=RotationStrategyOption.LOOKBACK)

        orc = ScheduleOrchestrator(gate_layers[0], wid, strat, False)
        orc.schedule()

    def test_end_to_end_reject_vertical(self):
        gate_layers = [
            [*chain(*(([x] * 8) for x in [5, 0, 6, 8, 7]))],
        ]
        gate_layers = [[gate.T_Gate(t, 2, 3) for t in layer]
                       for layer in gate_layers]

        strat, wid = VerticalRoutingStrategy.with_prefilled_buffer_widget(
            20, 5, rot_strat=RotationStrategyOption.REJECT)

        orc = ScheduleOrchestrator(gate_layers[0], wid, strat, False)

        raise NotImplementedError("Infinite loop detection not implemented")

        # try:
        #     # This should fail
        #     # TODO add infinite loop detection
        #     raise Exception()
        #     orc.schedule()
        # except orc.SchedulerException:
        #     pass`

    def test_end_to_end_inject_vertical(self):
        gate_layers = [
            [*chain(*(([x] * 8) for x in [5, 0, 6, 8, 7]))],
        ]
        gate_layers = [[gate.T_Gate(t, 2, 3) for t in layer]
                       for layer in gate_layers]

        strat, wid = VerticalRoutingStrategy.with_prefilled_buffer_widget(
            20, 5, rot_strat=RotationStrategyOption.INJECT)

        orc = ScheduleOrchestrator(gate_layers[0], wid, strat, False)

        orc.schedule()

    def test_end_to_end_backprop_vertical(self):
        gate_layers = [
            [*chain(*(([x] * 8) for x in [5, 0, 6, 8, 7]))],
        ]
        gate_layers = [[gate.T_Gate(t, 2, 3) for t in layer]
                       for layer in gate_layers]

        strat, wid = VerticalRoutingStrategy.with_prefilled_buffer_widget(
            20, 5, rot_strat=RotationStrategyOption.BACKPROP_INIT)

        orc = ScheduleOrchestrator(gate_layers[0], wid, strat, False)

        orc.schedule()

    def test_end_to_end_2(self):
        gate_layers = [
            [*chain(*(([x] * 10) for x in [5, 0, 6, 8, 7]))],
        ]
        gate_layers = [[gate.T_Gate(t, 1, 1) for t in layer]
                       for layer in gate_layers]

        strat, wid = TreeRoutingStrategy.with_prefilled_buffer_widget(20, 5)
        
        orc = ScheduleOrchestrator(gate_layers[0], wid, strat, False)

        orc.schedule()

    def test_end_to_end_3(self):
        gate_layers = [
            [*chain(*(([x] * 100) for x in [6, 7, 9]))],
        ]
        gate_layers = [[gate.T_Gate(t, 1, 1) for t in layer]
                       for layer in gate_layers]

        strat, wid = TreeRoutingStrategy.with_prefilled_buffer_widget(40, 20)
        
        orc = ScheduleOrchestrator(gate_layers[0], wid, strat, False)

        orc.schedule()

    def test_vertical_toffoli(self):
        strat, wid = VerticalRoutingStrategy.with_prefilled_buffer_widget(26, 5, RotationStrategyOption.BACKPROP_INIT)
        obj = util.toffoli_example_input()
        gates = util.make_gates(obj)
        dag_layers, all_gates = util.dag_create(obj, gates)
        dag_roots = dag_layers[0]

        orc = ScheduleOrchestrator(dag_roots, wid, strat, False)
        orc.schedule()

    def test_tree_qft(self):
        with open('tests/qft_test_obj.json') as f:
            obj = json.load(f)
        strat, wid = TreeRoutingStrategy.with_prefilled_buffer_widget(12, 10)
        gates = util.make_gates(obj, lambda x: int(x) % 5)
        dag_layers, all_gates = util.dag_create(obj, gates)
        dag_roots = dag_layers[0]

        orc = ScheduleOrchestrator(dag_roots, wid, strat, False)
        orc.schedule()

    def test_flat_naive_qft(self):
        with open('tests/qft_test_obj.json') as f:
            obj = json.load(f)
        strat, wid = FlatNaiveStrategy.with_t_cultivator_widget(10, 5)
        gates = util.make_gates(obj, lambda x: int(x) % 5)
        dag_layers, all_gates = util.dag_create(obj, gates)
        dag_roots = dag_layers[0]

        orc = ScheduleOrchestrator(dag_roots, wid, strat, False)
        orc.schedule()

    def test_litinski_5x3_qft(self):
        with open('tests/qft_test_obj.json') as f:
            obj = json.load(f)
        strat, wid = FlatNaiveStrategy.with_litinski_5x3_unbuffered_widget(10, 7)
        gates = util.make_gates(obj, lambda x: int(x) % 5)
        dag_layers, all_gates = util.dag_create(obj, gates)
        dag_roots = dag_layers[0]

        orc = ScheduleOrchestrator(dag_roots, wid, strat, False)
        orc.schedule()

    def test_litinski_6x3_qft(self):
        with open('tests/qft_test_obj.json') as f:
            obj = json.load(f)
        strat, wid = FlatNaiveStrategy.with_litinski_6x3_dense_unbuffered_widget(10, 8)
        gates = util.make_gates(obj, lambda x: int(x) % 5)
        dag_layers, all_gates = util.dag_create(obj, gates)
        dag_roots = dag_layers[0]

        orc = ScheduleOrchestrator(dag_roots, wid, strat, False)
        orc.schedule()

    def test_litinski_6x3_buffered_qft(self):
        with open('tests/qft_test_obj.json') as f:
            obj = json.load(f)
        strat, wid = BufferedNaiveStrategy.with_buffered_widget(10, 18, 2, factory_factory=MagicStateFactoryRegion.with_litinski_6x3_dense)
        gates = util.make_gates(obj, lambda x: int(x) % 5)
        dag_layers, all_gates = util.dag_create(obj, gates)
        dag_roots = dag_layers[0]

        orc = ScheduleOrchestrator(dag_roots, wid, strat, True)


if __name__ == '__main__':
    unittest.main()
