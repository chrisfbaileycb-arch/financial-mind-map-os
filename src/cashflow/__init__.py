"""
Paycheck-to-Bill Cash Flow Orchestrator

Maps upcoming bills against user paycheck cycles and alerts when a bill
must be paid from the current paycheck to avoid late fees.
"""

from datetime import date, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class PaycheckSchedule:
    """User's paycheck schedule."""
    member_hash: str
    pay_days: List[int]  # e.g., [15, 30] for bi-monthly


@dataclass
class Bill:
    """A recurring bill with a due date."""
    id: int
    merchant_hash: str
    amount: float
    due_day: int  # Day of month (1-31)
    grace_period_days: int = 0  # Days after due before late fee
    late_fee: float = 0.0


@dataclass
class BillAlert:
    """Alert generated when a bill needs attention."""
    bill: Bill
    alert_type: str  # 'PAY_NOW', 'UPCOMING', 'LATE_RISK'
    message: str
    days_until_due: int
    pay_from_paycheck: date


def get_next_paycheck(today: date, pay_days: List[int]) -> date:
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


def get_following_paycheck(today: date, pay_days: List[int]) -> date:
    """Get the paycheck AFTER the next one."""
    next_pay = get_next_paycheck(today, pay_days)
    return get_next_paycheck(next_pay + timedelta(days=1), pay_days)


def analyze_bills(
    today: date,
    bills: List[Bill],
    schedule: PaycheckSchedule
) -> List[BillAlert]:
    """
    Analyze all bills against paycheck schedule.
    Returns alerts for bills that need to be paid from the current paycheck.
    """
    alerts = []
    next_paycheck = get_next_paycheck(today, schedule.pay_days)
    following_paycheck = get_following_paycheck(today, schedule.pay_days)

    for bill in bills:
        # Calculate this month's due date
        try:
            due_date = date(today.year, today.month, bill.due_day)
        except ValueError:
            # Month doesn't have this day, use last day
            if today.month == 12:
                due_date = date(today.year + 1, 1, 1) - timedelta(days=1)
            else:
                due_date = date(today.year, today.month + 1, 1) - timedelta(days=1)

        # If due date already passed this month, look at next month
        if due_date < today:
            if today.month == 12:
                due_date = date(today.year + 1, 1, bill.due_day)
            else:
                try:
                    due_date = date(today.year, today.month + 1, bill.due_day)
                except ValueError:
                    due_date = date(today.year, today.month + 2, 1) - timedelta(days=1)

        days_until_due = (due_date - today).days
        late_deadline = due_date + timedelta(days=bill.grace_period_days)

        # Key logic: Does this bill fall BETWEEN next paycheck and following paycheck?
        # If so, user must pay from NEXT paycheck.
        # If it falls BEFORE next paycheck, it needs immediate attention.
        if due_date < next_paycheck:
            # Bill is due BEFORE next paycheck — pay NOW or risk late fee
            alerts.append(BillAlert(
                bill=bill,
                alert_type='PAY_NOW',
                message=f"URGENT: Due in {days_until_due} days, before your next paycheck on {next_paycheck}. Pay now to avoid ${bill.late_fee} late fee.",
                days_until_due=days_until_due,
                pay_from_paycheck=today  # Must use current funds
            ))
        elif due_date <= following_paycheck:
            # Bill falls between next and following paycheck — pay from next paycheck
            alerts.append(BillAlert(
                bill=bill,
                alert_type='UPCOMING',
                message=f"Due on the {bill.due_day}th ({days_until_due} days). Allocate from your {next_paycheck} paycheck.",
                days_until_due=days_until_due,
                pay_from_paycheck=next_paycheck
            ))

    # Sort by urgency
    priority = {'PAY_NOW': 0, 'LATE_RISK': 1, 'UPCOMING': 2}
    alerts.sort(key=lambda a: (priority.get(a.alert_type, 99), a.days_until_due))

    return alerts
