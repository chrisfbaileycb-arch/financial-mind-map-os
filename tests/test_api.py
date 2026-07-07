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
    assert summary["total_items"] == 8

    latest = client.get("/api/report/latest").json()
    assert latest["report"]["id"] == summary["report_id"]
    assert len(latest["items"]) == 8


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


def test_transactions_list_and_categorize(client):
    txns = client.get("/api/transactions").json()
    assert len(txns) > 0
    debit = next(t for t in txns if t["amount"] < 0)
    resp = client.patch(f"/api/transactions/{debit['id']}", json={"category": "fun"})
    assert resp.status_code == 200
    assert resp.json()["category"] == "fun"


def test_transaction_split(client):
    txns = client.get("/api/transactions").json()
    debit = next(t for t in txns if t["amount"] < 0)
    half = round(debit["amount"] / 2, 2)
    resp = client.post(
        f"/api/transactions/{debit['id']}/split",
        json={"parts": [
            {"amount": half, "category": "a"},
            {"amount": debit["amount"] - half, "category": "b"},
        ]},
    )
    assert resp.status_code == 200
    assert len(resp.json()["created"]) == 2


def test_spending_endpoint(client):
    data = client.get("/api/spending").json()
    assert "by_month" in data and "by_category" in data
    assert len(data["by_month"]) > 0


def test_edit_and_delete_bill(client):
    bill = client.get("/api/bills").json()[0]
    resp = client.patch(f"/api/bills/{bill['id']}", json={"amount": 999.0})
    assert resp.status_code == 200 and resp.json()["amount"] == 999.0
    resp = client.delete(f"/api/bills/{bill['id']}")
    assert resp.status_code == 200 and resp.json()["status"] == "CANCELLED"


def test_edit_account(client):
    acct = client.get("/api/accounts").json()[0]
    resp = client.patch(
        f"/api/accounts/{acct['account_hash']}", json={"balance": 4321.0}
    )
    assert resp.status_code == 200
    updated = next(
        a for a in client.get("/api/accounts").json()
        if a["account_hash"] == acct["account_hash"]
    )
    assert updated["balance"] == 4321.0


def test_cashflow_endpoint(client):
    data = client.get("/api/cashflow").json()
    assert "start_balance" in data and "events" in data
    assert all("balance" in e for e in data["events"])


def test_networth_endpoint(client):
    client.post("/api/sync")  # records a snapshot
    data = client.get("/api/networth").json()
    assert data["summary"]["total"] > 0
    assert "BUCKET_TAX" in data["summary"]["by_bucket"]
    assert len(data["history"]) > 0


def test_budgets_endpoints(client):
    resp = client.put("/api/budgets", json={"category": "groceries", "monthly_limit": 400})
    assert resp.status_code == 200
    budgets = client.get("/api/budgets").json()
    assert any(b["category"] == "groceries" and "spent" in b for b in budgets)
    assert client.delete("/api/budgets/groceries").json()["deleted"] is True


def test_goals_endpoints(client):
    resp = client.post(
        "/api/goals", json={"label": "Vacation", "target_amount": 5000, "current_amount": 1000}
    )
    assert resp.status_code == 201
    goal_id = resp.json()["id"]
    resp = client.patch(f"/api/goals/{goal_id}", json={"current_amount": 1500})
    assert resp.status_code == 200 and resp.json()["current_amount"] == 1500
    goals = client.get("/api/goals").json()
    assert any(g["id"] == goal_id for g in goals)
    # Goal shows up on the mind map.
    graph = client.get("/api/graph").json()
    assert any(n["type"] == "goal" for n in graph["nodes"])
    assert client.delete(f"/api/goals/{goal_id}").json()["deleted"] is True


def test_transaction_filter_endpoint(client):
    all_txns = client.get("/api/transactions").json()
    debit = next(t for t in all_txns if t["amount"] < 0)
    client.patch(f"/api/transactions/{debit['id']}", json={"category": "uniquecat"})
    filtered = client.get("/api/transactions?category=uniquecat").json()
    assert len(filtered) == 1 and filtered[0]["id"] == debit["id"]


def test_manual_bill_creation(client):
    resp = client.post(
        "/api/bills",
        json={"merchant": "New Co", "label": "Phone", "amount": 45.0, "due_day": 8},
    )
    assert resp.status_code == 201
    bill_id = resp.json()["id"]
    bills = client.get("/api/bills").json()
    assert any(b["id"] == bill_id and b["label"] == "Phone" for b in bills)
