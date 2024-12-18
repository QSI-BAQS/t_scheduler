from abc import ABC
from .t_generator import TGenerator


class TFactory(TGenerator):
    def __init__(self, *args, positions=((0, 0)), layout_position=((0, 0)), **kwargs):

        self.positions = positions
        self.layout_position = (0, 0)

        super().__init__(*args, **kwargs)


class TFactory_Litinski_5x3_15_to_1(TFactory):
    """
    https://arxiv.org/pdf/1808.02892
    Fig 17
    """

    def __init__(
        self, generator=None, p_logical=1 - 1e-4, layout_position=((0, 0))  # RNG
    ):
        super().__init__(
            n_cycles=11,
            positions=((0, 1),),
            n_emitted=1,
            height=5,
            width=3,
            prob=p_logical,
            generator=generator,
            layout_position=layout_position,
        )


class TFactory_Litinski_6x3_20_to_4(TFactory):
    """
    https://arxiv.org/pdf/1808.02892
    Fig 17
    For easier routing we extend patches 5 and 6 to the top boundary

    TODO: Treat the empty regions at the corners as buffers, move patch 4 to the buffer when finished
        for an early reset
    """

    def __init__(
        self, generator=None, p_logical=1 - 1e-4, layout_position=((0, 0))  # RNG
    ):
        super().__init__(
            n_cycles=17,
            positions=((0, 1), (0, 0), (0, 2), (2, 2)),
            n_emitted=1,
            height=6,
            width=3,
            prob=p_logical,
            generator=generator,
            layout_position=layout_position,
        )


class TFactory_Litinski_6x3_20_to_4_dense(TFactory):
    """
    https://arxiv.org/pdf/1808.02892
    Fig 17
    For easier routing we extend patches 5 and 6 to the top boundary
    This version assumes that all Ts are extracted      from the top edge and constraints the bandwidth accordingly
    """

    def __init__(
        self, generator=None, p_logical=1 - 1e-4, layout_position=((0, 0))  # RNG
    ):
        super().__init__(
            n_cycles=17,
            positions=((0, 1), (0, 0), (0, 2), (0, 2)),
            n_emitted=4,
            bandwidth=3,
            height=6,
            width=3,
            prob=p_logical,
            generator=generator,
            layout_position=layout_position,
        )
