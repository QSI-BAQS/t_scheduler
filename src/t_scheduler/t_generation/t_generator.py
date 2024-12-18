from abc import ABC
import numpy as np


class TGenerator(ABC):
    """
    Base T generator object
    """

    def __init__(
        self,
        n_cycles: int,  # Number of cycles to emit
        height: int,  # Height of block
        width: int,  # Width of block
        n_emitted: int = 1,  # Number of T states per emission
        prob: float = 1,  # Probability of generation
        generator=None,  # RNG
        bandwidth=None,  # Number of simultaneous T states extractable
    ):

        if generator is None:
            generator = np.random.default_rng()

        self.n_cycles = n_cycles
        self.height = height
        self.width = width
        self.n_emitted = n_emitted
        self.prob = prob
        self._generator = generator

        if bandwidth is None:
            bandwidth = self.n_emitted
        self.bandwidth = bandwidth

        self._curr_cycle = 0  # Current cycle

    def __call__(self) -> int:
        """
        Calls the update method and emits a number of $T$ states
        """
        return self.update()

    def update(self, prob: bool = True):
        """
        Update the state of the generator
        :: prob : bool :: Are emissions probablistic
        Returns the number of T states produced that cycle
        """
        if self._curr_cycle == self.n_cycles:
            self._curr_cycle = 0
            if prob and self._generator.random() < self.prob:
                return self.n_emitted
            elif not prob:
                return self.n_emitted
            return 0
        self._curr_cycle += 1
        return 0

    def reset(self):
        """
        Triggers a reset on the generator
        """
        self._curr_cycle = 0
