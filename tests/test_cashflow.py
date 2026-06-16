"""Tests for the Paycheck-to-Bill Cash Flow Orchestrator."""

import sys
sys.path.insert(0, '.')

from datetime import date
from src.cashflow import (
    PaycheckSchedule, Bill, analyze_bills,
    get_next_paycheck, get_following_paycheck
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


if __name__ == "__main__":
    test_next_paycheck_calculation()
    test_bill_before_paycheck_triggers_pay_now()
    test_bill_after_paycheck_triggers_upcoming()
    test_following_paycheck()
    print("All cashflow tests passed!")
