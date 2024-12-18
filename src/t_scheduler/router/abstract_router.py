from abc import ABC

class AbstractRouter(ABC):
    def request_transaction(self, *args, **kwargs):
        '''
        Request a transaction from the router with specified args.

        Overridden by implementers.
        '''
        raise NotImplementedError

    @staticmethod
    def range_directed(a, b):
        if a <= b:
            return range(a, b + 1)
        else:
            return range(a, b - 1, -1)
