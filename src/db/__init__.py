import sqlite3
import hashlib
import os
import json
from pathlib import Path

DB_PATH = Path("financial_os.db")
SALT = os.getenv("PII_SALT", "default_local_salt_do_not_use_in_prod")

def hash_pii(data: str) -> str:
    """Hash PII data using SHA-256 with a local salt."""
    if not data:
        return ""
    salted = f"{data}{SALT}".encode('utf-8')
    return hashlib.sha256(salted).hexdigest()

def get_connection():
    """Get SQLite database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def migrate():
    """Initialize database schema."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Transactions table with hashed PII
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
    
    # Subscriptions table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS subscriptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        merchant_hash TEXT NOT NULL,
        amount REAL NOT NULL,
        frequency TEXT,
        next_due_date TEXT,
        status TEXT DEFAULT 'ACTIVE'
    )
    ''')
    
    # Household members table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS household_members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        member_hash TEXT NOT NULL,
        role TEXT,
        spending_limit REAL
    )
    ''')
    
    conn.commit()
    conn.close()
    print("Database migration complete. Schema initialized.")

if __name__ == "__main__":
    migrate()
