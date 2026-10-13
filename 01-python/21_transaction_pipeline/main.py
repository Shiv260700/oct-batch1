# Guided practice: a transaction processing pipeline
#
#   transactions.csv -> read_rows -> valid_transactions -> filters -> summarize
#
# Every step is a generator, so only one row is in memory at a time.
#
# Run:   python3 play-with-python/21_transaction_pipeline/main.py
# Test:  python3 -m pytest play-with-python/21_transaction_pipeline -v

import json
from pathlib import Path

from pipeline import by_account, read_rows, summarize, timer, valid_transactions

DATA = Path(__file__).parent / "transactions.csv"


@timer
def report(account=None):
    errors: list[str] = []
    transactions = valid_transactions(read_rows(DATA), errors)
    if account:
        transactions = by_account(transactions, account)
    summary = summarize(transactions)  # the pipeline only runs here
    return summary, errors


def main():
    summary, errors = report()
    print(json.dumps(summary, indent=2))

    print(f"\nSkipped {len(errors)} invalid rows:")
    for error in errors:
        print(f"  - {error}")

    acc_summary, _ = report(account="ACC-2")
    print("\nACC-2 net:", acc_summary["net"])


if __name__ == "__main__":
    main()
