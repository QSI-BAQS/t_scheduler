import unittest
from itertools import chain
from t_scheduler import gate, widget, scheduler, tree_scheduler, vertical_scheduler


class StaticBufferTest(unittest.TestCase): 
    def test_end_to_end_lookback_vertical(self):
        gate_layers = [
            [*chain(*(([x] * 8) for x in [5, 0, 6, 8, 7]))],
        ]
        gate_layers = [[gate.T_Gate(t, 2, 3) for t in layer] for layer in gate_layers]

        wid = widget.Widget.prefillec_buffer_widget(20, 5)
        sched = vertical_scheduler.VerticalScheduler(
            gate_layers,
            wid,
            rotation_strategy=scheduler.RotationStrategy.LOOKBACK
        )
        sched.schedule()

    def test_end_to_end_reject_vertical(self):
        gate_layers = [
            [*chain(*(([x] * 8) for x in [5, 0, 6, 8, 7]))],
        ]
        gate_layers = [[gate.T_Gate(t, 2, 3) for t in layer] for layer in gate_layers]

        wid = widget.Widget.prefillec_buffer_widget(20, 5)
        sched = vertical_scheduler.VerticalScheduler(
            gate_layers,
            wid,
            rotation_strategy=scheduler.RotationStrategy.REJECT
        )
        try:
            # This should fail
            sched.schedule()
            raise Exception()
        except scheduler.SchedulerException:
            pass

    def test_end_to_end_inject_vertical(self):
        gate_layers = [
            [*chain(*(([x] * 8) for x in [5, 0, 6, 8, 7]))],
        ]
        gate_layers = [[gate.T_Gate(t, 2, 3) for t in layer] for layer in gate_layers]

        wid = widget.Widget.prefillec_buffer_widget(20, 5)
        sched = vertical_scheduler.VerticalScheduler(
            gate_layers,
            wid,
            rotation_strategy=scheduler.RotationStrategy.INJECT
        )
        
        sched.schedule()

    def test_end_to_end_backprop_vertical(self):
        gate_layers = [
            [*chain(*(([x] * 8) for x in [5, 0, 6, 8, 7]))],
        ]
        gate_layers = [[gate.T_Gate(t, 2, 3) for t in layer] for layer in gate_layers]

        wid = widget.Widget.prefillec_buffer_widget(20, 5)
        sched = vertical_scheduler.VerticalScheduler(
            gate_layers,
            wid
        )

        sched.schedule()


    def test_end_to_end_2(self):
        gate_layers = [
            [*chain(*(([x] * 10) for x in [5, 0, 6, 8, 7]))],
        ]
        gate_layers = [[gate.T_Gate(t, 1, 1) for t in layer] for layer in gate_layers]

        wid = widget.Widget.chessboard_widget(20, 5)
        sched = tree_scheduler.TreeScheduler(gate_layers, wid)
        sched.schedule()


    def test_end_to_end_3(self):
        gate_layers = [
            [*chain(*(([x] * 100) for x in [6, 7, 9]))],
        ]
        gate_layers = [[gate.T_Gate(t, 1, 1) for t in layer] for layer in gate_layers]

        wid = widget.Widget.chessboard_widget(40, 20)
        sched = tree_scheduler.TreeScheduler(gate_layers, wid)
        sched.schedule()

     


if __name__ == '__main__':
    unittest.main()
