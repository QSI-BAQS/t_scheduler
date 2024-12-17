from collections import defaultdict, deque
from typing import TextIO

from t_scheduler.strategy.buffered_naive_strategy import BufferedNaiveStrategy
from t_scheduler.strategy.flat_naive_strategy import FlatNaiveStrategy
from t_scheduler.strategy.tree_strategy import TreeRoutingStrategy
from t_scheduler.strategy.vertical_strategy import VerticalRoutingStrategy
from t_scheduler.widget.factory_region import MagicStateFactoryRegion
from t_scheduler.widget.widget import Widget


class ScheduleOrchestrator:
    def __init__(
        self,
        gate_dag_roots,
        widget,
        strategy,
        debug: bool = False,
        tikz_output: bool = False
    ):
        self.widget: Widget = widget
        self.strategy: BufferedNaiveStrategy = strategy

        self.processed = set()

        self.waiting = deque(gate_dag_roots)
        self.queued = []

        self.active = deque()
        self.next_active = []

        self.output_layers = []

        self.curr_layer = []

        self.debug = debug

        self.ROTATION_DURATION = 3
        self.time = 0

        self.hazard = {}

        self.T_queue = []
        self.next_T_queue = []

        self.tikz_output = tikz_output

        if self.tikz_output:
            self.output_objs = []
            self.widget.make_coordinate_adapter()

    def schedule(self):
        self.queued.extend(self.waiting)

        while self.queued or self.active:
            self.schedule_pass()

    def schedule_pass(self):

        next_queued = []
        for gate in self.queued:
            if gate in self.processed:
                continue
            elif gate.available() and (active_gate := self.strategy.alloc_gate(gate)):
                self.active.append(active_gate)
                self.processed.add(active_gate)
            else:
                next_queued.append(gate)

        self.queued = next_queued

        if self.strategy.needs_upkeep:
            self.active.extend(self.strategy.upkeep())

        # Print widget board state
        if self.debug:
            print(self.widget.to_str_output_dedup(), end='')

        self.output_layers.append([])
        for gate in self.active:
            self.output_layers[-1].append(gate.transaction.active_cells)

        if self.tikz_output and self.widget.rep_count == 1:
            # from lattice_surgery_draw.tikz_layer import TikzLayers
            # print('\\begin{tikzpicture}[scale=0.5]', file=file)
            # print(''.join(map(str,
            #                   self.widget.save_tikz_region_layer() + self.widget.save_tikz_patches_layer())), file=file)
            # print('\\end{tikzpicture}\n\\newpage', file=file)
            # file.close()
            pass


        for gate in self.active:
            gate.tick()

        self.widget.update()

        for gate in self.active:
            gate.cleanup(self)

        for gate in self.active:
            gate.next(self)
            if not gate.completed():
                self.next_active.append(gate)
            else:
                for child in gate.post:
                    if all(g.completed() for g in child.pre):
                        self.queued.append(child)
        self.active = self.next_active
        self.next_active = deque()

        self.time += 1

    def get_space_time_volume(self):
        volume = 0
        for layer in self.output_layers:
            for gate_cells in layer:
                volume += len(gate_cells)
        return volume

    def get_total_cycles(self):
        return self.time


if __name__ == '__main__':
    import t_scheduler.util as util
    from t_scheduler.gate import T_Gate
    from itertools import chain

    # Test vertical prefilled with reuse
    # strat, wid = VerticalRoutingStrategy.with_prefilled_buffer_widget(20, 5)
    # gate_layers = [
    #         [*chain(*(([x] * 8) for x in [5, 0, 6, 8, 7]))],
    #     ]
    # gate_layers = [[T_Gate(t, 2, 3) for t in layer] for layer in gate_layers]

    # orc = ScheduleOrchestrator(gate_layers[0], wid, strat, True)

    # Test with toffoli
    # strat, wid = VerticalRoutingStrategy.with_prefilled_buffer_widget(26, 5)
    # obj = util.toffoli_example_input()
    # dag_layers, all_gates = util.dag_create(obj)
    # dag_roots = dag_layers[0]

    # orc = ScheduleOrchestrator(dag_roots, wid, strat, True)

    # TEst tree with qft
    # obj = eval(open('../../json.out').read())
    # strat, wid = TreeRoutingStrategy.with_prefilled_buffer_widget(10, 10)
    # gates = util.make_gates(obj, lambda x: x % 5)
    # dag_layers, all_gates = util.dag_create(obj, gates)
    # dag_roots = dag_layers[0]

    # orc = ScheduleOrchestrator(dag_roots, wid, strat, True)

    # Test flat naive with qft
    # obj = eval(open('../../json.out').read())
    # strat, wid = FlatNaiveStrategy.with_t_cultivator_widget(10, 5)
    # gates = util.make_gates(obj, lambda x: x % 5)
    # dag_layers, all_gates = util.dag_create(obj, gates)
    # dag_roots = dag_layers[0]

    # orc = ScheduleOrchestrator(dag_roots, wid, strat, True)

    # Test litinski 5x3
    # obj = eval(open('../../json.out').read())
    # strat, wid = FlatNaiveStrategy.with_litinski_5x3_unbuffered_widget(10, 7)
    # gates = util.make_gates(obj, lambda x: x % 5)
    # dag_layers, all_gates = util.dag_create(obj, gates)
    # dag_roots = dag_layers[0]

    # orc = ScheduleOrchestrator(dag_roots, wid, strat, True)

    # Test litinski 6x3
    # obj = eval(open('../../json.out').read())
    # strat, wid = FlatNaiveStrategy.with_litinski_6x3_dense_unbuffered_widget(10, 18)
    # gates = util.make_gates(obj, lambda x: x % 5)
    # dag_layers, all_gates = util.dag_create(obj, gates)
    # dag_roots = dag_layers[0]

    # orc = ScheduleOrchestrator(dag_roots, wid, strat, True)

    # Test buffered litinski 6x3
    obj = eval(open('../../json.out').read())
    strat, wid = BufferedNaiveStrategy.with_buffered_widget(
        10, 18, 2, factory_factory=MagicStateFactoryRegion.with_litinski_6x3_dense)
    gates = util.make_gates(obj, lambda x: x % 5)
    dag_layers, all_gates = util.dag_create(obj, gates)
    dag_roots = dag_layers[0]

    orc = ScheduleOrchestrator(dag_roots, wid, strat, True)
