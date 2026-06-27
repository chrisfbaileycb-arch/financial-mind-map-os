"""Tests for budgets, savings goals, and transaction filtering."""

from __future__ import annotations

from datetime import date

from src import db
from src.sync.engine import heartbeat
from src.visualization import NodeType, build_map_from_db


def _debit(conn, amount, category=None, when=None, desc=None):
    return db.insert_transaction(
        conn,
        account_hash=db.hash_pii("acct"),
        amount=amount,
        date=(when or date.today()).isoformat(),
        category=category,
        description_tokens=desc,
    )


def test_budget_alert_when_over(conn):
    today = date.today()
    _debit(conn, -80, category="food", when=today)
    _debit(conn, -70, category="food", when=today)
    db.upsert_budget(conn, "food", 100)

    summary = heartbeat(conn, today=today)
    assert summary["budget"] == 1
    items = db.get_action_items(conn, summary["report_id"])
    assert any(i["item_type"] == "BUDGET_ALERT" for i in items)


def test_no_budget_alert_when_under(conn):
    today = date.today()
    _debit(conn, -40, category="food", when=today)
    db.upsert_budget(conn, "food", 100)
    summary = heartbeat(conn, today=today)
    assert summary["budget"] == 0


def test_budget_upsert_and_delete(conn):
    db.upsert_budget(conn, "food", 100)
    db.upsert_budget(conn, "food", 150)  # update, not duplicate
    budgets = db.get_budgets(conn)
    assert len(budgets) == 1 and budgets[0]["monthly_limit"] == 150
    db.delete_budget(conn, "food")
    assert db.get_budgets(conn) == []


def test_goal_crud_and_map_node(conn):
    acct = db.hash_pii("savings")
    db.upsert_account(conn, acct, name="Savings", bucket_type="BUCKET_TAXABLE")
    goal_id = db.insert_goal(
        conn, "Emergency Fund", 10000, current_amount=2500, account_hash=acct
    )
    db.update_goal(conn, goal_id, current_amount=3000)
    assert db.get_goal(conn, goal_id)["current_amount"] == 3000

    graph = build_map_from_db(conn).to_graph_data()
    goal_nodes = [n for n in graph["nodes"] if n["type"] == NodeType.GOAL.value]
    assert len(goal_nodes) == 1
    assert goal_nodes[0]["label"] == "Emergency Fund"
    assert goal_nodes[0]["metadata"]["progress"] == 0.3

    db.delete_goal(conn, goal_id)
    assert db.get_goals(conn) == []


def test_transaction_filters(conn):
    _debit(conn, -10, category="food", desc="chipotle burrito")
    _debit(conn, -20, category="gas", desc="shell oil")
    by_cat = db.get_transactions(conn, category="food")
    assert len(by_cat) == 1 and by_cat[0]["category"] == "food"
    by_q = db.get_transactions(conn, query="shell")
    assert len(by_q) == 1 and "shell" in by_q[0]["description_tokens"]
