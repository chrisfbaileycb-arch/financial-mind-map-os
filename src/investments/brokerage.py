"""
Brokerage sync — placeholder for the SnapTrade / Plaid Investments integration.

A real implementation will, per connected brokerage:

1. Exchange the user's OAuth connection for an access token (SnapTrade's
   connection portal or Plaid Link in ``investments`` mode).
2. Pull accounts + positions (symbol, quantity, cost basis) and upsert them
   via ``db.upsert_holding`` — the same rows manual entry uses, so the
   mind-map, Net Worth view, and market-data refresh all work unchanged.
3. Run on the sync heartbeat like bank sync.

Configuration (reserved): ``FMM_SNAPTRADE_CLIENT_ID``,
``FMM_SNAPTRADE_CONSUMER_KEY``. Vendor approval is the calendar bottleneck —
apply early, then wire this module.
"""

from __future__ import annotations

import sqlite3


def sync_brokerage_accounts(conn: sqlite3.Connection) -> int:
    """Pull positions from connected brokerages. Placeholder: returns 0."""
    return 0
