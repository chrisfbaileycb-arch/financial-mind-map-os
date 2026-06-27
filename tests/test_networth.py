"""Tests for net-worth summary and balance snapshots."""

from __future__ import annotations

from datetime import date

from src import db
from src.sync.engine import heartbeat


def test_net_worth_summary(conn):
    db.upsert_account(conn, db.hash_pii("a"), "Checking", "BUCKET_TAXABLE", 1000)
    db.upsert_account(conn, db.hash_pii("b"), "401k", "BUCKET_TAX", 5000)
    db.upsert_account(conn, db.hash_pii("c"), "Roth", "BUCKET_FREE", 2000)
    summary = db.net_worth_summary(conn)
    assert summary["total"] == 8000
    assert summary["by_bucket"]["BUCKET_TAX"] == 5000
    assert summary["by_bucket"]["BUCKET_FREE"] == 2000


def test_snapshot_is_one_per_day(conn):
    db.upsert_account(conn, db.hash_pii("a"), "Checking", "BUCKET_TAXABLE", 1000)
    db.record_balance_snapshot(conn, "2026-06-27")
    db.upsert_account(conn, db.hash_pii("a"), "Checking", "BUCKET_TAXABLE", 1500)
    db.record_balance_snapshot(conn, "2026-06-27")  # same day -> replace
    snaps = db.get_balance_snapshots(conn)
    assert len(snaps) == 1
    assert snaps[0]["total"] == 1500


def test_heartbeat_records_snapshot(conn):
    db.upsert_account(conn, db.hash_pii("a"), "Checking", "BUCKET_TAXABLE", 1000)
    heartbeat(conn, today=date(2026, 6, 27))
    snaps = db.get_balance_snapshots(conn)
    assert len(snaps) == 1
    assert snaps[0]["date"] == "2026-06-27"
    assert snaps[0]["total"] == 1000


def test_snapshots_returned_oldest_first(conn):
    db.upsert_account(conn, db.hash_pii("a"), "Checking", "BUCKET_TAXABLE", 1000)
    db.record_balance_snapshot(conn, "2026-04-01")
    db.record_balance_snapshot(conn, "2026-05-01")
    db.record_balance_snapshot(conn, "2026-06-01")
    dates = [s["date"] for s in db.get_balance_snapshots(conn)]
    assert dates == ["2026-04-01", "2026-05-01", "2026-06-01"]
