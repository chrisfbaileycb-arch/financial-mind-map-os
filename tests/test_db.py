"""Tests for the database layer: hashing, tokenization, schema and repository."""

from __future__ import annotations

from src import config, db


def test_hash_pii_is_deterministic_and_salted():
    a = db.hash_pii("alice@example.com")
    b = db.hash_pii("alice@example.com")
    assert a == b
    assert a != db.hash_pii("bob@example.com")
    assert len(a) == 64  # SHA-256 hex digest
    assert db.hash_pii("") == ""


def test_hash_pii_uses_configured_salt(monkeypatch):
    base = db.hash_pii("secret")
    monkeypatch.setattr(config, "PII_SALT", "a_different_salt")
    assert db.hash_pii("secret") != base


def test_tokenize_strips_digits_and_short_words():
    tokens = db.tokenize_description("NETFLIX.COM 4567 a")
    assert "netflix" in tokens
    assert "com" in tokens
    assert "4567" not in tokens
    assert "a" not in tokens  # too short


def test_migrate_creates_expected_tables(conn):
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    tables = {r["name"] for r in rows}
    for expected in {
        "transactions",
        "subscriptions",
        "household_members",
        "accounts",
        "paycheck_schedules",
        "bills",
        "action_reports",
        "action_items",
        "sync_log",
    }:
        assert expected in tables


def test_migrate_is_idempotent(conn):
    # Running migrate again on an existing connection must not raise.
    db.migrate(conn)
    db.migrate(conn)


def test_insert_and_query_transaction(conn):
    member = db.hash_pii("m1")
    db.insert_transaction(
        conn,
        account_hash=db.hash_pii("acct"),
        amount=-12.50,
        date="2026-06-01",
        merchant_hash=db.hash_pii("Coffee"),
        member_hash=member,
    )
    debits = db.get_transactions(conn, only_debits=True)
    assert len(debits) == 1
    assert debits[0]["amount"] == -12.50

    by_member = db.get_transactions(conn, member_hash=member)
    assert len(by_member) == 1
    since = db.get_transactions(conn, since="2026-07-01")
    assert since == []


def test_upsert_subscription_is_unique_per_merchant(conn):
    merchant = db.hash_pii("Netflix")
    db.upsert_subscription(conn, merchant, 15.99, frequency="monthly", occurrences=3)
    db.upsert_subscription(conn, merchant, 17.99, frequency="monthly", occurrences=4)
    subs = db.get_subscriptions(conn)
    assert len(subs) == 1
    assert subs[0]["amount"] == 17.99
    assert subs[0]["occurrences"] == 4


def test_action_report_and_items(conn):
    report_id = db.create_action_report(conn, "HEARTBEAT", "test")
    db.add_action_item(
        conn, report_id, "BILL_PAYMENT", "Rent due", amount=1400, urgency="CRITICAL"
    )
    db.add_action_item(
        conn, report_id, "SUBSCRIPTION_CANCEL", "Netflix", amount=15.99, urgency="NORMAL"
    )
    items = db.get_action_items(conn, report_id)
    assert len(items) == 2
    # Critical items are ordered first.
    assert items[0]["urgency"] == "CRITICAL"
