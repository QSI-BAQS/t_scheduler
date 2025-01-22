import json
import unittest
from itertools import chain
import math

import numpy as np
import timeit

from t_scheduler.base import * 
from t_scheduler.router import * 
from t_scheduler.region import * 


def rng_generator(fn):
    def _wrap(*args, generator=None, **kwargs):
        if generator is None:
            generator = np.random.default_rng()
        return fn(*args, generator=generator, **kwargs) 
    return _wrap

@rng_generator
def benchmark_single_register(
    n_qubits : int,
    n_cycles: int,
    load: float = 1,
    delay = 2, # Locking delay
    generator=None):

    region = SingleRowRegisterRegion(n_qubits * 2)
    router = BaselineRegisterRouter(region) 
    gate_load = math.ceil(load * n_qubits) 
    targs = list(range(n_qubits))

    transactions = {}
    dropped_gates = []

    for i in range(n_cycles):

        updated = {}
        for i in transactions: 
            transactions[i] += 1
            if transactions[i] >= delay:
                i.unlock()
            else:
                updated[i] = transactions[i]
        transactions = updated

       
        # New gates 
        updated = []
        targs = list(generator.choice(targs, gate_load, replace=False))
        for targ in dropped_gates + targs: 
            transaction = router._request_transaction(targ)          
            if transaction is not None:
                transaction.lock_move(None)
                transactions[transaction] = 0
            else:
                updated.append(targ)
        dropped_gates = updated

    while len(dropped_gates) > 0:

        updated = {}
        for i in transactions: 
            transactions[i] += 1
            if transactions[i] >= delay:
                i.unlock()
            else:
                updated[i] = transactions[i]
        transactions = updated

       
        # New gates 
        updated = []
        for targ in dropped_gates: 
            transaction = router._request_transaction(targ)          
            if transaction is not None:
                transaction.lock_move(None)
                transactions[transaction] = 0
            else:
                updated.append(targ)
        dropped_gates = updated

    return


def main():
    print("Single Register",  timeit.timeit("benchmark_single_register(100000, 1)", number=10, setup='from __main__ import benchmark_single_register; gc.enable()'))

if __name__ == '__main__':
    main()
