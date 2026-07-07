"""
Market data — pluggable quote providers for marking holdings to market.

Providers are selected from configuration and require nothing beyond an API
key in the environment; with no key configured the refresh is a quiet no-op,
so the app works fully offline (holdings fall back to cost basis).

Supported providers:

- ``finnhub`` — https://finnhub.io (free tier: 60 calls/min).
  Set ``FMM_FINNHUB_API_KEY``.
- ``alphavantage`` — https://www.alphavantage.co (free tier: 25 calls/day).
  Set ``FMM_ALPHAVANTAGE_API_KEY``.

``FMM_MARKET_DATA_PROVIDER=auto`` (the default) picks whichever has a key.
"""

from __future__ import annotations

import json
import sqlite3
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime

from src import config

_REQUEST_TIMEOUT_SECONDS = 8


@dataclass
class PriceUpdate:
    """A holding symbol marked to a fresh market price."""

    symbol: str
    old_price: float | None
    new_price: float


def _http_get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "financial-mind-map-os"})
    with urllib.request.urlopen(req, timeout=_REQUEST_TIMEOUT_SECONDS) as resp:
        return json.load(resp)


def fetch_quote_finnhub(symbol: str, api_key: str) -> float | None:
    """Current price from Finnhub's /quote endpoint (field ``c``)."""
    url = "https://finnhub.io/api/v1/quote?" + urllib.parse.urlencode(
        {"symbol": symbol, "token": api_key}
    )
    data = _http_get_json(url)
    price = data.get("c")
    return float(price) if price else None


def fetch_quote_alphavantage(symbol: str, api_key: str) -> float | None:
    """Current price from Alpha Vantage's GLOBAL_QUOTE endpoint."""
    url = "https://www.alphavantage.co/query?" + urllib.parse.urlencode(
        {"function": "GLOBAL_QUOTE", "symbol": symbol, "apikey": api_key}
    )
    data = _http_get_json(url).get("Global Quote", {})
    price = data.get("05. price")
    return float(price) if price else None


def resolve_provider() -> tuple[str, callable | None]:
    """Resolve the configured provider to (name, fetch(symbol) -> price|None).

    Returns ``("none", None)`` when no provider is configured — callers treat
    that as "skip the refresh", keeping the app fully functional offline.
    """
    choice = config.MARKET_DATA_PROVIDER.lower()
    finnhub_key = config.FINNHUB_API_KEY
    alpha_key = config.ALPHAVANTAGE_API_KEY

    if choice in ("finnhub", "auto") and finnhub_key:
        return "finnhub", lambda s: fetch_quote_finnhub(s, finnhub_key)
    if choice in ("alphavantage", "auto") and alpha_key:
        return "alphavantage", lambda s: fetch_quote_alphavantage(s, alpha_key)
    return "none", None


def refresh_holding_prices(
    conn: sqlite3.Connection, fetch: callable | None = None
) -> list[PriceUpdate]:
    """Mark every held symbol to its current market price.

    ``fetch`` may be injected for testing; otherwise the configured provider
    is used. Symbols whose quote fails (network, rate limit, unknown ticker)
    are skipped — a partial refresh is still a refresh.
    """
    from src import db

    if fetch is None:
        _, fetch = resolve_provider()
    if fetch is None:
        return []

    rows = conn.execute(
        "SELECT symbol, MAX(last_price) AS last_price FROM holdings GROUP BY symbol"
    ).fetchall()

    now = datetime.now().isoformat(timespec="seconds")
    updates: list[PriceUpdate] = []
    for row in rows:
        try:
            price = fetch(row["symbol"])
        except Exception:
            continue  # skip this symbol; others may still succeed
        if price is None or price <= 0:
            continue
        db.update_symbol_price(conn, row["symbol"], price, now)
        updates.append(
            PriceUpdate(
                symbol=row["symbol"],
                old_price=row["last_price"],
                new_price=price,
            )
        )
    return updates
