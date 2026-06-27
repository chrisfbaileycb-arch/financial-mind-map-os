"""Tests for CSV transaction import."""

from __future__ import annotations

from src import db
from src.importer import ColumnMapping, import_transactions, parse_csv


def test_parse_single_signed_amount():
    text = "Date,Amount,Description\n2026-01-05,-15.99,NETFLIX\n2026-01-06,2000,PAYROLL\n"
    res = parse_csv(text, ColumnMapping(date="Date", amount="Amount", description="Description"))
    assert res.errors == []
    assert [r.amount for r in res.rows] == [-15.99, 2000.0]
    assert res.rows[0].merchant == "NETFLIX"


def test_parse_debit_credit_columns():
    text = "Date,Debit,Credit\n01/05/2026,15.99,\n01/15/2026,,2000\n"
    res = parse_csv(text, ColumnMapping(date="Date", debit="Debit", credit="Credit"))
    assert [r.amount for r in res.rows] == [-15.99, 2000.0]


def test_flip_sign():
    text = "Date,Amount\n2026-01-05,15.99\n"
    res = parse_csv(text, ColumnMapping(date="Date", amount="Amount", flip_sign=True))
    assert res.rows[0].amount == -15.99


def test_currency_formatting_and_parentheses():
    text = "Date,Amount\n2026-01-05,\"($1,234.50)\"\n"
    res = parse_csv(text, ColumnMapping(date="Date", amount="Amount"))
    assert res.rows[0].amount == -1234.50


def test_multiple_date_formats():
    text = 'Date,Amount\n"Jan 05, 2026",-5\n'
    res = parse_csv(text, ColumnMapping(date="Date", amount="Amount"))
    assert res.rows[0].date == "2026-01-05"


def test_bad_row_collected_not_fatal():
    text = "Date,Amount\n2026-01-05,-5\nnot-a-date,-9\n2026-01-07,-7\n"
    res = parse_csv(text, ColumnMapping(date="Date", amount="Amount"))
    assert len(res.rows) == 2
    assert len(res.errors) == 1
    assert "Row 3" in res.errors[0]


def test_missing_mapped_column_errors():
    text = "Date,Amount\n2026-01-05,-5\n"
    res = parse_csv(text, ColumnMapping(date="Date", amount="Nope"))
    assert res.rows == []
    assert res.errors and "missing" in res.errors[0].lower()


def test_import_persists_and_detects(conn):
    # Six monthly Netflix charges -> should be detected as a subscription.
    lines = ["Date,Amount,Description"]
    for month in range(1, 7):
        lines.append(f"2026-{month:02d}-05,-15.99,NETFLIX.COM")
    text = "\n".join(lines) + "\n"

    summary = import_transactions(
        conn,
        text,
        ColumnMapping(date="Date", amount="Amount", description="Description"),
        account_id="my-checking",
    )
    assert summary["imported"] == 6
    assert summary["skipped"] == 0
    assert summary["detected"] == 1

    txns = db.get_transactions(conn, only_debits=True)
    assert len(txns) == 6
    assert len(db.get_subscriptions(conn)) == 1

    # Import auto-creates the destination account so the map can link it.
    accounts = db.get_accounts(conn)
    assert len(accounts) == 1
    assert accounts[0]["name"] == "my-checking"


def test_import_does_not_clobber_existing_account(conn):
    from src import db as _db

    account_hash = _db.hash_pii("my-checking")
    _db.upsert_account(conn, account_hash, name="My Checking", bucket_type="BUCKET_FREE")
    import_transactions(
        conn,
        "Date,Amount\n2026-01-05,-5\n",
        ColumnMapping(date="Date", amount="Amount"),
        account_id="my-checking",
    )
    acct = db.get_accounts(conn)[0]
    assert acct["name"] == "My Checking"  # preserved
    assert acct["bucket_type"] == "BUCKET_FREE"
