from abc import ABC
from t_scheduler.t_generation.t_generator import TGenerator

class TFactory_Litinski_3x6(TGenerator):
    '''
    https://arxiv.org/pdf/1808.02892
    Fig 17
    '''

    def __init__(self,
                 generator=None,  # RNG
                 p_logical=1 - 1e-4
                 ):
        super().__init__(
            n_cycles=35,
            height=3,
            width=6,
            n_emitted=1,
            prob=p_logical,
            generator=generator
        )
