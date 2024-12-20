

class CoordinateAdapter:
    '''
    Maps from above_range to below range.

    Example:

    0123456789
      -------   <- above_range = [2, 8]
        ----    <- below_range = [4, 7]
    
    above_to_below(2) -> global 4 -> below 0
    '''
    def __init__(self, above_range, below_range) -> None:
        self.above_range = above_range
        self.below_range = below_range
    
    @staticmethod
    def clamp(val, range_low, range_high):
        return max(range_low, min(val, range_high))

    def above_to_below(self, above_index):
        global_pos = self.above_range[0] + above_index
        global_pos = self.clamp(global_pos, *self.below_range)
        below_index = global_pos - self.below_range[0]
        return below_index
    
    def below_to_above(self, below_index):
        global_pos = self.below_range[0] + below_index
        global_pos = self.clamp(global_pos, *self.above_range)
        above_index = global_pos - self.above_range[0]
        return above_index

    def above_to_global(self, above_index):
        global_pos = self.above_range[0] + above_index
        return global_pos
    
    def below_to_global(self, below_index):
        global_pos = self.below_range[0] + below_index
        return global_pos

