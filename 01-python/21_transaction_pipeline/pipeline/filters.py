# Step 3: filter (each one is a lazy generator, so they chain cheaply)

from typing import Iterable, Iterator

from .models import Transaction


def by_type(transactions: Iterable[Transaction], tx_type: str) -> Iterator[Transaction]:
    return (tx for tx in transactions if tx.type == tx_type)


def by_account(transactions: Iterable[Transaction], account: str) -> Iterator[Transaction]:
    return (tx for tx in transactions if tx.account == account)


def min_amount(transactions: Iterable[Transaction], threshold: float) -> Iterator[Transaction]:
    return (tx for tx in transactions if tx.amount >= threshold)
