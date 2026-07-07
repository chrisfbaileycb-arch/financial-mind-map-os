"""Tests for the Action Report Loop resolution logic."""

from __future__ import annotations

from datetime import date

import pytest

from src import actions, db
from src.sync.engine import heartbeat


def _items_by_type(conn, report_id, item_type):
    return [i for i in db.get_action_items(conn, report_id) if i["item_type"] == item_type]


def test_approving_cancel_marks_subscription_cancelled(seeded_conn):
    summary = heartbeat(seeded_conn, today=date(2026, 6, 27))
    sub_item = _items_by_type(seeded_conn, summary["report_id"], "SUBSCRIPTION_CANCEL")[0]

    updated = actions.resolve_action_item(seeded_conn, sub_item["id"], "APPROVED")
    assert updated["status"] == "APPROVED"
    assert updated["resolved_at"] is not None

    sub = db.get_action_item(seeded_conn, sub_item["id"])
    target = seeded_conn.execute(
        "SELECT status FROM subscriptions WHERE id = ?", (sub["ref_id"],)
    ).fetchone()
    assert target["status"] == "CANCELLED"


def test_denying_cancel_keeps_subscription_active(seeded_conn):
    summary = heartbeat(seeded_conn, today=date(2026, 6, 27))
    sub_item = _items_by_type(seeded_conn, summary["report_id"], "SUBSCRIPTION_CANCEL")[0]

    actions.resolve_action_item(seeded_conn, sub_item["id"], "DENIED")
    target = seeded_conn.execute(
        "SELECT status FROM subscriptions WHERE id = ?", (sub_item["ref_id"],)
    ).fetchone()
    assert target["status"] == "ACTIVE"


def test_denying_cancel_promotes_subscription_to_bill(seeded_conn):
    summary = heartbeat(seeded_conn, today=date(2026, 6, 27))
    sub_item = _items_by_type(seeded_conn, summary["report_id"], "SUBSCRIPTION_CANCEL")[0]
    sub = db.get_subscription(seeded_conn, sub_item["ref_id"])

    bills_before = len(db.get_bills(seeded_conn, active_only=False))
    actions.resolve_action_item(seeded_conn, sub_item["id"], "DENIED")
    bills_after = db.get_bills(seeded_conn, active_only=False)

    assert len(bills_after) == bills_before + 1
    promoted = db.get_bill_by_merchant(seeded_conn, sub["merchant_hash"])
    assert promoted is not None
    assert promoted["category"] == "subscription"
    assert promoted["amount"] == sub["amount"]


def test_promote_to_bill_is_idempotent(seeded_conn):
    summary = heartbeat(seeded_conn, today=date(2026, 6, 27))
    items = _items_by_type(seeded_conn, summary["report_id"], "SUBSCRIPTION_CANCEL")
    # Deny the same subscription twice (second via a fresh heartbeat's item).
    actions.resolve_action_item(seeded_conn, items[0]["id"], "DENIED")
    merchant = db.get_subscription(seeded_conn, items[0]["ref_id"])["merchant_hash"]

    def count():
        return sum(
            1
            for b in db.get_bills(seeded_conn, active_only=False)
            if b["merchant_hash"] == merchant
        )

    first = count()
    summary2 = heartbeat(seeded_conn, today=date(2026, 6, 27))
    again = _items_by_type(seeded_conn, summary2["report_id"], "SUBSCRIPTION_CANCEL")
    same = next(i for i in again if db.get_subscription(seeded_conn, i["ref_id"])["merchant_hash"] == merchant)
    actions.resolve_action_item(seeded_conn, same["id"], "DENIED")
    assert count() == first  # no duplicate bill


def test_snooze_sets_future_date(seeded_conn):
    summary = heartbeat(seeded_conn, today=date(2026, 6, 27))
    item = db.get_action_items(seeded_conn, summary["report_id"])[0]

    updated = actions.resolve_action_item(
        seeded_conn, item["id"], "SNOOZED", snooze_days=10, today=date(2026, 6, 27)
    )
    assert updated["status"] == "SNOOZED"
    assert updated["snooze_until"] == "2026-07-07"


def test_invalid_resolution_raises(seeded_conn):
    summary = heartbeat(seeded_conn, today=date(2026, 6, 27))
    item = db.get_action_items(seeded_conn, summary["report_id"])[0]
    with pytest.raises(ValueError):
        actions.resolve_action_item(seeded_conn, item["id"], "MAYBE")


def test_unknown_item_raises(seeded_conn):
    with pytest.raises(ValueError):
        actions.resolve_action_item(seeded_conn, 99999, "APPROVED")


def test_resolve_report_resolves_all_pending(seeded_conn):
    summary = heartbeat(seeded_conn, today=date(2026, 6, 27))
    resolved = actions.resolve_report(seeded_conn, summary["report_id"], "SNOOZED")
    assert len(resolved) == summary["total_items"]
    remaining = [
        i
        for i in db.get_action_items(seeded_conn, summary["report_id"])
        if i["status"] == "PENDING"
    ]
    assert remaining == []


def test_approving_price_increase_updates_tracked_bill(seeded_conn):
    # Track Netflix as a bill at the old price, then accept the increase.
    merchant = db.hash_pii("Netflix")
    bill_id = db.insert_bill(
        seeded_conn, merchant, amount=15.99, due_day=15,
        label="Netflix", category="subscription",
    )

    summary = heartbeat(seeded_conn, today=date(2026, 6, 27))
    price_item = _items_by_type(seeded_conn, summary["report_id"], "PRICE_INCREASE")[0]
    assert "15.99" in price_item["description"]
    assert "17.99" in price_item["description"]

    actions.resolve_action_item(seeded_conn, price_item["id"], "APPROVED")
    bill = seeded_conn.execute(
        "SELECT amount FROM bills WHERE id = ?", (bill_id,)
    ).fetchone()
    assert abs(bill["amount"] - 17.99) < 0.01


def test_denying_price_increase_leaves_bill_untouched(seeded_conn):
    merchant = db.hash_pii("Netflix")
    bill_id = db.insert_bill(
        seeded_conn, merchant, amount=15.99, due_day=15,
        label="Netflix", category="subscription",
    )

    summary = heartbeat(seeded_conn, today=date(2026, 6, 27))
    price_item = _items_by_type(seeded_conn, summary["report_id"], "PRICE_INCREASE")[0]

    actions.resolve_action_item(seeded_conn, price_item["id"], "DENIED")
    bill = seeded_conn.execute(
        "SELECT amount FROM bills WHERE id = ?", (bill_id,)
    ).fetchone()
    assert abs(bill["amount"] - 15.99) < 0.01
