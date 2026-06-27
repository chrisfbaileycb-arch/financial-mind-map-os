"""
Paycheck-to-Bill Cash Flow Orchestrator

Maps upcoming bills against user paycheck cycles and alerts when a bill
must be paid from the current paycheck to avoid late fees.

The :class:`Bill` dataclass mirrors the ``bills`` table column-for-column so the
schema, the dataclasses and the engine stay consistent. Use :meth:`Bill.from_row`
to hydrate a :class:`Bill` from a ``sqlite3.Row``.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date, timedelta


@dataclass
class PaycheckSchedule:
    """User's paycheck schedule."""

    member_hash: str
    pay_days: list[int]  # e.g., [15, 30] for bi-monthly

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> PaycheckSchedule:
        pay_days = [row["pay_day_1"]]
        if row["pay_day_2"] is not None:
            pay_days.append(row["pay_day_2"])
        return cls(member_hash=row["member_hash"], pay_days=pay_days)


@dataclass
class Bill:
    """A recurring bill with a due date.

    Fields mirror the ``bills`` table so the dataclass and schema stay aligned.
    """

    id: int | None
    merchant_hash: str
    amount: float
    due_day: int  # Day of month (1-31)
    label: str | None = None
    grace_period_days: int = 0  # Days after due before late fee
    late_fee: float = 0.0
    category: str | None = None
    auto_pay: bool = False
    status: str = "ACTIVE"

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> Bill:
        keys = row.keys()
        return cls(
            id=row["id"],
            merchant_hash=row["merchant_hash"],
            amount=row["amount"],
            due_day=row["due_day"],
            label=row["label"] if "label" in keys else None,
            grace_period_days=row["grace_period_days"] or 0,
            late_fee=row["late_fee"] or 0.0,
            category=row["category"] if "category" in keys else None,
            auto_pay=bool(row["auto_pay"]) if "auto_pay" in keys else False,
            status=row["status"] if "status" in keys else "ACTIVE",
        )


@dataclass
class BillAlert:
    """Alert generated when a bill needs attention."""

    bill: Bill
    alert_type: str  # 'PAY_NOW', 'UPCOMING', 'LATE_RISK'
    message: str
    days_until_due: int
    pay_from_paycheck: date


def get_next_paycheck(today: date, pay_days: list[int]) -> date:
    """Calculate the next paycheck date from today."""
    current_month = today.month
    current_year = today.year

    for day in sorted(pay_days):
        try:
            pay_date = date(current_year, current_month, day)
            if pay_date >= today:
                return pay_date
        except ValueError:
            # Handle months with fewer days (e.g., Feb 30)
            continue

    # Roll to next month
    next_month = current_month + 1 if current_month < 12 else 1
    next_year = current_year if current_month < 12 else current_year + 1
    for day in sorted(pay_days):
        try:
            return date(next_year, next_month, day)
        except ValueError:
            continue

    return today + timedelta(days=15)  # Fallback


def get_following_paycheck(today: date, pay_days: list[int]) -> date:
    """Get the paycheck AFTER the next one."""
    next_pay = get_next_paycheck(today, pay_days)
    return get_next_paycheck(next_pay + timedelta(days=1), pay_days)


def _resolve_due_date(today: date, due_day: int) -> date:
    """Resolve a bill's next due date relative to ``today``.

    Clamps ``due_day`` to the last day of short months and rolls forward if the
    day has already passed this month.
    """

    def last_day_of(year: int, month: int) -> int:
        if month == 12:
            return 31
        return (date(year, month + 1, 1) - timedelta(days=1)).day

    def safe_date(year: int, month: int) -> date:
        day = min(due_day, last_day_of(year, month))
        return date(year, month, day)

    due_date = safe_date(today.year, today.month)
    if due_date < today:
        if today.month == 12:
            due_date = safe_date(today.year + 1, 1)
        else:
            due_date = safe_date(today.year, today.month + 1)
    return due_date


def analyze_bills(
    today: date,
    bills: list[Bill],
    schedule: PaycheckSchedule,
) -> list[BillAlert]:
    """Analyze all bills against a paycheck schedule.

    Returns alerts for bills that need to be paid from the current paycheck
    (``PAY_NOW``) or allocated from the next one (``UPCOMING``). Bills set to
    auto-pay are skipped — the user has already delegated those.
    """
    alerts: list[BillAlert] = []
    next_paycheck = get_next_paycheck(today, schedule.pay_days)
    following_paycheck = get_following_paycheck(today, schedule.pay_days)

    for bill in bills:
        if bill.auto_pay:
            continue

        due_date = _resolve_due_date(today, bill.due_day)
        days_until_due = (due_date - today).days

        # Key logic: does this bill fall due before the next paycheck?
        if due_date < next_paycheck:
            # Due BEFORE next paycheck — pay NOW or risk a late fee.
            alerts.append(
                BillAlert(
                    bill=bill,
                    alert_type="PAY_NOW",
                    message=(
                        f"URGENT: Due in {days_until_due} days, before your next "
                        f"paycheck on {next_paycheck}. Pay now to avoid a "
                        f"${bill.late_fee:.2f} late fee."
                    ),
                    days_until_due=days_until_due,
                    pay_from_paycheck=today,  # Must use current funds
                )
            )
        elif due_date <= following_paycheck:
            # Falls between next and following paycheck — pay from next paycheck.
            alerts.append(
                BillAlert(
                    bill=bill,
                    alert_type="UPCOMING",
                    message=(
                        f"Due on the {bill.due_day}th ({days_until_due} days). "
                        f"Allocate from your {next_paycheck} paycheck."
                    ),
                    days_until_due=days_until_due,
                    pay_from_paycheck=next_paycheck,
                )
            )

    # Sort by urgency, then soonest due.
    priority = {"PAY_NOW": 0, "LATE_RISK": 1, "UPCOMING": 2}
    alerts.sort(key=lambda a: (priority.get(a.alert_type, 99), a.days_until_due))

    return alerts


