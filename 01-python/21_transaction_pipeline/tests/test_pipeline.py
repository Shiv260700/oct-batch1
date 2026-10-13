# Tests for the transaction pipeline

import types
from datetime import date

import pytest

from pipeline import (
    InvalidTransaction, Transaction, by_account, by_type, min_amount,
    parse_transaction, read_rows, summarize, valid_transactions,
)


def make_row(**overrides):
    row = {
        "id": "T1", "date": "2026-10-01", "account": "ACC-1",
        "type": "debit", "category": "Food", "amount": "100.50",
    }
    row.update(overrides)
    return row


@pytest.fixture
def transactions():
    return [
        Transaction("T1", date(2026, 10, 1), "ACC-1", "credit", "salary", 1000.0),
        Transaction("T2", date(2026, 10, 2), "ACC-1", "debit", "food", 200.0),
        Transaction("T3", date(2026, 10, 3), "ACC-2", "debit", "travel", 500.0),
        Transaction("T4", date(2026, 10, 4), "ACC-2", "debit", "food", 50.0),
    ]


# -----------------------------------------------------
# validate
# -----------------------------------------------------

def test_parse_valid_row():
    tx = parse_transaction(make_row())
    assert tx.id == "T1"
    assert tx.date == date(2026, 10, 1)
    assert tx.amount == 100.50
    assert tx.category == "food"  # lowercased
    assert tx.signed_amount == -100.50


@pytest.mark.parametrize("overrides, message", [
    ({"id": ""}, "missing id"),
    ({"date": "2026-13-01"}, "bad date"),
    ({"type": "transfer"}, "unknown type"),
    ({"amount": "abc"}, "bad amount"),
    ({"amount": None}, "bad amount"),
    ({"amount": "-5"}, "must be positive"),
    ({"amount": "0"}, "must be positive"),
])
def test_parse_invalid_row(overrides, message):
    with pytest.raises(InvalidTransaction, match=message):
        parse_transaction(make_row(**overrides))


def test_valid_transactions_skips_and_records_errors():
    rows = [make_row(id="T1"), make_row(id="T2", amount="x"), make_row(id="T3")]
    errors = []
    result = list(valid_transactions(rows, errors))
    assert [tx.id for tx in result] == ["T1", "T3"]
    assert errors == ["T2: bad amount 'x'"]


def test_valid_transactions_is_lazy():
    def rows():
        yield make_row(id="T1")
        raise AssertionError("read too far")  # fails if the generator over-reads

    gen = valid_transactions(rows())
    assert isinstance(gen, types.GeneratorType)
    assert next(gen).id == "T1"  # only the first row was consumed


# -----------------------------------------------------
# read
# -----------------------------------------------------

def test_read_rows(tmp_path):
    file = tmp_path / "tx.csv"
    file.write_text("id,amount\nT1,10\nT2,20\n")
    assert list(read_rows(file)) == [
        {"id": "T1", "amount": "10"},
        {"id": "T2", "amount": "20"},
    ]


# -----------------------------------------------------
# filter
# -----------------------------------------------------

def test_filters(transactions):
    assert [t.id for t in by_type(transactions, "debit")] == ["T2", "T3", "T4"]
    assert [t.id for t in by_account(transactions, "ACC-2")] == ["T3", "T4"]
    assert [t.id for t in min_amount(transactions, 200)] == ["T1", "T2", "T3"]


def test_filters_chain(transactions):
    result = min_amount(by_type(transactions, "debit"), 100)
    assert [t.id for t in result] == ["T2", "T3"]


# -----------------------------------------------------
# summarize
# -----------------------------------------------------

def test_summarize(transactions):
    s = summarize(transactions)
    assert s["count"] == 4
    assert s["total_credits"] == 1000.0
    assert s["total_debits"] == 750.0
    assert s["net"] == 250.0
    assert s["spend_by_category"] == {"travel": 500.0, "food": 250.0}
    assert s["largest_debit"] == "T3"


def test_summarize_empty():
    s = summarize([])
    assert s["count"] == 0
    assert s["net"] == 0
    assert s["largest_debit"] is None


# -----------------------------------------------------
# end to end
# -----------------------------------------------------

def test_full_pipeline_on_sample_file():
    from pathlib import Path

    data = Path(__file__).parent.parent / "transactions.csv"
    errors = []
    s = summarize(valid_transactions(read_rows(data), errors))
    assert s["count"] == 9
    assert len(errors) == 6
