"""
Financial Mind-Map OS — Database Layer

All PII is SHA-256 hashed with a local salt before storage. No raw PII is ever
transmitted. Descriptions are tokenized to safe keywords only.

This module owns the SQLite schema (:func:`migrate`) and a thin repository of
helpers used by the sync engine, the cash-flow orchestrator and the
visualization layer. Every helper accepts an explicit ``sqlite3.Connection`` so
callers (and tests) control transaction and lifecycle boundaries.

Sign convention for ``transactions.amount``: money *out* (debits, spending) is
negative, money *in* (deposits, income) is positive.
"""

from __future__ import annotations

import hashlib
import re
import sqlite3
from collections.abc import Iterable
from datetime import date
from pathlib import Path
from typing import Any

from src import config


def hash_pii(data: str) -> str:
    """Hash PII data using SHA-256 with a local salt."""
    if not data:
        return ""
    salted = f"{data}{config.PII_SALT}".encode()
    return hashlib.sha256(salted).hexdigest()


def tokenize_description(description: str) -> str:
    """Tokenize a transaction description to safe keywords only.

    Strips account/card numbers and other digit runs, then keeps lowercase
    alphabetic words longer than two characters.
    """
    if not description:
        return ""
    # Drop long digit runs (account/card numbers) up front, then keep only
    # alphabetic keywords longer than two characters.
    safe = re.sub(r"\d{4,}", " ", description)
    tokens = re.findall(r"[A-Za-z]+", safe)
    return " ".join(t.lower() for t in tokens if len(t) > 2)


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    """Open a SQLite connection with row access and WAL journaling.

    When ``db_path`` is omitted the path is resolved lazily from configuration
    (``FMM_DB_PATH``), so the environment can redirect storage at runtime.
    """
    path = Path(db_path) if db_path is not None else config.get_db_path()
    # check_same_thread=False: FastAPI runs sync handlers on a threadpool, so a
    # single per-request connection may be created and used on different worker
    # threads. Each request still gets its own connection and never shares it
    # concurrently, so cross-thread use is safe here.
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, ddl: str) -> None:
    """Add ``column`` to ``table`` if it does not already exist (idempotent)."""
    existing = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
    if column not in existing:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")


