# Step 4: summarize (one pass, so it works on a generator)

from collections import defaultdict
from typing import Iterable, Optional

from .models import Transaction


def summarize(transactions: Iterable[Transaction]) -> dict:
    count = 0
    credits = 0.0
    debits = 0.0
    spend_by_category: dict[str, float] = defaultdict(float)
    largest_debit: Optional[Transaction] = None

    for tx in transactions:
        count += 1
        if tx.type == "credit":
            credits += tx.amount
        else:
            debits += tx.amount
            spend_by_category[tx.category] += tx.amount
            if largest_debit is None or tx.amount > largest_debit.amount:
                largest_debit = tx

    return {
        "count": count,
        "total_credits": round(credits, 2),
        "total_debits": round(debits, 2),
        "net": round(credits - debits, 2),
        "spend_by_category": dict(
            sorted(spend_by_category.items(), key=lambda kv: kv[1], reverse=True)
        ),
        "largest_debit": largest_debit.id if largest_debit else None,
    }
