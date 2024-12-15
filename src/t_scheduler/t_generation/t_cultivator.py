from abc import ABC
from t_scheduler.t_generation.t_generator import TGenerator

class TCultivator(TGenerator):
    '''
        Base T generator object
    '''
    STAGE_CYCLES = 0
    STAGE_PROB = 1
    stages = [
        [4, 0.7],  # Injection
        [5, 0.25],  # Cultivation
        [5, 0.3],  # Escape
        [10, 1 / 6]  # Gap
    ]

    def __init__(self,
                 generator=None  # RNG
                 ):
        super().__init__(
            n_cycles=22,
            height=1,
            width=1,
            n_emitted=1,
            generator=generator
        )
        self.curr_stage = 0
        self.n_stages = 4

    def __call__(self) -> int:
        '''
            Calls the update method and emits a number of $T$ states
        '''
        return self.update()

    def update(self, prob: bool = True):
        '''
            Update the state of the generator 
            :: prob : bool :: Are emissions probablistic   
            Returns the number of T states produced that cycle
        '''
        if self._curr_cycle == self.stages[self.curr_stage][self.STAGE_CYCLES]:
            self._curr_cycle = 0
            # Go to next stage
            if prob and self._generator.random() < self.stages[self.curr_stage][self.STAGE_PROB]:
                self.curr_stage += 1
                if self.curr_stage == self.n_stages:
                    self.curr_stage = 0
                    return self.n_emitted
            elif not prob:
                if self.curr_stage == self.n_stages:
                    self.curr_stage = 0
                    return self.n_emitted

                return self.n_emitted
            return 0
        self._curr_cycle += 1
        return 0

    def reset(self):
        '''
            Resets the cultivator 
        '''
        self._curr_cycle = 0
        self.curr_stage = 0