def load_bills(conn: sqlite3.Connection) -> list[Bill]:
    """Load active bills from the database as :class:`Bill` objects."""
    from src import db

    return [Bill.from_row(row) for row in db.get_bills(conn, active_only=True)]


def load_schedules(conn: sqlite3.Connection) -> list[PaycheckSchedule]:
    """Load paycheck schedules from the database."""
    from src import db

    return [PaycheckSchedule.from_row(row) for row in db.get_paycheck_schedules(conn)]


def analyze_bills_from_db(conn: sqlite3.Connection, today: date) -> list[BillAlert]:
    """Run bill analysis using bills and schedules loaded from the database.

    Bills are analyzed against every member's paycheck schedule; the most urgent
    alert per bill is kept so a single bill is not reported multiple times.
    """
    bills = load_bills(conn)
    schedules = load_schedules(conn)
    if not bills or not schedules:
        return []

    priority = {"PAY_NOW": 0, "LATE_RISK": 1, "UPCOMING": 2}
    best_by_bill: dict[int, BillAlert] = {}
    for schedule in schedules:
        for alert in analyze_bills(today, bills, schedule):
            key = alert.bill.id if alert.bill.id is not None else id(alert.bill)
            current = best_by_bill.get(key)
            if current is None or priority.get(alert.alert_type, 99) < priority.get(
                current.alert_type, 99
            ):
                best_by_bill[key] = alert

    alerts = list(best_by_bill.values())
    alerts.sort(key=lambda a: (priority.get(a.alert_type, 99), a.days_until_due))
    return alerts


def cashflow_timeline(
    conn: sqlite3.Connection, today: date, *, horizon_days: int = 45
) -> dict:
    """Project paydays and bills over the coming weeks with a running balance.

    Starts from the current taxable-account balance and walks each dated event
    (paychecks add, bills subtract) so the UI can warn when the balance dips
    below zero before the next paycheck.
    """
    from src import db

    horizon = today + timedelta(days=horizon_days)
    schedules = db.get_paycheck_schedules(conn)
    all_pay_days = sorted(
        {
            d
            for s in schedules
            for d in (s["pay_day_1"], s["pay_day_2"])
            if d is not None
        }
    )
    next_pay = get_next_paycheck(today, all_pay_days) if all_pay_days else None

    events: list[dict] = []

    for bill in load_bills(conn):
        if bill.auto_pay:
            continue
        due = _resolve_due_date(today, bill.due_day)
        if today <= due <= horizon:
            alert = "PAY_NOW" if next_pay and due < next_pay else "UPCOMING"
            events.append(
                {
                    "date": due.isoformat(),
                    "kind": "bill",
                    "label": bill.label or bill.merchant_hash[:8],
                    "amount": -bill.amount,
                    "alert_type": alert,
                }
            )

    for sched in schedules:
        pay_days = [sched["pay_day_1"]]
        if sched["pay_day_2"] is not None:
            pay_days.append(sched["pay_day_2"])
        amount = sched["pay_amount"] or 0.0
        cursor = today
        for _ in range(12):  # safety bound on iterations
            nxt = get_next_paycheck(cursor, pay_days)
            if nxt > horizon:
                break
            events.append(
                {
                    "date": nxt.isoformat(),
                    "kind": "payday",
                    "label": "Paycheck",
                    "amount": amount,
                }
            )
            cursor = nxt + timedelta(days=1)

    # Income lands before bills on the same day; then chronological.
    kind_rank = {"payday": 0, "bill": 1}
    events.sort(key=lambda e: (e["date"], kind_rank.get(e["kind"], 9)))

    summary = db.net_worth_summary(conn)
    balance = summary["by_bucket"].get("BUCKET_TAXABLE", 0.0)
    lowest = balance
    for event in events:
        balance = round(balance + event["amount"], 2)
        event["balance"] = balance
        lowest = min(lowest, balance)

    return {
        "start_balance": summary["by_bucket"].get("BUCKET_TAXABLE", 0.0),
        "lowest_balance": round(lowest, 2),
        "events": events,
    }
