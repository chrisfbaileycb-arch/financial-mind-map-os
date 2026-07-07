"""Tests for keyword auto-categorization."""

from __future__ import annotations

from datetime import date

from src import db
from src.categorize import categorize_tokens, run_auto_categorization
from src.sync.engine import heartbeat


def test_categorize_tokens_matches_keywords():
    assert categorize_tokens("netflix com") == "entertainment"
    assert categorize_tokens("grocery mart") == "groceries"
    assert categorize_tokens("shell oil") == "transport"
    assert categorize_tokens("city gym") == "health"
    assert categorize_tokens("home hardware") == "home"


def test_categorize_tokens_no_match_returns_none():
    assert categorize_tokens("mystery merchant") is None
    assert categorize_tokens("") is None
    assert categorize_tokens(None) is None


def test_run_auto_categorization_fills_blanks_only(conn):
    account = db.hash_pii("acct")
    blank_id = db.insert_transaction(
        conn, account_hash=account, amount=-15.99, date="2026-06-01",
        merchant_hash=db.hash_pii("Netflix"), description_tokens="netflix com",
    )
    manual_id = db.insert_transaction(
        conn, account_hash=account, amount=-20.0, date="2026-06-02",
        merchant_hash=db.hash_pii("Netflix"), description_tokens="netflix com",
        category="gifts",  # user-set; must never be overwritten
    )

    updated = run_auto_categorization(conn)
    assert updated == 1

    rows = {
        r["id"]: r["category"]
        for r in conn.execute("SELECT id, category FROM transactions")
    }
    assert rows[blank_id] == "entertainment"
    assert rows[manual_id] == "gifts"


def test_learned_merchant_rules_beat_keyword_defaults(conn):
    account = db.hash_pii("acct")
    merchant = db.hash_pii("Netflix")
    txn_id = db.insert_transaction(
        conn, account_hash=account, amount=-15.99, date="2026-06-01",
        merchant_hash=merchant, description_tokens="netflix com",
    )
    # The user previously categorized this merchant as 'family'.
    db.upsert_category_rule(conn, merchant, "family")

    # Callers apply learned rules first, then keyword defaults.
    db.apply_category_rules(conn)
    run_auto_categorization(conn)

    row = conn.execute(
        "SELECT category FROM transactions WHERE id = ?", (txn_id,)
    ).fetchone()
    assert row["category"] == "family"


def test_heartbeat_categorizes_seeded_transactions(seeded_conn):
    summary = heartbeat(seeded_conn, today=date(2026, 6, 27))
    assert summary["categorized"] > 0

    # The known seeded merchants are now categorized.
    spend = {
        r["category"]: r["spent"] for r in db.spending_by_category(seeded_conn)
    }
    assert "entertainment" in spend  # netflix + spotify
    assert "health" in spend  # city gym
    assert "groceries" in spend  # grocery mart
    assert "transport" in spend  # shell oil
