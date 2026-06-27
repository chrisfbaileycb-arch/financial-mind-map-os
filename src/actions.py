"""
Action Report Loop — resolution logic.

Turns a pending action item into a decision (Approve / Deny / Snooze) and
applies the real-world effect of that decision. This is what makes the loop
more than a list: approving a "Cancel?" suggestion actually marks the
subscription cancelled; snoozing defers the item to a future date.
"""

from __future__ import annotations

import sqlite3
from datetime import date, timedelta

from src import db

RESOLUTIONS = {"APPROVED", "DENIED", "SNOOZED"}
DEFAULT_SNOOZE_DAYS = 7


def resolve_action_item(
    conn: sqlite3.Connection,
    item_id: int,
    resolution: str,
    *,
    snooze_days: int = DEFAULT_SNOOZE_DAYS,
    today: date | None = None,
) -> sqlite3.Row:
    """Resolve a single action item and apply its side effect.

    Returns the updated item row. Raises ``ValueError`` for an unknown item or
    an invalid resolution.
    """
    resolution = resolution.upper()
    if resolution not in RESOLUTIONS:
        raise ValueError(
            f"Invalid resolution {resolution!r}; expected one of {sorted(RESOLUTIONS)}"
        )

    item = db.get_action_item(conn, item_id)
    if item is None:
        raise ValueError(f"No action item with id {item_id}")

    snooze_until = None
    if resolution == "SNOOZED":
        base = today or date.today()
        snooze_until = (base + timedelta(days=snooze_days)).isoformat()

    # Apply the effect of an approved suggestion.
    if resolution == "APPROVED":
        _apply_approval(conn, item)
    elif resolution == "DENIED":
        _apply_denial(conn, item)

    db.set_action_item_status(conn, item_id, resolution, snooze_until=snooze_until)
    return db.get_action_item(conn, item_id)


def _apply_approval(conn: sqlite3.Connection, item: sqlite3.Row) -> None:
    """Apply the real-world effect of approving a suggestion."""
    item_type = item["item_type"]
    ref_table = item["ref_table"]
    ref_id = item["ref_id"]

    if item_type == "SUBSCRIPTION_CANCEL" and ref_table == "subscriptions" and ref_id:
        # Approving "Cancel?" means the user wants it gone.
        db.set_subscription_status(conn, ref_id, "CANCELLED")
    # BILL_PAYMENT / SPENDING_ALERT approvals are acknowledgements; the bill
    # recurs next cycle and the spend is simply marked reviewed.


def _apply_denial(conn: sqlite3.Connection, item: sqlite3.Row) -> None:
    """Apply the effect of denying a suggestion."""
    item_type = item["item_type"]
    ref_table = item["ref_table"]
    ref_id = item["ref_id"]

    if item_type == "SUBSCRIPTION_CANCEL" and ref_table == "subscriptions" and ref_id:
        # Denying "Cancel?" means "keep it" — so promote the recurring charge to
        # a tracked bill the cash-flow orchestrator can plan around, and mark the
        # subscription reviewed so it is not re-surfaced.
        db.set_subscription_status(conn, ref_id, "ACTIVE")
        _promote_subscription_to_bill(conn, ref_id)


def _promote_subscription_to_bill(conn: sqlite3.Connection, subscription_id: int) -> None:
    """Create a tracked bill from a kept subscription (idempotent per merchant)."""
    sub = db.get_subscription(conn, subscription_id)
    if sub is None:
        return
    if db.get_bill_by_merchant(conn, sub["merchant_hash"]) is not None:
        return  # already tracked

    due_day = 1
    if sub["next_due_date"]:
        try:
            due_day = date.fromisoformat(sub["next_due_date"]).day
        except ValueError:
            due_day = 1
    db.insert_bill(
        conn,
        sub["merchant_hash"],
        amount=sub["amount"],
        due_day=due_day,
        label=sub["label"] or "Subscription",
        category="subscription",
    )


def resolve_report(
    conn: sqlite3.Connection,
    report_id: int,
    resolution: str,
    *,
    today: date | None = None,
) -> list[sqlite3.Row]:
    """Resolve every still-pending item in a report the same way."""
    items = db.get_action_items(conn, report_id)
    resolved = []
    for item in items:
        if item["status"] == "PENDING":
            resolved.append(
                resolve_action_item(conn, item["id"], resolution, today=today)
            )
    return resolved