def migrate(conn: sqlite3.Connection | None = None) -> None:
    """Initialize or update the database schema (idempotent)."""
    owns_conn = conn is None
    conn = conn or get_connection()
    try:
        cur = conn.cursor()

        # --- Household & accounts ---------------------------------------
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS household_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                member_hash TEXT NOT NULL UNIQUE,
                role TEXT,
                spending_limit REAL,
                baseline_monthly REAL DEFAULT 0.0
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_hash TEXT NOT NULL UNIQUE,
                name TEXT,
                bucket_type TEXT CHECK(
                    bucket_type IN ('BUCKET_TAX', 'BUCKET_TAXABLE', 'BUCKET_FREE')
                ),
                balance REAL DEFAULT 0.0,
                member_hash TEXT,
                FOREIGN KEY (member_hash) REFERENCES household_members(member_hash)
            )
            """
        )

        # --- Transactions ----------------------------------------------
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_hash TEXT NOT NULL,
                merchant_hash TEXT,
                member_hash TEXT,
                amount REAL NOT NULL,
                date TEXT NOT NULL,
                description_tokens TEXT,
                bucket_type TEXT CHECK(
                    bucket_type IN ('BUCKET_TAX', 'BUCKET_TAXABLE', 'BUCKET_FREE')
                ),
                category TEXT,
                is_subscription BOOLEAN DEFAULT 0,
                status TEXT DEFAULT 'PENDING' CHECK(
                    status IN ('PENDING', 'APPROVED', 'DENIED', 'SNOOZED')
                ),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        # Older databases may predate these columns.
        _ensure_column(conn, "transactions", "merchant_hash", "merchant_hash TEXT")
        _ensure_column(conn, "transactions", "member_hash", "member_hash TEXT")
        _ensure_column(conn, "transactions", "category", "category TEXT")

        # --- Subscriptions ---------------------------------------------
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                merchant_hash TEXT NOT NULL UNIQUE,
                label TEXT,
                amount REAL NOT NULL,
                frequency TEXT,
                interval_days INTEGER,
                occurrences INTEGER DEFAULT 0,
                last_charge_date TEXT,
                next_due_date TEXT,
                status TEXT DEFAULT 'ACTIVE' CHECK(
                    status IN ('ACTIVE', 'CANCELLED', 'FLAGGED')
                ),
                detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # --- Paycheck & bill tables ------------------------------------
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS paycheck_schedules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                member_hash TEXT NOT NULL,
                pay_day_1 INTEGER NOT NULL,
                pay_day_2 INTEGER,
                pay_amount REAL,
                employer_hash TEXT,
                FOREIGN KEY (member_hash) REFERENCES household_members(member_hash)
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS bills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                merchant_hash TEXT NOT NULL,
                label TEXT,
                amount REAL NOT NULL,
                due_day INTEGER NOT NULL,
                grace_period_days INTEGER DEFAULT 0,
                late_fee REAL DEFAULT 0.0,
                category TEXT,
                auto_pay BOOLEAN DEFAULT 0,
                status TEXT DEFAULT 'ACTIVE'
            )
            """
        )
        _ensure_column(conn, "bills", "label", "label TEXT")

        # --- Budgets & goals -------------------------------------------
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS category_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                merchant_hash TEXT NOT NULL UNIQUE,
                category TEXT NOT NULL
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS budgets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL UNIQUE,
                monthly_limit REAL NOT NULL
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                label TEXT NOT NULL,
                target_amount REAL NOT NULL,
                current_amount REAL DEFAULT 0.0,
                account_hash TEXT,
                monthly_contribution REAL DEFAULT 0.0,
                last_contributed TEXT
            )
            """
        )
        _ensure_column(conn, "goals", "monthly_contribution", "monthly_contribution REAL DEFAULT 0.0")
        _ensure_column(conn, "goals", "last_contributed", "last_contributed TEXT")

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS balance_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL UNIQUE,
                total REAL NOT NULL,
                bucket_tax REAL DEFAULT 0.0,
                bucket_taxable REAL DEFAULT 0.0,
                bucket_free REAL DEFAULT 0.0
            )
            """
        )

        # --- Action report loop ----------------------------------------
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS action_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_type TEXT NOT NULL,
                summary TEXT,
                generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved_at TIMESTAMP,
                resolution TEXT CHECK(
                    resolution IN ('APPROVED', 'DENIED', 'SNOOZED', NULL)
                )
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS action_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_id INTEGER NOT NULL,
                item_type TEXT NOT NULL,
                description TEXT,
                amount REAL,
                urgency TEXT DEFAULT 'NORMAL' CHECK(
                    urgency IN ('CRITICAL', 'HIGH', 'NORMAL', 'LOW')
                ),
                status TEXT DEFAULT 'PENDING' CHECK(
                    status IN ('PENDING', 'APPROVED', 'DENIED', 'SNOOZED')
                ),
                ref_table TEXT,
                ref_id INTEGER,
                resolved_at TIMESTAMP,
                snooze_until TEXT,
                FOREIGN KEY (report_id) REFERENCES action_reports(id)
            )
            """
        )
        # Older databases may predate the resolution/reference columns.
        _ensure_column(conn, "action_items", "ref_table", "ref_table TEXT")
        _ensure_column(conn, "action_items", "ref_id", "ref_id INTEGER")
        _ensure_column(conn, "action_items", "resolved_at", "resolved_at TIMESTAMP")
        _ensure_column(conn, "action_items", "snooze_until", "snooze_until TEXT")

        # --- Sync log ---------------------------------------------------
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS sync_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sync_type TEXT NOT NULL,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                status TEXT DEFAULT 'RUNNING',
                items_processed INTEGER DEFAULT 0,
                errors TEXT
            )
            """
        )

        conn.commit()
    finally:
        if owns_conn:
            conn.close()


# ---------------------------------------------------------------------------
# Repository helpers
# ---------------------------------------------------------------------------


