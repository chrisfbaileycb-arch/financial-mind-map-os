"""Tests for the Subscription Killer heuristic."""

from __future__ import annotations

from datetime import date, timedelta

from src import db
from src.sync.subscriptions import (
    ChargeRecord,
    classify_frequency,
    detect_recurring,
    run_subscription_detection,
)


def _monthly_charges(merchant: str, amount: float, count: int, start: date):
    charges = []
    for i in range(count):
        # ~monthly spacing with mild jitter that stays within tolerance
        charge_date = start + timedelta(days=30 * i + (i % 2))
        charges.append(ChargeRecord(merchant, amount, charge_date, label=merchant))
    return charges


def test_detects_regular_monthly_charge():
    charges = _monthly_charges("netflix", 15.99, 5, date(2026, 1, 5))
    detected = detect_recurring(charges)
    assert len(detected) == 1
    sub = detected[0]
    assert sub.merchant_hash == "netflix"
    assert sub.frequency == "monthly"
    assert sub.occurrences == 5
    assert abs(sub.amount - 15.99) < 0.01


def test_too_few_occurrences_not_detected():
    charges = _monthly_charges("rare", 9.99, 2, date(2026, 1, 1))
    assert detect_recurring(charges, min_occurrences=3) == []


def test_irregular_intervals_not_detected():
    charges = [
        ChargeRecord("shop", 20.0, date(2026, 1, 1)),
        ChargeRecord("shop", 20.0, date(2026, 1, 18)),
        ChargeRecord("shop", 20.0, date(2026, 3, 2)),
        ChargeRecord("shop", 20.0, date(2026, 3, 9)),
    ]
    assert detect_recurring(charges) == []


def test_varying_amounts_not_detected():
    charges = [
        ChargeRecord("varies", 10.0, date(2026, 1, 1)),
        ChargeRecord("varies", 80.0, date(2026, 2, 1)),
        ChargeRecord("varies", 45.0, date(2026, 3, 1)),
    ]
    assert detect_recurring(charges) == []


def test_amount_within_tolerance_is_detected():
    # Small variation (under 5%) around ~$20 should still count.
    charges = [
        ChargeRecord("flex", 20.00, date(2026, 1, 1)),
        ChargeRecord("flex", 20.50, date(2026, 1, 31)),
        ChargeRecord("flex", 19.75, date(2026, 3, 2)),
    ]
    detected = detect_recurring(charges)
    assert len(detected) == 1


def test_classify_frequency():
    assert classify_frequency(30, 5) == "monthly"
    assert classify_frequency(7, 5) == "weekly"
    assert classify_frequency(14, 5) == "biweekly"
    assert classify_frequency(365, 5) == "annual"
    # An interval far from any named cadence reports raw days.
    assert classify_frequency(50, 2) == "every 50 days"


def test_next_due_date_projects_forward():
    charges = _monthly_charges("svc", 5.0, 4, date(2026, 1, 10))
    sub = detect_recurring(charges)[0]
    assert sub.next_due_date > sub.last_charge_date


def test_run_detection_persists_to_db(seeded_conn):
    detected = run_subscription_detection(seeded_conn)
    # The seed lays down three monthly recurring merchants.
    assert len(detected) == 3
    stored = db.get_subscriptions(seeded_conn)
    assert len(stored) == 3
    # Running again should not duplicate rows (unique per merchant).
    run_subscription_detection(seeded_conn)
    assert len(db.get_subscriptions(seeded_conn)) == 3
