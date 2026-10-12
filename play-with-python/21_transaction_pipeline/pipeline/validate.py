# Step 2: validate (turn raw text rows into Transaction objects)

from datetime import date
from typing import Iterable, Iterator, Optional

from .models import Transaction

VALID_TYPES = {"credit", "debit"}


class InvalidTransaction(ValueError):
    """A row that can't be turned into a Transaction."""


def _field(row: dict, name: str) -> str:
    return (row.get(name) or "").strip()  # missing cells come back as None


def parse_transaction(row: dict) -> Transaction:
    tx_id = _field(row, "id")
    if not tx_id:
        raise InvalidTransaction("missing id")

    try:
        tx_date = date.fromisoformat(_field(row, "date"))
    except ValueError:
        raise InvalidTransaction(f"{tx_id}: bad date {row.get('date')!r}") from None

    tx_type = _field(row, "type").lower()
    if tx_type not in VALID_TYPES:
        raise InvalidTransaction(f"{tx_id}: unknown type {tx_type!r}")

    try:
        amount = float(_field(row, "amount"))
    except ValueError:
        raise InvalidTransaction(f"{tx_id}: bad amount {row.get('amount')!r}") from None
    if amount <= 0:
        raise InvalidTransaction(f"{tx_id}: amount must be positive, got {amount}")

    return Transaction(
        id=tx_id,
        date=tx_date,
        account=_field(row, "account"),
        type=tx_type,
        category=_field(row, "category").lower() or "uncategorized",
        amount=amount,
    )


def valid_transactions(
    rows: Iterable[dict], errors: Optional[list[str]] = None
) -> Iterator[Transaction]:
    """Yield good transactions; skip bad rows, recording why in `errors`."""
    for row in rows:
        try:
            yield parse_transaction(row)
        except InvalidTransaction as e:
            if errors is not None:
                errors.append(str(e))
