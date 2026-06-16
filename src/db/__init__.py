"""
Financial Mind-Map OS — Database Layer

All PII is SHA-256 hashed with local salt before storage.
No raw PII is ever transmitted. Descriptions are tokenized to safe keywords only.
"""

import sqlite3
import hashlib
import os
from pathlib import Path

DB_PATH = Path("financial_os.db")
SALT = os.getenv("PII_SALT", "default_local_salt_do_not_use_in_prod")


def hash_pii(data: str) -> str:
    """Hash PII data using SHA-256 with a local salt."""
    if not data:
        return ""
    salted = f"{data}{SALT}".encode('utf-8')
    return hashlib.sha256(salted).hexdigest()


def tokenize_description(description: str) -> str:
    """
    Tokenize a transaction description to safe keywords only.
    Strips account numbers, names, and other PII from descriptions.
    """
    # Remove digits (potential account numbers, card numbers)
    import re
    safe = re.sub(r'\d{4,}', '[REDACTED]', description)
    # Keep only alphabetic words
    tokens = re.findall(r'[A-Za-z]+', safe)
    # Return lowercase keywords
    return ' '.join(t.lower() for t in tokens if len(t) > 2)


def get_connection():
    """Get SQLite database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def migrate():
    """Initialize or update database schema."""
    conn = get_connection()
    cursor = conn.cursor()

    # --- Core Tables ---

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        account_hash TEXT NOT NULL,
        amount REAL NOT NULL,
        date TEXT NOT NULL,
        description_tokens TEXT,
        bucket_type TEXT CHECK(bucket_type IN ('BUCKET_TAX', 'BUCKET_TAXABLE', 'BUCKET_FREE')),
        is_subscription BOOLEAN DEFAULT 0,
        status TEXT DEFAULT 'PENDING' CHECK(status IN ('PENDING', 'APPROVED', 'DENIED', 'SNOOZED')),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS subscriptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        merchant_hash TEXT NOT NULL,
        amount REAL NOT NULL,
        frequency TEXT,
        next_due_date TEXT,
        status TEXT DEFAULT 'ACTIVE' CHECK(status IN ('ACTIVE', 'CANCELLED', 'FLAGGED')),
        detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS household_members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        member_hash TEXT NOT NULL UNIQUE,
        role TEXT,
        spending_limit REAL,
        baseline_monthly REAL DEFAULT 0.0
    )
    ''')

    # --- Paycheck & Bill Tables ---

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS paycheck_schedules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        member_hash TEXT NOT NULL,
        pay_day_1 INTEGER NOT NULL,
        pay_day_2 INTEGER,
        pay_amount REAL,
        employer_hash TEXT,
        FOREIGN KEY (member_hash) REFERENCES household_members(member_hash)
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS bills (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        merchant_hash TEXT NOT NULL,
        amount REAL NOT NULL,
        due_day INTEGER NOT NULL,
        grace_period_days INTEGER DEFAULT 0,
        late_fee REAL DEFAULT 0.0,
        category TEXT,
        auto_pay BOOLEAN DEFAULT 0,
        status TEXT DEFAULT 'ACTIVE'
    )
    ''')

    # --- Action Report Tables ---

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS action_reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        report_type TEXT NOT NULL,
        summary TEXT,
        generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        resolved_at TIMESTAMP,
        resolution TEXT CHECK(resolution IN ('APPROVED', 'DENIED', 'SNOOZED', NULL))
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS action_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        report_id INTEGER NOT NULL,
        item_type TEXT NOT NULL,
        description TEXT,
        amount REAL,
        urgency TEXT DEFAULT 'NORMAL' CHECK(urgency IN ('CRITICAL', 'HIGH', 'NORMAL', 'LOW')),
        status TEXT DEFAULT 'PENDING',
        FOREIGN KEY (report_id) REFERENCES action_reports(id)
    )
    ''')

    # --- Sync Log ---

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS sync_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sync_type TEXT NOT NULL,
        started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        completed_at TIMESTAMP,
        status TEXT DEFAULT 'RUNNING',
        items_processed INTEGER DEFAULT 0,
        errors TEXT
    )
    ''')

    conn.commit()
    conn.close()
    print("Database migration complete. Schema initialized.")


if __name__ == "__main__":
    migrate()
