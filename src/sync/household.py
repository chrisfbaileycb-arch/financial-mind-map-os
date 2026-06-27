"""
Shared Vigilance — household spending-spike detection.

Compares each household member's current-month spending against their configured
baseline and limit. The pure :func:`evaluate_spending` keeps the rule logic
testable; :func:`run_household_vigilance` sources current spend from the
``transactions`` table.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date

from src import config


@dataclass
class VigilanceAlert:
    """A flagged member whose spending warrants attention."""

    member_hash: str
    role: str | None
    current_spend: float
    baseline_monthly: float
    spending_limit: float | None
    reason: str  # 'OVER_LIMIT' or 'SPIKE'
    urgency: str  # 'CRITICAL', 'HIGH', ...


def evaluate_spending(
    member_hash: str,
    current_spend: float,
    *,
    role: str | None = None,
    baseline_monthly: float = 0.0,
    spending_limit: float | None = None,
    spike_factor: float = config.HOUSEHOLD_SPIKE_FACTOR,
) -> VigilanceAlert | None:
    """Return an alert if a member's spend breaches their limit or baseline.

    A hard ``spending_limit`` breach is CRITICAL; spending above
    ``baseline_monthly * spike_factor`` is a HIGH-urgency spike.
    """
    if spending_limit is not None and current_spend > spending_limit:
        return VigilanceAlert(
            member_hash=member_hash,
            role=role,
            current_spend=current_spend,
            baseline_monthly=baseline_monthly,
            spending_limit=spending_limit,
            reason="OVER_LIMIT",
            urgency="CRITICAL",
        )

    if baseline_monthly > 0 and current_spend > baseline_monthly * spike_factor:
        return VigilanceAlert(
            member_hash=member_hash,
            role=role,
            current_spend=current_spend,
            baseline_monthly=baseline_monthly,
            spending_limit=spending_limit,
            reason="SPIKE",
            urgency="HIGH",
        )

    return None


def _month_start(today: date) -> str:
    return date(today.year, today.month, 1).isoformat()


def run_household_vigilance(
    conn: sqlite3.Connection, today: date
) -> list[VigilanceAlert]:
    """Evaluate every household member's current-month spending."""
    from src import db

    month_start = _month_start(today)
    alerts: list[VigilanceAlert] = []
    for member in db.get_members(conn):
        txns = db.get_transactions(
            conn,
            member_hash=member["member_hash"],
            since=month_start,
            only_debits=True,
        )
        current_spend = sum(abs(t["amount"]) for t in txns)
        alert = evaluate_spending(
            member["member_hash"],
            current_spend,
            role=member["role"],
            baseline_monthly=member["baseline_monthly"] or 0.0,
            spending_limit=member["spending_limit"],
        )
        if alert is not None:
            alerts.append(alert)
    return alerts