def upsert_member(
    conn: sqlite3.Connection,
    member_hash: str,
    role: str | None = None,
    spending_limit: float | None = None,
    baseline_monthly: float = 0.0,
) -> None:
    conn.execute(
        """
        INSERT INTO household_members (member_hash, role, spending_limit, baseline_monthly)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(member_hash) DO UPDATE SET
            role = excluded.role,
            spending_limit = excluded.spending_limit,
            baseline_monthly = excluded.baseline_monthly
        """,
        (member_hash, role, spending_limit, baseline_monthly),
    )
    conn.commit()


def get_members(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return list(conn.execute("SELECT * FROM household_members ORDER BY id"))


def upsert_account(
    conn: sqlite3.Connection,
    account_hash: str,
    name: str | None = None,
    bucket_type: str | None = None,
    balance: float = 0.0,
    member_hash: str | None = None,
) -> None:
    conn.execute(
        """
        INSERT INTO accounts (account_hash, name, bucket_type, balance, member_hash)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(account_hash) DO UPDATE SET
            name = excluded.name,
            bucket_type = excluded.bucket_type,
            balance = excluded.balance,
            member_hash = excluded.member_hash
        """,
        (account_hash, name, bucket_type, balance, member_hash),
    )
    conn.commit()


def get_accounts(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return list(conn.execute("SELECT * FROM accounts ORDER BY id"))


def update_account(conn: sqlite3.Connection, account_hash: str, **fields: Any) -> None:
    """Update allowed account fields (name, bucket_type, balance)."""
    allowed = {"name", "bucket_type", "balance"}
    updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
    if not updates:
        return
    set_sql = ", ".join(f"{k} = ?" for k in updates)
    conn.execute(
        f"UPDATE accounts SET {set_sql} WHERE account_hash = ?",
        (*updates.values(), account_hash),
    )
    conn.commit()


def insert_transaction(
    conn: sqlite3.Connection,
    account_hash: str,
    amount: float,
    date: str,
    merchant_hash: str | None = None,
    member_hash: str | None = None,
    description_tokens: str | None = None,
    bucket_type: str | None = None,
    category: str | None = None,
    is_subscription: bool = False,
    status: str = "PENDING",
) -> int:
    cur = conn.execute(
        """
        INSERT INTO transactions (
            account_hash, merchant_hash, member_hash, amount, date,
            description_tokens, bucket_type, category, is_subscription, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            account_hash,
            merchant_hash,
            member_hash,
            amount,
            date,
            description_tokens,
            bucket_type,
            category,
            int(is_subscription),
            status,
        ),
    )
    conn.commit()
    return int(cur.lastrowid)


def get_transactions(
    conn: sqlite3.Connection,
    *,
    member_hash: str | None = None,
    since: str | None = None,
    only_debits: bool = False,
    query: str | None = None,
    category: str | None = None,
    limit: int | None = None,
) -> list[sqlite3.Row]:
    clauses: list[str] = []
    params: list[Any] = []
    if member_hash is not None:
        clauses.append("member_hash = ?")
        params.append(member_hash)
    if since is not None:
        clauses.append("date >= ?")
        params.append(since)
    if only_debits:
        clauses.append("amount < 0")
    if query:
        clauses.append("description_tokens LIKE ?")
        params.append(f"%{query.lower()}%")
    if category:
        clauses.append("category = ?")
        params.append(category)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    limit_sql = f" LIMIT {int(limit)}" if limit else ""
    return list(
        conn.execute(
            f"SELECT * FROM transactions {where} ORDER BY date DESC, id DESC{limit_sql}",
            params,
        )
    )


def get_transaction(conn: sqlite3.Connection, txn_id: int) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM transactions WHERE id = ?", (txn_id,)
    ).fetchone()


def update_transaction(conn: sqlite3.Connection, txn_id: int, **fields: Any) -> None:
    """Update allowed transaction fields (amount, date, category, bucket_type)."""
    allowed = {"amount", "date", "category", "bucket_type", "description_tokens"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return
    set_sql = ", ".join(f"{k} = ?" for k in updates)
    conn.execute(
        f"UPDATE transactions SET {set_sql} WHERE id = ?",
        (*updates.values(), txn_id),
    )
    conn.commit()


def delete_transaction(conn: sqlite3.Connection, txn_id: int) -> None:
    conn.execute("DELETE FROM transactions WHERE id = ?", (txn_id,))
    conn.commit()


def split_transaction(
    conn: sqlite3.Connection, txn_id: int, parts: list[dict]
) -> list[int]:
    """Replace a transaction with several child rows (e.g. by category).

    Each part is ``{amount, category?, description?}``; children inherit the
    parent's account, date, merchant and member. The parent row is removed.
    """
    parent = get_transaction(conn, txn_id)
    if parent is None:
        raise ValueError(f"No transaction with id {txn_id}")
    if not parts:
        raise ValueError("Split requires at least one part")

    new_ids = []
    for part in parts:
        new_ids.append(
            insert_transaction(
                conn,
                account_hash=parent["account_hash"],
                amount=float(part["amount"]),
                date=parent["date"],
                merchant_hash=parent["merchant_hash"],
                member_hash=parent["member_hash"],
                description_tokens=part.get("description") or parent["description_tokens"],
                bucket_type=parent["bucket_type"],
                category=part.get("category"),
                status=parent["status"],
            )
        )
    delete_transaction(conn, txn_id)
    return new_ids


def spending_by_month(
    conn: sqlite3.Connection, *, months: int = 12
) -> list[sqlite3.Row]:
    """Total spending (debits) grouped by calendar month, most recent last."""
    return list(
        conn.execute(
            """
            SELECT substr(date, 1, 7) AS month,
                   ROUND(SUM(-amount), 2) AS spent
            FROM transactions
            WHERE amount < 0
            GROUP BY month
            ORDER BY month DESC
            LIMIT ?
            """,
            (months,),
        )
    )


def spending_by_category(
    conn: sqlite3.Connection, *, since: str | None = None
) -> list[sqlite3.Row]:
    """Total spending (debits) grouped by category, optionally since a date."""
    clause = "AND date >= ?" if since else ""
    params = (since,) if since else ()
    return list(
        conn.execute(
            f"""
            SELECT COALESCE(NULLIF(category, ''), 'uncategorized') AS category,
                   ROUND(SUM(-amount), 2) AS spent
            FROM transactions
            WHERE amount < 0 {clause}
            GROUP BY category
            ORDER BY spent DESC
            """,
            params,
        )
    )


# --- Auto-categorization rules ---------------------------------------------


def upsert_category_rule(
    conn: sqlite3.Connection, merchant_hash: str, category: str
) -> None:
    conn.execute(
        """
        INSERT INTO category_rules (merchant_hash, category) VALUES (?, ?)
        ON CONFLICT(merchant_hash) DO UPDATE SET category = excluded.category
        """,
        (merchant_hash, category),
    )
    conn.commit()


def get_category_rules(conn: sqlite3.Connection) -> dict[str, str]:
    return {
        r["merchant_hash"]: r["category"]
        for r in conn.execute("SELECT merchant_hash, category FROM category_rules")
    }


def apply_category_rules(conn: sqlite3.Connection) -> int:
    """Set categories on still-uncategorized transactions from saved rules."""
    cur = conn.execute(
        """
        UPDATE transactions
        SET category = (
            SELECT category FROM category_rules
            WHERE category_rules.merchant_hash = transactions.merchant_hash
        )
        WHERE (category IS NULL OR category = '')
          AND merchant_hash IN (SELECT merchant_hash FROM category_rules)
        """
    )
    conn.commit()
    return cur.rowcount


# --- Budgets ---------------------------------------------------------------


def upsert_budget(
    conn: sqlite3.Connection, category: str, monthly_limit: float
) -> None:
    conn.execute(
        """
        INSERT INTO budgets (category, monthly_limit) VALUES (?, ?)
        ON CONFLICT(category) DO UPDATE SET monthly_limit = excluded.monthly_limit
        """,
        (category, monthly_limit),
    )
    conn.commit()


def get_budgets(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return list(conn.execute("SELECT * FROM budgets ORDER BY category"))


def delete_budget(conn: sqlite3.Connection, category: str) -> None:
    conn.execute("DELETE FROM budgets WHERE category = ?", (category,))
    conn.commit()


# --- Goals -----------------------------------------------------------------


def insert_goal(
    conn: sqlite3.Connection,
    label: str,
    target_amount: float,
    *,
    current_amount: float = 0.0,
    account_hash: str | None = None,
    monthly_contribution: float = 0.0,
) -> int:
    cur = conn.execute(
        """
        INSERT INTO goals
            (label, target_amount, current_amount, account_hash, monthly_contribution)
        VALUES (?, ?, ?, ?, ?)
        """,
        (label, target_amount, current_amount, account_hash, monthly_contribution),
    )
    conn.commit()
    return int(cur.lastrowid)


def advance_goals(conn: sqlite3.Connection, today: date) -> list[sqlite3.Row]:
    """Apply each goal's monthly contribution once per calendar month.

    Returns the goals that became fully funded as a result of this run, so the
    engine can celebrate them in the action report.
    """
    month = today.strftime("%Y-%m")
    newly_funded: list[sqlite3.Row] = []
    for goal in get_goals(conn):
        contribution = goal["monthly_contribution"] or 0.0
        if contribution <= 0 or goal["last_contributed"] == month:
            continue
        was_funded = (goal["current_amount"] or 0.0) >= goal["target_amount"]
        new_amount = min(
            goal["target_amount"], (goal["current_amount"] or 0.0) + contribution
        )
        conn.execute(
            "UPDATE goals SET current_amount = ?, last_contributed = ? WHERE id = ?",
            (new_amount, month, goal["id"]),
        )
        if not was_funded and new_amount >= goal["target_amount"]:
            newly_funded.append(get_goal(conn, goal["id"]))
    conn.commit()
    return newly_funded


def get_goals(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return list(conn.execute("SELECT * FROM goals ORDER BY id"))


def update_goal(conn: sqlite3.Connection, goal_id: int, **fields: Any) -> None:
    allowed = {
        "label",
        "target_amount",
        "current_amount",
        "account_hash",
        "monthly_contribution",
    }
    updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
    if not updates:
        return
    set_sql = ", ".join(f"{k} = ?" for k in updates)
    conn.execute(
        f"UPDATE goals SET {set_sql} WHERE id = ?", (*updates.values(), goal_id)
    )
    conn.commit()


def get_goal(conn: sqlite3.Connection, goal_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM goals WHERE id = ?", (goal_id,)).fetchone()


# --- Net worth -------------------------------------------------------------


def net_worth_summary(conn: sqlite3.Connection) -> dict:
    """Current net worth as a total and a breakdown by tax bucket."""
    rows = conn.execute(
        """
        SELECT COALESCE(bucket_type, 'UNBUCKETED') AS bucket,
               ROUND(SUM(balance), 2) AS total
        FROM accounts
        GROUP BY bucket
        """
    ).fetchall()
    by_bucket = {r["bucket"]: r["total"] for r in rows}
    total = round(sum(by_bucket.values()), 2)
    return {"total": total, "by_bucket": by_bucket}


def record_balance_snapshot(conn: sqlite3.Connection, snapshot_date: str) -> None:
    """Record (or replace) the net-worth snapshot for a given date."""
    summary = net_worth_summary(conn)
    by_bucket = summary["by_bucket"]
    conn.execute(
        """
        INSERT INTO balance_snapshots (date, total, bucket_tax, bucket_taxable, bucket_free)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(date) DO UPDATE SET
            total = excluded.total,
            bucket_tax = excluded.bucket_tax,
            bucket_taxable = excluded.bucket_taxable,
            bucket_free = excluded.bucket_free
        """,
        (
            snapshot_date,
            summary["total"],
            by_bucket.get("BUCKET_TAX", 0.0),
            by_bucket.get("BUCKET_TAXABLE", 0.0),
            by_bucket.get("BUCKET_FREE", 0.0),
        ),
    )
    conn.commit()


def get_balance_snapshots(
    conn: sqlite3.Connection, *, limit: int = 24
) -> list[sqlite3.Row]:
    rows = conn.execute(
        "SELECT * FROM balance_snapshots ORDER BY date DESC LIMIT ?", (limit,)
    ).fetchall()
    return list(reversed(rows))  # oldest -> newest


def delete_goal(conn: sqlite3.Connection, goal_id: int) -> None:
    conn.execute("DELETE FROM goals WHERE id = ?", (goal_id,))
    conn.commit()


def upsert_subscription(
    conn: sqlite3.Connection,
    merchant_hash: str,
    amount: float,
    *,
    label: str | None = None,
    frequency: str | None = None,
    interval_days: int | None = None,
    occurrences: int = 0,
    last_charge_date: str | None = None,
    next_due_date: str | None = None,
) -> None:
    conn.execute(
        """
        INSERT INTO subscriptions (
            merchant_hash, label, amount, frequency, interval_days,
            occurrences, last_charge_date, next_due_date
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(merchant_hash) DO UPDATE SET
            label = excluded.label,
            amount = excluded.amount,
            frequency = excluded.frequency,
            interval_days = excluded.interval_days,
            occurrences = excluded.occurrences,
            last_charge_date = excluded.last_charge_date,
            next_due_date = excluded.next_due_date
        """,
        (
            merchant_hash,
            label,
            amount,
            frequency,
            interval_days,
            occurrences,
            last_charge_date,
            next_due_date,
        ),
    )
    conn.commit()


def get_subscriptions(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return list(conn.execute("SELECT * FROM subscriptions ORDER BY amount DESC"))


def get_subscription(conn: sqlite3.Connection, subscription_id: int) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM subscriptions WHERE id = ?", (subscription_id,)
    ).fetchone()


def insert_bill(
    conn: sqlite3.Connection,
    merchant_hash: str,
    amount: float,
    due_day: int,
    *,
    label: str | None = None,
    grace_period_days: int = 0,
    late_fee: float = 0.0,
    category: str | None = None,
    auto_pay: bool = False,
    status: str = "ACTIVE",
) -> int:
    cur = conn.execute(
        """
        INSERT INTO bills (
            merchant_hash, label, amount, due_day, grace_period_days,
            late_fee, category, auto_pay, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            merchant_hash,
            label,
            amount,
            due_day,
            grace_period_days,
            late_fee,
            category,
            int(auto_pay),
            status,
        ),
    )
    conn.commit()
    return int(cur.lastrowid)


def get_bills(conn: sqlite3.Connection, *, active_only: bool = True) -> list[sqlite3.Row]:
    where = "WHERE status = 'ACTIVE'" if active_only else ""
    return list(conn.execute(f"SELECT * FROM bills {where} ORDER BY due_day"))


def get_bill(conn: sqlite3.Connection, bill_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM bills WHERE id = ?", (bill_id,)).fetchone()


def get_bill_by_merchant(
    conn: sqlite3.Connection, merchant_hash: str
) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM bills WHERE merchant_hash = ? LIMIT 1", (merchant_hash,)
    ).fetchone()


def update_bill(conn: sqlite3.Connection, bill_id: int, **fields: Any) -> None:
    """Update allowed bill fields."""
    allowed = {
        "label",
        "amount",
        "due_day",
        "grace_period_days",
        "late_fee",
        "category",
        "auto_pay",
        "status",
    }
    updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
    if not updates:
        return
    if "auto_pay" in updates:
        updates["auto_pay"] = int(updates["auto_pay"])
    set_sql = ", ".join(f"{k} = ?" for k in updates)
    conn.execute(
        f"UPDATE bills SET {set_sql} WHERE id = ?",
        (*updates.values(), bill_id),
    )
    conn.commit()


def insert_paycheck_schedule(
    conn: sqlite3.Connection,
    member_hash: str,
    pay_day_1: int,
    pay_day_2: int | None = None,
    pay_amount: float | None = None,
    employer_hash: str | None = None,
) -> int:
    cur = conn.execute(
        """
        INSERT INTO paycheck_schedules (
            member_hash, pay_day_1, pay_day_2, pay_amount, employer_hash
        ) VALUES (?, ?, ?, ?, ?)
        """,
        (member_hash, pay_day_1, pay_day_2, pay_amount, employer_hash),
    )
    conn.commit()
    return int(cur.lastrowid)


def get_paycheck_schedules(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return list(conn.execute("SELECT * FROM paycheck_schedules ORDER BY id"))


def create_action_report(
    conn: sqlite3.Connection, report_type: str, summary: str = ""
) -> int:
    cur = conn.execute(
        "INSERT INTO action_reports (report_type, summary) VALUES (?, ?)",
        (report_type, summary),
    )
    conn.commit()
    return int(cur.lastrowid)


def add_action_item(
    conn: sqlite3.Connection,
    report_id: int,
    item_type: str,
    description: str,
    *,
    amount: float | None = None,
    urgency: str = "NORMAL",
    ref_table: str | None = None,
    ref_id: int | None = None,
) -> int:
    cur = conn.execute(
        """
        INSERT INTO action_items (
            report_id, item_type, description, amount, urgency, ref_table, ref_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (report_id, item_type, description, amount, urgency, ref_table, ref_id),
    )
    conn.commit()
    return int(cur.lastrowid)


def update_report_summary(conn: sqlite3.Connection, report_id: int, summary: str) -> None:
    conn.execute(
        "UPDATE action_reports SET summary = ? WHERE id = ?", (summary, report_id)
    )
    conn.commit()


def get_action_items(conn: sqlite3.Connection, report_id: int) -> list[sqlite3.Row]:
    return list(
        conn.execute(
            "SELECT * FROM action_items WHERE report_id = ? ORDER BY "
            "CASE urgency WHEN 'CRITICAL' THEN 0 WHEN 'HIGH' THEN 1 "
            "WHEN 'NORMAL' THEN 2 ELSE 3 END, id",
            (report_id,),
        )
    )


def get_action_item(conn: sqlite3.Connection, item_id: int) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM action_items WHERE id = ?", (item_id,)
    ).fetchone()


def get_latest_report(conn: sqlite3.Connection) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM action_reports ORDER BY id DESC LIMIT 1"
    ).fetchone()


def set_action_item_status(
    conn: sqlite3.Connection,
    item_id: int,
    status: str,
    *,
    snooze_until: str | None = None,
) -> None:
    conn.execute(
        """
        UPDATE action_items
        SET status = ?, resolved_at = CURRENT_TIMESTAMP, snooze_until = ?
        WHERE id = ?
        """,
        (status, snooze_until, item_id),
    )
    conn.commit()


def set_subscription_status(
    conn: sqlite3.Connection, subscription_id: int, status: str
) -> None:
    conn.execute(
        "UPDATE subscriptions SET status = ? WHERE id = ?", (status, subscription_id)
    )
    conn.commit()


def set_bill_status(conn: sqlite3.Connection, bill_id: int, status: str) -> None:
    conn.execute("UPDATE bills SET status = ? WHERE id = ?", (status, bill_id))
    conn.commit()


def start_sync(conn: sqlite3.Connection, sync_type: str) -> int:
    cur = conn.execute(
        "INSERT INTO sync_log (sync_type, status) VALUES (?, 'RUNNING')",
        (sync_type,),
    )
    conn.commit()
    return int(cur.lastrowid)


def finish_sync(
    conn: sqlite3.Connection,
    sync_id: int,
    *,
    status: str = "COMPLETE",
    items_processed: int = 0,
    errors: str | None = None,
) -> None:
    conn.execute(
        """
        UPDATE sync_log
        SET completed_at = CURRENT_TIMESTAMP, status = ?, items_processed = ?, errors = ?
        WHERE id = ?
        """,
        (status, items_processed, errors, sync_id),
    )
    conn.commit()


def coerce_rows(rows: Iterable[sqlite3.Row]) -> list[dict]:
    """Turn rows into plain dicts (handy for JSON/serialization)."""
    return [dict(r) for r in rows]


if __name__ == "__main__":
    migrate()
    print("Database migration complete. Schema initialized.")
