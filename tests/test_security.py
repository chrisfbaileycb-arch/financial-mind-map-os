"""Security and input-validation regression tests."""

from __future__ import annotations

from datetime import date

import pytest
from fastapi.testclient import TestClient

from src import db
from src.api.app import create_app
from src.sync.engine import heartbeat


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("FMM_DB_PATH", str(tmp_path / "sec.db"))
    app = create_app()
    with TestClient(app) as c:
        yield c


def test_security_headers_present(client):
    resp = client.get("/api/health")
    assert resp.headers["X-Content-Type-Options"] == "nosniff"
    assert resp.headers["X-Frame-Options"] == "DENY"
    assert resp.headers["Referrer-Policy"] == "same-origin"


def test_malformed_transaction_date_rejected(client):
    resp = client.post(
        "/api/transactions",
        json={"account_id": "a1", "amount": -5.0, "date": "not-a-date"},
    )
    assert resp.status_code == 422


def test_invalid_holding_symbol_rejected(client):
    client.post(
        "/api/accounts",
        json={"account_id": "a1", "name": "Brokerage", "balance": 0},
    )
    account_hash = client.get("/api/accounts").json()[0]["account_hash"]
    resp = client.post(
        "/api/holdings",
        json={
            "account_hash": account_hash,
            "symbol": "VTI; DROP TABLE holdings--",
            "quantity": 1,
        },
    )
    assert resp.status_code == 422


def test_negative_holding_price_rejected(client):
    client.post(
        "/api/accounts",
        json={"account_id": "a1", "name": "Brokerage", "balance": 0},
    )
    account_hash = client.get("/api/accounts").json()[0]["account_hash"]
    resp = client.post(
        "/api/holdings",
        json={
            "account_hash": account_hash,
            "symbol": "VTI",
            "quantity": 1,
            "last_price": -10,
        },
    )
    assert resp.status_code == 422


def test_transactions_limit_bounds(client):
    assert client.get("/api/transactions?limit=0").status_code == 422
    assert client.get("/api/transactions?limit=99999").status_code == 422
    assert client.get("/api/transactions?limit=50").status_code == 200


def test_oversized_csv_rejected(client):
    resp = client.post(
        "/api/import/csv",
        json={
            "account_id": "a1",
            "csv_text": "x" * 5_000_001,
            "mapping": {"date": "date", "amount": "amount"},
        },
    )
    assert resp.status_code == 422


def test_malformed_stored_date_does_not_break_sync(conn):
    """A bad date already in the DB must not brick the heartbeat."""
    account = db.hash_pii("acct")
    db.upsert_account(conn, account, "Checking", "BUCKET_TAXABLE", 100.0)
    db.insert_transaction(
        conn,
        account_hash=account,
        amount=-9.99,
        date="garbage-date",
        merchant_hash=db.hash_pii("BadCo"),
        description_tokens="badco",
    )
    summary = heartbeat(conn, today=date(2026, 6, 27))  # must not raise
    assert summary["report_id"] > 0


def test_pii_is_hashed_and_digits_stripped():
    tokens = db.tokenize_description("ACME CORP card 4111111111111111")
    assert "4111111111111111" not in tokens
    hashed = db.hash_pii("primary@example.com")
    assert "primary@example.com" not in hashed
    assert len(hashed) == 64  # sha256 hex
