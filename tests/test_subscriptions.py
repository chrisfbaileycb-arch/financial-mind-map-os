"""Tests for the Subscription Killer heuristic."""

from __future__ import annotations

from datetime import date, timedelta

from src import db
from src.sync.subscriptions import (
    ChargeRecord,
    analyze_charges,
    classify_frequency,
    detect_price_increases,
    detect_recurring,
    run_price_increase_detection,
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


# --- Price-increase detection ------------------------------------------------


def _stepped_charges(
    merchant: str,
    old: float,
    new: float,
    old_count: int,
    new_count: int,
    start: date,
):
    """Monthly charges at ``old`` price, then ``new`` price."""
    charges = []
    for i in range(old_count + new_count):
        amount = old if i < old_count else new
        charges.append(
            ChargeRecord(merchant, amount, start + timedelta(days=30 * i), label=merchant)
        )
    return charges


def test_price_step_up_detected_and_tracked_at_new_price():
    charges = _stepped_charges("netflix", 15.99, 17.99, 4, 1, date(2026, 1, 5))

    subs = detect_recurring(charges)
    assert len(subs) == 1
    assert abs(subs[0].amount - 17.99) < 0.01  # tracked at the new price

    increases = detect_price_increases(charges)
    assert len(increases) == 1
    inc = increases[0]
    assert abs(inc.old_amount - 15.99) < 0.01
    assert abs(inc.new_amount - 17.99) < 0.01
    assert abs(inc.increase - 2.00) < 0.01
    assert abs(inc.pct_increase - 12.5) < 0.1
    assert inc.new_charges == 1


def test_small_wiggle_is_not_a_price_increase():
    # A 26-cent move stays within the $1 cluster tolerance: stable series.
    charges = _stepped_charges("hulu", 15.99, 16.25, 4, 1, date(2026, 1, 5))
    assert len(detect_recurring(charges)) == 1
    assert detect_price_increases(charges) == []


def test_price_decrease_is_not_flagged():
    charges = _stepped_charges("cable", 17.99, 12.99, 4, 2, date(2026, 1, 5))
    subs = detect_recurring(charges)
    assert len(subs) == 1
    assert abs(subs[0].amount - 12.99) < 0.01  # tracks the current price
    assert detect_price_increases(charges) == []


def test_erratic_amounts_still_rejected():
    # Multiple jumps means irregular, not a price change.
    charges = []
    for i, amount in enumerate([10.0, 14.0, 10.0, 14.0]):
        charges.append(ChargeRecord("erratic", amount, date(2026, 1, 5) + timedelta(days=30 * i)))
    assert detect_recurring(charges) == []
    assert detect_price_increases(charges) == []


def test_unconfirmed_new_price_tracks_old_price():
    charges = _stepped_charges("svc", 15.99, 17.99, 4, 1, date(2026, 1, 5))
    subs, increases = analyze_charges(charges, price_min_new_charges=2)
    assert len(subs) == 1
    assert abs(subs[0].amount - 15.99) < 0.01  # new price not confirmed yet
    assert increases == []


def test_seeded_netflix_hike_is_detected(seeded_conn):
    increases = run_price_increase_detection(seeded_conn)
    assert len(increases) == 1
    inc = increases[0]
    assert abs(inc.old_amount - 15.99) < 0.01
    assert abs(inc.new_amount - 17.99) < 0.01

    # The persisted subscription tracks the new price.
    run_subscription_detection(seeded_conn)
    stored = {
        row["merchant_hash"]: row["amount"]
        for row in db.get_subscriptions(seeded_conn)
    }
    assert abs(stored[inc.merchant_hash] - 17.99) < 0.01
