from ..router.transaction import Transaction
from ..region.route_bus import RouteBus

class FullyConnectedRouter:
    '''
        Fully connected router for Ion traps networks
    '''

    def __init__(self, ancillae_queue, factory_queue, bell_queue) -> None:
        self.ancillae_queue = ancillae_queue
        self.t_factory_queue = factory_queue
        self.bell_queue = bell_queue

    def request_transaction(self, transaction_type): 

        return Transaction(path, [])
