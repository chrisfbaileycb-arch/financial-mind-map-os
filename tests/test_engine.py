"""Tests for the wired sync engine and Action Report Loop."""

from __future__ import annotations

from datetime import date

from src import db
from src.sync.engine import heartbeat


def test_heartbeat_produces_action_report(seeded_conn):
    summary = heartbeat(seeded_conn, today=date(2026, 6, 27))

    assert summary["subscriptions"] == 3
    assert summary["price_increases"] == 1  # seeded Netflix hike
    assert summary["bills"] == 3  # internet is auto-pay and excluded
    assert summary["household"] == 1
    assert summary["total_items"] == 8

    items = db.get_action_items(seeded_conn, summary["report_id"])
    assert len(items) == 8
    item_types = {i["item_type"] for i in items}
    assert item_types == {
        "SUBSCRIPTION_CANCEL",
        "PRICE_INCREASE",
        "BILL_PAYMENT",
        "SPENDING_ALERT",
    }


def test_heartbeat_logs_sync(seeded_conn):
    heartbeat(seeded_conn, today=date(2026, 6, 27))
    rows = list(seeded_conn.execute("SELECT * FROM sync_log ORDER BY id DESC LIMIT 1"))
    assert rows[0]["status"] == "COMPLETE"
    assert rows[0]["items_processed"] == 8


def test_heartbeat_on_empty_db_is_safe(conn):
    summary = heartbeat(conn, today=date(2026, 6, 27))
    assert summary["total_items"] == 0


def test_subscriptions_not_duplicated_across_heartbeats(seeded_conn):
    heartbeat(seeded_conn, today=date(2026, 6, 27))
    heartbeat(seeded_conn, today=date(2026, 6, 27))
    # Unique-per-merchant constraint keeps the subscriptions table stable.
    assert len(db.get_subscriptions(seeded_conn)) == 3
