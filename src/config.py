"""
Central configuration for Financial Mind-Map OS.

All tunables are read from the environment (see ``.env.example``) so the
application stays local-first and configurable without code changes. Values
are read lazily where it matters (e.g. the database path) so tests can point
the engine at a throwaway database.
"""

from __future__ import annotations

import os
from pathlib import Path

try:  # python-dotenv is optional at runtime; load a .env file if present.
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover - dotenv is a convenience, not required.
    pass


def _get_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


# --- Storage ---------------------------------------------------------------

def get_db_path() -> Path:
    """Resolve the SQLite database path at call time.

    Read lazily so a test (or a caller) can set ``FMM_DB_PATH`` before any
    connection is opened.
    """
    return Path(os.getenv("FMM_DB_PATH", "financial_os.db"))


# Default path kept for backwards compatibility / convenience.
DB_PATH = get_db_path()

# --- Privacy ---------------------------------------------------------------

# SHA-256 salt for hashing PII. MUST be overridden in production via PII_SALT.
PII_SALT = os.getenv("PII_SALT", "default_local_salt_do_not_use_in_prod")

# --- Sync engine -----------------------------------------------------------

HEARTBEAT_HOURS = int(os.getenv("FMM_HEARTBEAT_HOURS", "4"))

# --- Subscription Killer heuristic ----------------------------------------

# Minimum number of charges from the same merchant before we call it recurring.
SUB_MIN_OCCURRENCES = int(os.getenv("FMM_SUB_MIN_OCCURRENCES", "3"))

# Allowed relative variation in charge amount (0.05 == ±5%).
SUB_AMOUNT_TOLERANCE = float(os.getenv("FMM_SUB_AMOUNT_TOLERANCE", "0.05"))

# Allowed variation (in days) of the gap between charges vs. the expected
# cadence before we stop treating the series as regular.
SUB_INTERVAL_TOLERANCE_DAYS = int(os.getenv("FMM_SUB_INTERVAL_TOLERANCE_DAYS", "5"))

# --- Price-increase detection ----------------------------------------------

# A recurring charge's new price must exceed the old baseline by at least
# max(MIN_ABS dollars, MIN_REL * old price) to raise a PRICE_INCREASE item.
SUB_PRICE_INCREASE_MIN_ABS = float(os.getenv("FMM_SUB_PRICE_INCREASE_MIN_ABS", "0.50"))
SUB_PRICE_INCREASE_MIN_REL = float(os.getenv("FMM_SUB_PRICE_INCREASE_MIN_REL", "0.03"))

# How many charges must land at the new price before we call it a real change
# (1 == alert on the first increased charge).
SUB_PRICE_MIN_NEW_CHARGES = int(os.getenv("FMM_SUB_PRICE_MIN_NEW_CHARGES", "1"))

# --- Market data / investments ----------------------------------------------

# Quote provider: 'auto' picks whichever key is set; 'finnhub',
# 'alphavantage', or 'none' force a choice. No key -> refresh is a no-op.
MARKET_DATA_PROVIDER = os.getenv("FMM_MARKET_DATA_PROVIDER", "auto")
FINNHUB_API_KEY = os.getenv("FMM_FINNHUB_API_KEY", "")
ALPHAVANTAGE_API_KEY = os.getenv("FMM_ALPHAVANTAGE_API_KEY", "")

# A held symbol moving at least this % between refreshes raises an alert.
PORTFOLIO_MOVE_ALERT_PCT = float(os.getenv("FMM_PORTFOLIO_MOVE_ALERT_PCT", "5"))

# --- Household vigilance ---------------------------------------------------

# A member's current-month spend above ``baseline * SPIKE_FACTOR`` is a spike.
HOUSEHOLD_SPIKE_FACTOR = float(os.getenv("FMM_HOUSEHOLD_SPIKE_FACTOR", "1.5"))
