# The Transaction record

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)  # frozen: can't be changed after creation
class Transaction:
    id: str
    date: date
    account: str
    type: str  # "credit" (money in) or "debit" (money out)
    category: str
    amount: float  # always positive; `type` gives the direction

    @property
    def signed_amount(self) -> float:
        return self.amount if self.type == "credit" else -self.amount
