"""
Sync Engine — heartbeat-driven reconciliation and the Action Report Loop.

Each heartbeat opens a database connection, runs the previously disconnected
checks (subscription detection, cash-flow analysis, household vigilance), and
folds their findings into a single Action Report whose items await an explicit
Approve / Deny / Snooze decision.
"""

from __future__ import annotations

import sqlite3
import time
from datetime import date, datetime

import schedule

from src import config, db
from src.cashflow import analyze_bills_from_db
from src.sync.household import run_household_vigilance
from src.sync.subscriptions import run_subscription_detection


def sync_accounts(conn: sqlite3.Connection) -> int:
    """Reconcile accounts with external sources.

    Placeholder for the Plaid/Teller integration: a real implementation would
    fetch new transactions and insert them with ``status='PENDING'``. For now it
    operates on whatever data has already been seeded and reports zero new rows.
    """
    print(
        f"[{datetime.now().isoformat()}] Syncing accounts "
        "(no external source configured)..."
    )
    return 0


def detect_subscriptions(conn: sqlite3.Connection, report_id: int) -> int:
    """Run the Subscription Killer and attach cancel suggestions to the report."""
    print(f"[{datetime.now().isoformat()}] Running subscription killer detection...")
    detected = run_subscription_detection(conn)
    # Map merchant -> persisted subscription id so action items can reference them.
    sub_ids = {row["merchant_hash"]: row["id"] for row in db.get_subscriptions(conn)}
    for sub in detected:
        name = sub.label or sub.merchant_hash[:8]
        db.add_action_item(
            conn,
            report_id,
            item_type="SUBSCRIPTION_CANCEL",
            description=(
                f"Recurring {sub.frequency} charge detected: '{name}' "
                f"~${sub.amount:.2f} ({sub.occurrences} charges). Cancel?"
            ),
            amount=sub.amount,
            urgency="HIGH" if sub.amount >= 50 else "NORMAL",
            ref_table="subscriptions",
            ref_id=sub_ids.get(sub.merchant_hash),
        )
    print(f"  -> {len(detected)} recurring charge series detected.")
    return len(detected)


def run_cashflow(conn: sqlite3.Connection, report_id: int, today: date) -> int:
    """Run the cash-flow orchestrator and attach bill alerts to the report."""
    print(f"[{datetime.now().isoformat()}] Running paycheck-to-bill cash-flow checks...")
    alerts = analyze_bills_from_db(conn, today)
    for alert in alerts:
        name = alert.bill.label or alert.bill.merchant_hash[:8]
        db.add_action_item(
            conn,
            report_id,
            item_type="BILL_PAYMENT",
            description=f"{name}: {alert.message}",
            amount=alert.bill.amount,
            urgency="CRITICAL" if alert.alert_type == "PAY_NOW" else "NORMAL",
            ref_table="bills",
            ref_id=alert.bill.id,
        )
    print(f"  -> {len(alerts)} bill alert(s).")
    return len(alerts)


def check_household_vigilance(
    conn: sqlite3.Connection, report_id: int, today: date
) -> int:
    """Run household vigilance and attach spending alerts to the report."""
    print(f"[{datetime.now().isoformat()}] Running household vigilance checks...")
    alerts = run_household_vigilance(conn, today)
    for alert in alerts:
        if alert.reason == "OVER_LIMIT":
            msg = (
                f"Member {alert.member_hash[:8]} ({alert.role or 'unknown'}) spent "
                f"${alert.current_spend:.2f}, over their "
                f"${alert.spending_limit:.2f} limit."
            )
        else:
            msg = (
                f"Member {alert.member_hash[:8]} ({alert.role or 'unknown'}) spending "
                f"${alert.current_spend:.2f} this month vs. "
                f"${alert.baseline_monthly:.2f} baseline — possible spike."
            )
        db.add_action_item(
            conn,
            report_id,
            item_type="SPENDING_ALERT",
            description=msg,
            amount=alert.current_spend,
            urgency=alert.urgency,
        )
    print(f"  -> {len(alerts)} household alert(s).")
    return len(alerts)


def check_budgets(conn: sqlite3.Connection, report_id: int, today: date) -> int:
    """Compare current-month category spend against budgets; flag overspend."""
    print(f"[{datetime.now().isoformat()}] Running budget checks...")
    budgets = db.get_budgets(conn)
    if not budgets:
        print("  -> 0 budget alert(s).")
        return 0

    month_start = date(today.year, today.month, 1).isoformat()
    spent = {
        row["category"]: row["spent"]
        for row in db.spending_by_category(conn, since=month_start)
    }
    count = 0
    for budget in budgets:
        used = spent.get(budget["category"], 0.0)
        if used > budget["monthly_limit"]:
            db.add_action_item(
                conn,
                report_id,
                item_type="BUDGET_ALERT",
                description=(
                    f"Over budget on '{budget['category']}': spent "
                    f"${used:.2f} of ${budget['monthly_limit']:.2f} this month."
                ),
                amount=used,
                urgency="HIGH",
            )
            count += 1
    print(f"  -> {count} budget alert(s).")
    return count


def heartbeat(
    conn: sqlite3.Connection | None = None, today: date | None = None
) -> dict:
    """Run one full sync cycle and produce an Action Report.

    Returns a summary dict (report id and per-check counts) for inspection and
    testing.
    """
    owns_conn = conn is None
    conn = conn or db.get_connection()
    today = today or date.today()

    print(f"\n--- Starting Sync Heartbeat at {datetime.now().isoformat()} ---")
    db.migrate(conn)  # ensure schema exists before we touch it
    sync_id = db.start_sync(conn, "HEARTBEAT")
    report_id = db.create_action_report(conn, "HEARTBEAT", summary="Pending review")

    try:
        sync_accounts(conn)
        n_subs = detect_subscriptions(conn, report_id)
        n_bills = run_cashflow(conn, report_id, today)
        n_household = check_household_vigilance(conn, report_id, today)
        n_budget = check_budgets(conn, report_id, today)

        # Record a net-worth snapshot for the day (bookkeeping, not an alert).
        db.record_balance_snapshot(conn, today.isoformat())

        total_items = n_subs + n_bills + n_household + n_budget
        summary = (
            f"{total_items} action item(s): {n_bills} bill, "
            f"{n_subs} subscription, {n_household} household, {n_budget} budget. "
            f"Each requires Approve/Deny/Snooze."
        )
        db.update_report_summary(conn, report_id, summary)
        db.finish_sync(conn, sync_id, status="COMPLETE", items_processed=total_items)

        print(f"--- Action Report #{report_id}: {summary} ---")
        print("--- Heartbeat Complete ---\n")
        return {
            "report_id": report_id,
            "subscriptions": n_subs,
            "bills": n_bills,
            "household": n_household,
            "budget": n_budget,
            "total_items": total_items,
        }
    except Exception as exc:  # pragma: no cover - defensive logging path
        db.finish_sync(conn, sync_id, status="FAILED", errors=str(exc))
        raise
    finally:
        if owns_conn:
            conn.close()


def run() -> None:
    """Start the long-running heartbeat scheduler."""
    print("Starting Financial Mind-Map OS Sync Engine...")
    print(f"Configured for a {config.HEARTBEAT_HOURS}-hour heartbeat.")

    heartbeat()  # run once on startup

    schedule.every(config.HEARTBEAT_HOURS).hours.do(heartbeat)
    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    run()
