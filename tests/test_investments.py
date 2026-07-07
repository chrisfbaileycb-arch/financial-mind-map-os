"""Tests for holdings, market-data refresh, and net worth integration."""

from __future__ import annotations

from datetime import date

from src import db
from src.investments.market_data import refresh_holding_prices, resolve_provider
from src.sync.engine import heartbeat, refresh_portfolio


def _account(conn, name="Brokerage", bucket="BUCKET_TAXABLE", balance=1000.0):
    account_hash = db.hash_pii(name)
    db.upsert_account(conn, account_hash, name, bucket, balance)
    return account_hash


def test_upsert_holding_is_unique_per_account_and_symbol(conn):
    acct = _account(conn)
    first = db.upsert_holding(conn, acct, "vti", 10, cost_basis=200.0)
    second = db.upsert_holding(conn, acct, "VTI", 12, cost_basis=205.0)
    assert first == second  # same row, symbol normalized to uppercase

    holdings = db.get_holdings(conn)
    assert len(holdings) == 1
    assert holdings[0]["symbol"] == "VTI"
    assert holdings[0]["quantity"] == 12
    assert holdings[0]["cost_basis"] == 205.0


def test_net_worth_includes_holdings_market_value(conn):
    acct = _account(conn, balance=1000.0)
    db.upsert_holding(conn, acct, "VTI", 10, cost_basis=200.0, last_price=225.0)

    summary = db.net_worth_summary(conn)
    # 1000 cash + 10 * 225 market value
    assert summary["total"] == 3250.0
    assert summary["by_bucket"]["BUCKET_TAXABLE"] == 3250.0


def test_holdings_without_price_fall_back_to_cost_basis(conn):
    acct = _account(conn, balance=0.0)
    db.upsert_holding(conn, acct, "VOO", 5, cost_basis=400.0)
    assert db.net_worth_summary(conn)["total"] == 2000.0


def test_refresh_prices_updates_all_accounts_holding_symbol(conn):
    a1 = _account(conn, "Brokerage")
    a2 = _account(conn, "IRA", bucket="BUCKET_TAX")
    db.upsert_holding(conn, a1, "VTI", 10, last_price=200.0)
    db.upsert_holding(conn, a2, "VTI", 5, last_price=200.0)

    updates = refresh_holding_prices(conn, fetch=lambda s: 230.0)
    assert len(updates) == 1  # one symbol, both rows updated
    assert updates[0].old_price == 200.0
    assert updates[0].new_price == 230.0
    for h in db.get_holdings(conn):
        assert h["last_price"] == 230.0
        assert h["last_price_at"] is not None


def test_refresh_skips_failing_symbols(conn):
    acct = _account(conn)
    db.upsert_holding(conn, acct, "GOOD", 1, last_price=10.0)
    db.upsert_holding(conn, acct, "BAD", 1, last_price=10.0)

    def fetch(symbol):
        if symbol == "BAD":
            raise OSError("network down")
        return 11.0

    updates = refresh_holding_prices(conn, fetch=fetch)
    assert [u.symbol for u in updates] == ["GOOD"]


def test_no_provider_is_a_noop(conn, monkeypatch):
    monkeypatch.setattr("src.config.MARKET_DATA_PROVIDER", "none")
    acct = _account(conn)
    db.upsert_holding(conn, acct, "VTI", 10, last_price=200.0)
    name, fetch = resolve_provider()
    assert name == "none" and fetch is None
    assert refresh_holding_prices(conn) == []


def test_portfolio_alert_on_big_move(conn, monkeypatch):
    from src.investments.market_data import PriceUpdate

    acct = _account(conn)
    db.upsert_holding(conn, acct, "VTI", 10, last_price=200.0)
    monkeypatch.setattr(
        "src.sync.engine.refresh_holding_prices",
        lambda c: [PriceUpdate("VTI", 200.0, 178.0)],  # -11% move
    )
    report_id = db.create_action_report(conn, "TEST", summary="t")
    alerts = refresh_portfolio(conn, report_id)
    assert alerts == 1
    items = db.get_action_items(conn, report_id)
    assert items[0]["item_type"] == "PORTFOLIO_ALERT"
    assert "11.0%" in items[0]["description"]
    assert items[0]["urgency"] == "HIGH"


def test_small_move_no_alert(conn, monkeypatch):
    from src.investments.market_data import PriceUpdate

    acct = _account(conn)
    db.upsert_holding(conn, acct, "VTI", 10, last_price=200.0)
    monkeypatch.setattr(
        "src.sync.engine.refresh_holding_prices",
        lambda c: [PriceUpdate("VTI", 200.0, 204.0)],  # +2% < 5% threshold
    )
    report_id = db.create_action_report(conn, "TEST", summary="t")
    assert refresh_portfolio(conn, report_id) == 0
    assert db.get_action_items(conn, report_id) == []


def test_seeded_holdings_keep_net_worth_total(seeded_conn):
    # 401(k): 11,250 cash + 150 VTI @ 225 = 45,000; Roth: 4,000 + 20 VOO @ 400 = 12,000.
    summary = db.net_worth_summary(seeded_conn)
    assert summary["by_bucket"]["BUCKET_TAX"] == 45000.0
    assert summary["by_bucket"]["BUCKET_FREE"] == 12000.0
    assert summary["total"] == 67800.0


def test_heartbeat_snapshot_includes_holdings(seeded_conn):
    heartbeat(seeded_conn, today=date(2026, 6, 27))
    snaps = db.get_balance_snapshots(seeded_conn)
    assert snaps[-1]["total"] == 67800.0
