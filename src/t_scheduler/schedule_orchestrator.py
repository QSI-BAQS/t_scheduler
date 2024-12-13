from collections import defaultdict, deque

from t_scheduler.strategy.tree_strategy import TreeRoutingStrategy
from t_scheduler.strategy.vertical_strategy import VerticalRoutingStrategy
from t_scheduler.widget.widget import Widget


class ScheduleOrchestrator:
    def __init__(
        self,
        gate_dag_roots,
        widget,
        strategy,
        debug: bool = False,
    ):
        self.widget: Widget = widget
        self.strategy: VerticalRoutingStrategy = strategy

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


        # Print widget board state
        if self.debug:
            print(self.widget.to_str_output_dedup(),end='')


        for gate in self.active:
            gate.tick()

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

if __name__ == '__main__':
    import t_scheduler.util as util
    from t_scheduler.gate import T_Gate
    from itertools import chain
    # strat, wid = VerticalRoutingStrategy.with_prefilled_buffer_widget(20, 5)
    # gate_layers = [
    #         [*chain(*(([x] * 8) for x in [5, 0, 6, 8, 7]))],
    #     ]
    # gate_layers = [[T_Gate(t, 2, 3) for t in layer] for layer in gate_layers]

    # orc = ScheduleOrchestrator(gate_layers[0], wid, strat, True)

    # strat, wid = VerticalRoutingStrategy.with_prefilled_buffer_widget(26, 5)
    # obj = util.toffoli_example_input()
    # dag_layers, all_gates = util.dag_create(obj)
    # dag_roots = dag_layers[0]

    # orc = ScheduleOrchestrator(dag_roots, wid, strat, True)

    obj = eval(open('../../json.out').read())
    strat, wid = TreeRoutingStrategy.with_prefilled_buffer_widget(10, 10)
    gates = util.make_gates(obj, lambda x: x % 5)
    dag_layers, all_gates = util.dag_create(obj, gates)
    dag_roots = dag_layers[0]

    orc = ScheduleOrchestrator(dag_roots, wid, strat, True)