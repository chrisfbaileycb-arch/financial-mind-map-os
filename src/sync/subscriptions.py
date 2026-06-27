"""
Subscription Killer — recurring-charge detection.

The heuristic groups transactions by merchant and flags a series as a
subscription when the charges are (a) for roughly the same amount and (b) spaced
at a regular interval. The pure :func:`detect_recurring` function is decoupled
from the database for easy testing; :func:`run_subscription_detection` wires it
to the ``transactions`` and ``subscriptions`` tables.
"""

from __future__ import annotations

import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from statistics import median

from src import config

# Known cadences in days, used to give a detected series a human label.
_CADENCES: list[tuple[int, str]] = [
    (7, "weekly"),
    (14, "biweekly"),
    (30, "monthly"),
    (91, "quarterly"),
    (182, "semiannual"),
    (365, "annual"),
]


@dataclass
class ChargeRecord:
    """A single charge fed into the detector."""

    merchant_hash: str
    amount: float  # positive magnitude of the charge
    charge_date: date
    label: str | None = None


@dataclass
class DetectedSubscription:
    """A recurring charge series identified by the heuristic."""

    merchant_hash: str
    amount: float
    frequency: str
    interval_days: int
    occurrences: int
    last_charge_date: date
    next_due_date: date
    label: str | None = None


def classify_frequency(interval_days: int, tolerance_days: int) -> str:
    """Map a median interval (in days) to a human-readable cadence label."""
    best_days, best_label = min(
        _CADENCES, key=lambda c: abs(c[0] - interval_days)
    )
    # Accept the nearest named cadence if it is close enough; otherwise report
    # the raw interval so we never mislabel an irregular-but-regular series.
    if abs(best_days - interval_days) <= max(tolerance_days, int(best_days * 0.15)):
        return best_label
    return f"every {interval_days} days"


def detect_recurring(
    charges: list[ChargeRecord],
    *,
    min_occurrences: int = config.SUB_MIN_OCCURRENCES,
    amount_tolerance: float = config.SUB_AMOUNT_TOLERANCE,
    interval_tolerance_days: int = config.SUB_INTERVAL_TOLERANCE_DAYS,
) -> list[DetectedSubscription]:
    """Identify recurring charge series among ``charges``.

    A merchant's charges qualify when there are at least ``min_occurrences`` of
    them, the amounts cluster around a median (within ``amount_tolerance``
    relative or $1 absolute), and the gaps between consecutive charges are
    regular (within ``interval_tolerance_days`` of their median).
    """
    by_merchant: dict[str, list[ChargeRecord]] = defaultdict(list)
    for charge in charges:
        by_merchant[charge.merchant_hash].append(charge)

    detected: list[DetectedSubscription] = []
    for merchant_hash, group in by_merchant.items():
        if len(group) < min_occurrences:
            continue

        group = sorted(group, key=lambda c: c.charge_date)

        amounts = [c.amount for c in group]
        med_amount = median(amounts)
        if med_amount <= 0:
            continue
        allowed = max(amount_tolerance * med_amount, 1.0)
        if any(abs(a - med_amount) > allowed for a in amounts):
            continue

        gaps = [
            (group[i].charge_date - group[i - 1].charge_date).days
            for i in range(1, len(group))
        ]
        if not gaps:
            continue
        med_gap = int(round(median(gaps)))
        if med_gap <= 0:
            continue
        if any(abs(g - med_gap) > interval_tolerance_days for g in gaps):
            continue

        last_charge = group[-1].charge_date
        label = next((c.label for c in reversed(group) if c.label), None)
        detected.append(
            DetectedSubscription(
                merchant_hash=merchant_hash,
                amount=round(med_amount, 2),
                frequency=classify_frequency(med_gap, interval_tolerance_days),
                interval_days=med_gap,
                occurrences=len(group),
                last_charge_date=last_charge,
                next_due_date=last_charge + timedelta(days=med_gap),
                label=label,
            )
        )

    detected.sort(key=lambda d: d.amount, reverse=True)
    return detected


def _parse_date(value: str) -> date:
    """Parse an ISO date or datetime string into a ``date``."""
    return datetime.fromisoformat(value).date()


def load_charges(conn: sqlite3.Connection) -> list[ChargeRecord]:
    """Load debit transactions with a merchant as :class:`ChargeRecord` objects."""
    from src import db

    charges: list[ChargeRecord] = []
    for row in db.get_transactions(conn, only_debits=True):
        if not row["merchant_hash"]:
            continue
        charges.append(
            ChargeRecord(
                merchant_hash=row["merchant_hash"],
                amount=abs(row["amount"]),
                charge_date=_parse_date(row["date"]),
                label=row["description_tokens"],
            )
        )
    return charges


def run_subscription_detection(
    conn: sqlite3.Connection,
) -> list[DetectedSubscription]:
    """Detect recurring charges in the DB and persist them to ``subscriptions``.

    Returns the detected subscriptions so the caller (the sync engine) can turn
    them into action items.
    """
    from src import db

    charges = load_charges(conn)
    detected = detect_recurring(charges)

    for sub in detected:
        db.upsert_subscription(
            conn,
            merchant_hash=sub.merchant_hash,
            amount=sub.amount,
            label=sub.label,
            frequency=sub.frequency,
            interval_days=sub.interval_days,
            occurrences=sub.occurrences,
            last_charge_date=sub.last_charge_date.isoformat(),
            next_due_date=sub.next_due_date.isoformat(),
        )

    return detected
