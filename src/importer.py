"""
CSV transaction import.

Bank/card exports vary wildly, so import is driven by a column mapping: the
caller says which columns hold the date, amount (or separate debit/credit
columns), description and (optionally) merchant. The pure :func:`parse_csv`
keeps parsing testable; :func:`import_transactions` writes the rows and can run
subscription detection afterwards.

Amounts are normalized to the project convention: money out is negative, money
in is positive.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from datetime import datetime

_DATE_FORMATS = [
    "%Y-%m-%d",
    "%m/%d/%Y",
    "%m/%d/%y",
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%Y/%m/%d",
    "%m-%d-%Y",
    "%b %d, %Y",
    "%d %b %Y",
]


@dataclass
class ColumnMapping:
    """Which CSV columns map to which transaction fields."""

    date: str
    amount: str | None = None
    debit: str | None = None
    credit: str | None = None
    description: str | None = None
    merchant: str | None = None
    flip_sign: bool = False  # negate a single signed amount column


@dataclass
class ParsedRow:
    date: str  # normalized ISO date
    amount: float  # signed: negative = out
    description: str
    merchant: str  # raw merchant key (hashed at import time)


@dataclass
class ParseResult:
    rows: list[ParsedRow] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def _parse_date(value: str) -> str:
    value = value.strip()
    try:
        return datetime.fromisoformat(value).date().isoformat()
    except ValueError:
        pass
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            continue
    raise ValueError(f"Unrecognized date: {value!r}")


def _parse_amount(value: str) -> float:
    """Parse a currency string, handling $, commas and accounting parentheses."""
    raw = value.strip()
    if not raw:
        return 0.0
    negative = raw.startswith("(") and raw.endswith(")")
    cleaned = raw.strip("()").replace("$", "").replace(",", "").strip()
    if cleaned in {"", "-", "+"}:
        return 0.0
    amount = float(cleaned)
    return -amount if negative else amount


def parse_csv(text: str, mapping: ColumnMapping) -> ParseResult:
    """Parse CSV text into normalized rows using ``mapping``.

    Rows that fail to parse are collected as errors (1-based, accounting for the
    header) rather than aborting the whole import.
    """
    result = ParseResult()
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        result.errors.append("CSV has no header row.")
        return result

    fields = set(reader.fieldnames)
    required = [mapping.date]
    if mapping.amount:
        required.append(mapping.amount)
    elif mapping.debit or mapping.credit:
        required.extend([c for c in (mapping.debit, mapping.credit) if c])
    else:
        result.errors.append("Mapping must set 'amount' or 'debit'/'credit'.")
        return result
    missing = [c for c in required if c not in fields]
    if missing:
        result.errors.append(f"CSV missing mapped columns: {', '.join(missing)}")
        return result

    for i, row in enumerate(reader, start=2):  # row 1 is the header
        try:
            date = _parse_date(row[mapping.date])
            amount = _row_amount(row, mapping)
            description = (
                row.get(mapping.description, "").strip() if mapping.description else ""
            )
            merchant = (
                row.get(mapping.merchant, "").strip() if mapping.merchant else ""
            ) or description
            if not merchant:
                merchant = f"unknown-{i}"
            result.rows.append(
                ParsedRow(
                    date=date,
                    amount=amount,
                    description=description,
                    merchant=merchant,
                )
            )
        except (ValueError, KeyError) as exc:
            result.errors.append(f"Row {i}: {exc}")
    return result


def _row_amount(row: dict, mapping: ColumnMapping) -> float:
    if mapping.amount:
        amount = _parse_amount(row[mapping.amount])
        return -amount if mapping.flip_sign else amount
    debit = _parse_amount(row.get(mapping.debit, "")) if mapping.debit else 0.0
    credit = _parse_amount(row.get(mapping.credit, "")) if mapping.credit else 0.0
    # Debits are money out (negative); credits are money in (positive).
    return credit - abs(debit)


def import_transactions(
    conn,
    text: str,
    mapping: ColumnMapping,
    *,
    account_id: str,
    member_id: str | None = None,
    run_detection: bool = True,
) -> dict:
    """Parse and persist transactions from CSV text.

    Returns a summary: imported/skipped counts, parse errors, and (if
    ``run_detection``) how many recurring subscriptions were detected after.
    """
    from src import db
    from src.sync.subscriptions import run_subscription_detection

    parsed = parse_csv(text, mapping)
    account_hash = db.hash_pii(account_id)
    member_hash = db.hash_pii(member_id) if member_id else None

    # Ensure the destination account exists so the mind map can link the
    # imported transactions. Don't clobber an account the user already defined.
    existing = conn.execute(
        "SELECT 1 FROM accounts WHERE account_hash = ?", (account_hash,)
    ).fetchone()
    if not existing:
        db.upsert_account(
            conn,
            account_hash,
            name=account_id,
            bucket_type="BUCKET_TAXABLE",
            member_hash=member_hash,
        )

    imported = 0
    for r in parsed.rows:
        db.insert_transaction(
            conn,
            account_hash=account_hash,
            amount=r.amount,
            date=r.date,
            merchant_hash=db.hash_pii(r.merchant),
            member_hash=member_hash,
            description_tokens=db.tokenize_description(r.description),
        )
        imported += 1

    detected = 0
    if run_detection and imported:
        detected = len(run_subscription_detection(conn))

    return {
        "imported": imported,
        "skipped": len(parsed.errors),
        "errors": parsed.errors,
        "detected": detected,
    }
