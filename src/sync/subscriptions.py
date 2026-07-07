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


@dataclass
class PriceIncrease:
    """A sustained step-up in a recurring charge's price."""

    merchant_hash: str
    old_amount: float
    new_amount: float
    increase: float
    pct_increase: float
    new_charges: int  # how many charges have landed at the new price
    last_charge_date: date
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


def _amounts_cluster(amounts: list[float], tolerance: float) -> float | None:
    """Return the cluster median if all ``amounts`` sit within tolerance of it.

    "Within tolerance" means within ``tolerance`` relative or $1 absolute of
    the median — the same rule the original detector used.
    """
    med = median(amounts)
    if med <= 0:
        return None
    allowed = max(tolerance * med, 1.0)
    if any(abs(a - med) > allowed for a in amounts):
        return None
    return med


def _find_single_step(amounts: list[float], tolerance: float) -> int | None:
    """Return the index of the one place ``amounts`` jumps, else ``None``.

    A jump is a consecutive-pair difference beyond tolerance. Exactly one jump
    means "stable old price, then stable new price" — a price change. Zero or
    multiple jumps mean the series is either stable or genuinely irregular.
    """
    jumps = [
        i
        for i in range(1, len(amounts))
        if abs(amounts[i] - amounts[i - 1]) > max(tolerance * amounts[i - 1], 1.0)
    ]
    return jumps[0] if len(jumps) == 1 else None


def analyze_charges(
    charges: list[ChargeRecord],
    *,
    min_occurrences: int = config.SUB_MIN_OCCURRENCES,
    amount_tolerance: float = config.SUB_AMOUNT_TOLERANCE,
    interval_tolerance_days: int = config.SUB_INTERVAL_TOLERANCE_DAYS,
    price_increase_min_abs: float = config.SUB_PRICE_INCREASE_MIN_ABS,
    price_increase_min_rel: float = config.SUB_PRICE_INCREASE_MIN_REL,
    price_min_new_charges: int = config.SUB_PRICE_MIN_NEW_CHARGES,
) -> tuple[list[DetectedSubscription], list[PriceIncrease]]:
    """Identify recurring charge series and price changes among ``charges``.

    A merchant's charges qualify as recurring when there are at least
    ``min_occurrences`` of them and the gaps between consecutive charges are
    regular (within ``interval_tolerance_days`` of their median). Amounts must
    either cluster around one median (within ``amount_tolerance`` relative or
    $1 absolute) — a stable subscription — or form exactly two stable clusters
    split at a single step: an established price followed by a new price. The
    stepped case still counts as a subscription (tracked at the *new* price)
    and, when the step is upward by at least
    ``max(price_increase_min_abs, price_increase_min_rel * old)``, also raises
    a :class:`PriceIncrease`.
    """
    by_merchant: dict[str, list[ChargeRecord]] = defaultdict(list)
    for charge in charges:
        by_merchant[charge.merchant_hash].append(charge)

    detected: list[DetectedSubscription] = []
    increases: list[PriceIncrease] = []
    for merchant_hash, group in by_merchant.items():
        if len(group) < min_occurrences:
            continue

        group = sorted(group, key=lambda c: c.charge_date)

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

        amounts = [c.amount for c in group]
        increase: PriceIncrease | None = None
        sub_amount = _amounts_cluster(amounts, amount_tolerance)
        if sub_amount is None:
            # Not one stable cluster — check for a single price step instead.
            step = _find_single_step(amounts, amount_tolerance)
            if step is None or step < min_occurrences:
                continue  # irregular amounts, or no established baseline
            old_amount = _amounts_cluster(amounts[:step], amount_tolerance)
            new_amount = _amounts_cluster(amounts[step:], amount_tolerance)
            if old_amount is None or new_amount is None:
                continue
            if len(amounts) - step < price_min_new_charges:
                # New price not confirmed yet — keep tracking the old price.
                sub_amount = old_amount
                new_amount = None
            else:
                # Track the subscription at its current (new) price.
                sub_amount = new_amount
            delta = (new_amount - old_amount) if new_amount is not None else 0.0
            if new_amount is not None and delta >= max(
                price_increase_min_abs, price_increase_min_rel * old_amount
            ):
                increase = PriceIncrease(
                    merchant_hash=merchant_hash,
                    old_amount=round(old_amount, 2),
                    new_amount=round(new_amount, 2),
                    increase=round(delta, 2),
                    pct_increase=round(100 * delta / old_amount, 1),
                    new_charges=len(amounts) - step,
                    last_charge_date=group[-1].charge_date,
                    label=next(
                        (c.label for c in reversed(group) if c.label), None
                    ),
                )

        last_charge = group[-1].charge_date
        label = next((c.label for c in reversed(group) if c.label), None)
        detected.append(
            DetectedSubscription(
                merchant_hash=merchant_hash,
                amount=round(sub_amount, 2),
                frequency=classify_frequency(med_gap, interval_tolerance_days),
                interval_days=med_gap,
                occurrences=len(group),
                last_charge_date=last_charge,
                next_due_date=last_charge + timedelta(days=med_gap),
                label=label,
            )
        )
        if increase is not None:
            increases.append(increase)

    detected.sort(key=lambda d: d.amount, reverse=True)
    increases.sort(key=lambda p: p.increase, reverse=True)
    return detected, increases


def detect_recurring(
    charges: list[ChargeRecord],
    *,
    min_occurrences: int = config.SUB_MIN_OCCURRENCES,
    amount_tolerance: float = config.SUB_AMOUNT_TOLERANCE,
    interval_tolerance_days: int = config.SUB_INTERVAL_TOLERANCE_DAYS,
) -> list[DetectedSubscription]:
    """Identify recurring charge series among ``charges`` (see analyze_charges)."""
    detected, _ = analyze_charges(
        charges,
        min_occurrences=min_occurrences,
        amount_tolerance=amount_tolerance,
        interval_tolerance_days=interval_tolerance_days,
    )
    return detected


def detect_price_increases(
    charges: list[ChargeRecord],
    *,
    min_occurrences: int = config.SUB_MIN_OCCURRENCES,
    amount_tolerance: float = config.SUB_AMOUNT_TOLERANCE,
    interval_tolerance_days: int = config.SUB_INTERVAL_TOLERANCE_DAYS,
) -> list[PriceIncrease]:
    """Identify price step-ups in recurring charges (see analyze_charges)."""
    _, increases = analyze_charges(
        charges,
        min_occurrences=min_occurrences,
        amount_tolerance=amount_tolerance,
        interval_tolerance_days=interval_tolerance_days,
    )
    return increases


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


def run_price_increase_detection(conn: sqlite3.Connection) -> list[PriceIncrease]:
    """Detect price step-ups in the DB's recurring charges.

    Returns the increases so the caller (the sync engine) can turn them into
    action items. Pure read — persistence of the updated price happens via
    :func:`run_subscription_detection`, which tracks the new amount.
    """
    return detect_price_increases(load_charges(conn))
