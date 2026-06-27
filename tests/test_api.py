"""Tests for the FastAPI layer."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.db.seed import seed_database


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("FMM_DB_PATH", str(tmp_path / "api.db"))
    seed_database()  # uses FMM_DB_PATH
    with TestClient(create_app()) as c:
        yield c


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_sync_and_latest_report(client):
    summary = client.post("/api/sync").json()
    assert summary["total_items"] == 7

    latest = client.get("/api/report/latest").json()
    assert latest["report"]["id"] == summary["report_id"]
    assert len(latest["items"]) == 7


def test_resolve_item_via_api(client):
    client.post("/api/sync")
    items = client.get("/api/report/latest").json()["items"]
    sub_item = next(i for i in items if i["item_type"] == "SUBSCRIPTION_CANCEL")

    resp = client.post(
        f"/api/items/{sub_item['id']}/resolve", json={"resolution": "APPROVED"}
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "APPROVED"

    subs = client.get("/api/subscriptions").json()
    cancelled = [s for s in subs if s["id"] == sub_item["ref_id"]]
    assert cancelled and cancelled[0]["status"] == "CANCELLED"


def test_resolve_unknown_item_404(client):
    resp = client.post("/api/items/99999/resolve", json={"resolution": "DENIED"})
    assert resp.status_code == 404


def test_graph_endpoint(client):
    graph = client.get("/api/graph").json()
    assert graph["metadata"]["total_nodes"] > 0
    assert graph["metadata"]["total_edges"] > 0


def test_collections_endpoints(client):
    assert len(client.get("/api/accounts").json()) == 4
    assert len(client.get("/api/bills").json()) == 4
    assert len(client.get("/api/members").json()) == 2


def test_csv_import_endpoint(client):
    lines = ["Date,Amount,Description"]
    for month in range(1, 7):
        lines.append(f"2026-{month:02d}-05,-9.99,SPOTIFY")
    payload = {
        "account_id": "import-acct",
        "csv_text": "\n".join(lines) + "\n",
        "mapping": {"date": "Date", "amount": "Amount", "description": "Description"},
    }
    resp = client.post("/api/import/csv", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["imported"] == 6
    assert data["detected"] >= 1


def test_manual_bill_creation(client):
    resp = client.post(
        "/api/bills",
        json={"merchant": "New Co", "label": "Phone", "amount": 45.0, "due_day": 8},
    )
    assert resp.status_code == 201
    bill_id = resp.json()["id"]
    bills = client.get("/api/bills").json()
    assert any(b["id"] == bill_id and b["label"] == "Phone" for b in bills)
