"""
Sample-data seeding for Financial Mind-Map OS.

Populates a fresh database with a small but realistic household so the engine,
cash-flow orchestrator, subscription killer and visualization all have something
to work with. Recurring charges are laid down on a regular monthly cadence so
the Subscription Killer detects them.

Run via ``python -m src.db.seed``.
"""

from __future__ import annotations

import sqlite3
from datetime import date, timedelta

from src import db


def _last_day_of_month(year: int, month: int) -> int:
    if month == 12:
        return 31
    return (date(year, month + 1, 1) - timedelta(days=1)).day


def _months_back(ref: date, n: int) -> date:
    """Return the date ``n`` months before ``ref`` on the same day-of-month."""
    month = ref.month - n
    year = ref.year
    while month <= 0:
        month += 12
        year -= 1
    day = min(ref.day, _last_day_of_month(year, month))
    return date(year, month, day)


def _reset(conn: sqlite3.Connection) -> None:
    for table in (
        "transactions",
        "subscriptions",
        "bills",
        "paycheck_schedules",
        "accounts",
        "household_members",
        "action_items",
        "action_reports",
        "sync_log",
    ):
        conn.execute(f"DELETE FROM {table}")
    conn.commit()


def seed_database(
    conn: sqlite3.Connection | None = None,
    today: date | None = None,
    reset: bool = True,
) -> None:
    """Seed the database with a sample household.

    When ``reset`` is true (the default) existing rows are cleared first so the
    result is deterministic.
    """
    owns_conn = conn is None
    conn = conn or db.get_connection()
    today = today or date.today()

    try:
        db.migrate(conn)
        if reset:
            _reset(conn)

        # --- Household members -----------------------------------------
        primary = db.hash_pii("primary@example.com")
        partner = db.hash_pii("partner@example.com")
        db.upsert_member(conn, primary, role="primary", baseline_monthly=1800.0)
        db.upsert_member(
            conn, partner, role="partner", spending_limit=800.0, baseline_monthly=500.0
        )

        # --- Accounts ---------------------------------------------------
        checking = db.hash_pii("checking-1234")
        savings = db.hash_pii("savings-5678")
        retirement = db.hash_pii("401k-9012")
        roth = db.hash_pii("roth-3456")
        db.upsert_account(conn, checking, "Checking", "BUCKET_TAXABLE", 2300.0, primary)
        db.upsert_account(conn, savings, "Savings", "BUCKET_TAXABLE", 8500.0, primary)
        db.upsert_account(conn, retirement, "401(k)", "BUCKET_TAX", 45000.0, primary)
        db.upsert_account(conn, roth, "Roth IRA", "BUCKET_FREE", 12000.0, partner)

        # --- Paycheck schedules ----------------------------------------
        db.insert_paycheck_schedule(conn, primary, pay_day_1=15, pay_day_2=30, pay_amount=2250.0)
        db.insert_paycheck_schedule(conn, partner, pay_day_1=5, pay_amount=3000.0)

        # --- Bills ------------------------------------------------------
        db.insert_bill(
            conn,
            db.hash_pii("Property Management LLC"),
            amount=1400.0,
            due_day=1,
            label="Rent",
            grace_period_days=3,
            late_fee=75.0,
            category="housing",
        )
        db.insert_bill(
            conn,
            db.hash_pii("Auto Finance Co"),
            amount=350.0,
            due_day=17,
            label="Car Payment",
            late_fee=25.0,
            category="transport",
        )
        db.insert_bill(
            conn,
            db.hash_pii("City Electric"),
            amount=120.0,
            due_day=12,
            label="Electric",
            grace_period_days=5,
            late_fee=15.0,
            category="utilities",
        )
        db.insert_bill(
            conn,
            db.hash_pii("FiberNet"),
            amount=70.0,
            due_day=20,
            label="Internet",
            category="utilities",
            auto_pay=True,  # delegated — should not raise an alert
        )

        # --- Recurring charges (the Subscription Killer should catch) ---
        recurring = [
            ("Netflix", "NETFLIX.COM 4567", 15.99),
            ("Spotify", "SPOTIFY P0F23A", 10.99),
            ("City Gym", "CITY GYM #221", 49.99),
        ]
        for name, raw_desc, amount in recurring:
            merchant_hash = db.hash_pii(name)
            tokens = db.tokenize_description(raw_desc)
            for i in range(6, 0, -1):  # six months of history up to last month
                charge_date = _months_back(today, i)
                db.insert_transaction(
                    conn,
                    account_hash=checking,
                    amount=-amount,
                    date=charge_date.isoformat(),
                    merchant_hash=merchant_hash,
                    member_hash=primary,
                    description_tokens=tokens,
                    is_subscription=True,
                    status="APPROVED",
                )

        # --- One-off / irregular spending (should NOT look recurring) ---
        oneoffs = [
            ("Grocery Mart", "GROCERY MART 8842", 84.20, 25),
            ("Gas Station", "SHELL OIL 2210", 41.50, 18),
            ("Hardware Store", "HOME HARDWARE", 132.75, 9),
        ]
        for name, raw_desc, amount, days_ago in oneoffs:
            db.insert_transaction(
                conn,
                account_hash=checking,
                amount=-amount,
                date=(today - timedelta(days=days_ago)).isoformat(),
                merchant_hash=db.hash_pii(name),
                member_hash=primary,
                description_tokens=db.tokenize_description(raw_desc),
            )

        # --- Partner spending this month (trips the household limit) ----
        partner_spend = [
            ("Department Store", "BIG DEPT STORE", 420.00, 6),
            ("Electronics", "GADGET WORLD", 510.00, 3),
        ]
        for name, raw_desc, amount, days_ago in partner_spend:
            db.insert_transaction(
                conn,
                account_hash=roth,
                amount=-amount,
                date=(today - timedelta(days=days_ago)).isoformat(),
                merchant_hash=db.hash_pii(name),
                member_hash=partner,
                description_tokens=db.tokenize_description(raw_desc),
            )

        # --- Income deposits -------------------------------------------
        db.insert_transaction(
            conn,
            account_hash=checking,
            amount=2250.0,
            date=(today - timedelta(days=2)).isoformat(),
            merchant_hash=db.hash_pii("Employer Payroll"),
            member_hash=primary,
            description_tokens="payroll deposit",
            status="APPROVED",
        )

        conn.commit()
        print("Seed complete: sample household, accounts, bills and transactions loaded.")
    finally:
        if owns_conn:
            conn.close()


if __name__ == "__main__":
    seed_database()
