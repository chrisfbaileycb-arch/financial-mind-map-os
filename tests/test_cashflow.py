"""Tests for the Paycheck-to-Bill Cash Flow Orchestrator."""

import sys

sys.path.insert(0, '.')

from datetime import date

from src.cashflow import (
    Bill,
    PaycheckSchedule,
    analyze_bills,
    get_following_paycheck,
    get_next_paycheck,
)


def test_next_paycheck_calculation():
    """Test that next paycheck is calculated correctly."""
    today = date(2026, 6, 10)
    pay_days = [15, 30]
    next_pay = get_next_paycheck(today, pay_days)
    assert next_pay == date(2026, 6, 15), f"Expected June 15, got {next_pay}"


def test_bill_before_paycheck_triggers_pay_now():
    """Test that a bill due before next paycheck triggers PAY_NOW alert."""
    today = date(2026, 6, 10)
    schedule = PaycheckSchedule(member_hash="abc123", pay_days=[15, 30])
    bills = [
        Bill(id=1, merchant_hash="electric_co", amount=150.0, due_day=12, late_fee=25.0)
    ]
    alerts = analyze_bills(today, bills, schedule)
    assert len(alerts) == 1
    assert alerts[0].alert_type == 'PAY_NOW'


def test_bill_after_paycheck_triggers_upcoming():
    """Test that a bill due after next paycheck triggers UPCOMING alert."""
    today = date(2026, 6, 10)
    schedule = PaycheckSchedule(member_hash="abc123", pay_days=[15, 30])
    bills = [
        Bill(id=2, merchant_hash="car_loan", amount=350.0, due_day=17)
    ]
    alerts = analyze_bills(today, bills, schedule)
    assert len(alerts) == 1
    assert alerts[0].alert_type == 'UPCOMING'


def test_following_paycheck():
    """Test following paycheck calculation."""
    today = date(2026, 6, 10)
    pay_days = [15, 30]
    following = get_following_paycheck(today, pay_days)
    assert following == date(2026, 6, 30), f"Expected June 30, got {following}"


def test_auto_pay_bills_are_skipped():
    """Bills set to auto-pay should not generate alerts."""
    today = date(2026, 6, 10)
    schedule = PaycheckSchedule(member_hash="abc123", pay_days=[15, 30])
    bills = [
        Bill(id=1, merchant_hash="internet", amount=70.0, due_day=12, auto_pay=True)
    ]
    assert analyze_bills(today, bills, schedule) == []


def test_bill_from_row_round_trips_through_db(conn):
    """A Bill hydrated from the bills table matches what was inserted."""
    from src import db

    bill_id = db.insert_bill(
        conn,
        merchant_hash="rent_co",
        amount=1400.0,
        due_day=1,
        label="Rent",
        grace_period_days=3,
        late_fee=75.0,
        category="housing",
        auto_pay=False,
    )
    rows = db.get_bills(conn)
    assert len(rows) == 1
    bill = Bill.from_row(rows[0])
    assert bill.id == bill_id
    assert bill.label == "Rent"
    assert bill.amount == 1400.0
    assert bill.category == "housing"
    assert bill.auto_pay is False


def test_analyze_bills_from_db(seeded_conn):
    """The DB-backed analyzer returns one alert per (non-auto-pay) bill."""
    from src.cashflow import analyze_bills_from_db

    alerts = analyze_bills_from_db(seeded_conn, date(2026, 6, 27))
    # Seed has 4 bills, one of which is auto-pay (internet) and skipped.
    assert len(alerts) == 3
    labels = {a.bill.label for a in alerts}
    assert "Internet" not in labels


if __name__ == "__main__":
    test_next_paycheck_calculation()
    test_bill_before_paycheck_triggers_pay_now()
    test_bill_after_paycheck_triggers_upcoming()
    test_following_paycheck()
    print("All cashflow tests passed!")
