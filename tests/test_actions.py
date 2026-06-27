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
