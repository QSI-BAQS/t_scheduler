from enum import Enum, IntEnum
from .transaction import Transaction, TransactionList

class ResponseStatus(IntEnum):
    FAILED = 0
    CHECK_DOWNSTREAM = 1
    SUCCESS = 2

class Response:
    status: ResponseStatus
    transaction: Transaction | TransactionList | None

    def __init__(self, status=ResponseStatus.FAILED, transaction=None) -> None:
        self.status = status
        self.transaction = transaction
        if transaction:
            self.downstream_patch = transaction.move_patches[0]
            self.upstream_patch = transaction.move_patches[-1]
