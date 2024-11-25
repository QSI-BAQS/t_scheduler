import unittest
from itertools import chain
from t_scheduler import util, scheduler


class StaticBufferTest(unittest.TestCase): 
    def test_end_to_end_lookback_vertical(self):
        gate_layers = [
            [*chain(*(([x] * 8) for x in [5, 0, 6, 8, 7]))],
        ]
        gate_layers = [[util.T_Gate(t, 2, 3) for t in layer] for layer in gate_layers]

        wid = util.Widget.default_widget(20, 5)
        sched = scheduler.VerticalScheduler(
            gate_layers,
            wid,
            rotation_strategy=scheduler.RotationStrategy.LOOKBACK
        )
        sched.schedule()

    def test_end_to_end_reject_vertical(self):
        gate_layers = [
            [*chain(*(([x] * 8) for x in [5, 0, 6, 8, 7]))],
        ]
        gate_layers = [[util.T_Gate(t, 2, 3) for t in layer] for layer in gate_layers]

        wid = util.Widget.default_widget(20, 5)
        sched = scheduler.VerticalScheduler(
            gate_layers,
            wid,
            rotation_strategy=scheduler.RotationStrategy.REJECT
        )
        try:
            # This should fail
            sched.schedule()
            raise Exception()
        except:
            pass

    def test_end_to_end_inject_vertical(self):
        gate_layers = [
            [*chain(*(([x] * 8) for x in [5, 0, 6, 8, 7]))],
        ]
        gate_layers = [[util.T_Gate(t, 2, 3) for t in layer] for layer in gate_layers]

        wid = util.Widget.default_widget(20, 5)
        sched = scheduler.VerticalScheduler(
            gate_layers,
            wid,
            rotation_strategy=scheduler.RotationStrategy.INJECT
        )
        try:
            # This should fail
            sched.schedule()
            raise Exception()
        except:
            pass

    def test_end_to_end_backprop_vertical(self):
        gate_layers = [
            [*chain(*(([x] * 8) for x in [5, 0, 6, 8, 7]))],
        ]
        gate_layers = [[util.T_Gate(t, 2, 3) for t in layer] for layer in gate_layers]

        wid = util.Widget.default_widget(20, 5)
        sched = scheduler.VerticalScheduler(
            gate_layers,
            wid
        )
        try:
            # This should fail
            sched.schedule()
            raise Exception()
        except:
            pass



    def test_end_to_end_2(self):
        gate_layers = [
            [*chain(*(([x] * 10) for x in [5, 0, 6, 8, 7]))],
        ]
        gate_layers = [[util.T_Gate(t, 1, 1) for t in layer] for layer in gate_layers]

        wid = util.Widget.chessboard_widget(20, 5)
        sched = scheduler.TreeScheduler(gate_layers, wid)
        sched.schedule()


    def test_end_to_end_3(self):
        gate_layers = [
            [*chain(*(([x] * 100) for x in [6, 7, 9]))],
        ]
        gate_layers = [[util.T_Gate(t, 1, 1) for t in layer] for layer in gate_layers]

        wid = util.Widget.chessboard_widget(40, 20)
        sched = scheduler.TreeScheduler(gate_layers, wid)
        sched.schedule()

     


if __name__ == '__main__':
    unittest.main()
