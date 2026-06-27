"""Tests for transaction edit/split/categorize and spending aggregation."""

from __future__ import annotations

from src import db


def _txn(conn, amount, date, category=None):
    return db.insert_transaction(
        conn,
        account_hash=db.hash_pii("acct"),
        amount=amount,
        date=date,
        merchant_hash=db.hash_pii("Store"),
        category=category,
    )


def test_update_transaction_category(conn):
    txn_id = _txn(conn, -50.0, "2026-06-10")
    db.update_transaction(conn, txn_id, category="groceries")
    assert db.get_transaction(conn, txn_id)["category"] == "groceries"


def test_split_transaction(conn):
    txn_id = _txn(conn, -100.0, "2026-06-10")
    new_ids = db.split_transaction(
        conn,
        txn_id,
        [
            {"amount": -60.0, "category": "groceries"},
            {"amount": -40.0, "category": "household"},
        ],
    )
    assert len(new_ids) == 2
    assert db.get_transaction(conn, txn_id) is None  # parent removed
    txns = db.get_transactions(conn)
    cats = {t["category"] for t in txns}
    assert cats == {"groceries", "household"}
    assert round(sum(t["amount"] for t in txns), 2) == -100.0


def test_spending_by_month(conn):
    _txn(conn, -100.0, "2026-05-10")
    _txn(conn, -50.0, "2026-05-20")
    _txn(conn, -30.0, "2026-06-01")
    _txn(conn, 2000.0, "2026-06-02")  # income, excluded
    rows = {r["month"]: r["spent"] for r in db.spending_by_month(conn)}
    assert rows["2026-05"] == 150.0
    assert rows["2026-06"] == 30.0


def test_spending_by_category(conn):
    _txn(conn, -100.0, "2026-06-10", category="groceries")
    _txn(conn, -40.0, "2026-06-11", category="groceries")
    _txn(conn, -25.0, "2026-06-12")  # uncategorized
    rows = {r["category"]: r["spent"] for r in db.spending_by_category(conn)}
    assert rows["groceries"] == 140.0
    assert rows["uncategorized"] == 25.0


def test_category_rules_apply_to_siblings(conn):
    merchant = db.hash_pii("Coffee Co")
    for day in ("2026-06-01", "2026-06-08", "2026-06-15"):
        db.insert_transaction(
            conn, account_hash=db.hash_pii("a"), amount=-5, date=day, merchant_hash=merchant
        )
    db.upsert_category_rule(conn, merchant, "coffee")
    applied = db.apply_category_rules(conn)
    assert applied == 3
    cats = {t["category"] for t in db.get_transactions(conn)}
    assert cats == {"coffee"}


def test_category_rules_do_not_overwrite_existing(conn):
    merchant = db.hash_pii("Shop")
    db.insert_transaction(
        conn, account_hash=db.hash_pii("a"), amount=-5, date="2026-06-01",
        merchant_hash=merchant, category="manual",
    )
    db.upsert_category_rule(conn, merchant, "auto")
    db.apply_category_rules(conn)
    assert db.get_transactions(conn)[0]["category"] == "manual"  # untouched


def test_update_bill(conn):
    bill_id = db.insert_bill(conn, db.hash_pii("Rent Co"), amount=1400, due_day=1, label="Rent")
    db.update_bill(conn, bill_id, amount=1500, auto_pay=True)
    bill = db.get_bill(conn, bill_id)
    assert bill["amount"] == 1500
    assert bill["auto_pay"] == 1


def test_update_account(conn):
    h = db.hash_pii("acct")
    db.upsert_account(conn, h, name="Old", bucket_type="BUCKET_TAXABLE", balance=100)
    db.update_account(conn, h, name="New", balance=250)
    acct = db.get_accounts(conn)[0]
    assert acct["name"] == "New"
    assert acct["balance"] == 250
    assert acct["bucket_type"] == "BUCKET_TAXABLE"  # unchanged
