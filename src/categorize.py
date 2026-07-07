"""
Auto-categorization — keyword rules over tokenized descriptions.

Fills in a category for transactions that have none, using conservative
keyword rules matched against the PII-safe ``description_tokens``. User
intent always wins: merchant-specific ``category_rules`` (learned when the
user categorizes a transaction inline) are applied first by the callers, and
this pass never overwrites a non-blank category.
"""

from __future__ import annotations

import sqlite3

# Ordered (keyword, category) pairs — first match wins. Keywords are single
# lowercase tokens as produced by ``db.tokenize_description``.
DEFAULT_KEYWORD_RULES: list[tuple[str, str]] = [
    # Streaming / entertainment
    ("netflix", "entertainment"),
    ("spotify", "entertainment"),
    ("hulu", "entertainment"),
    ("disney", "entertainment"),
    ("cinema", "entertainment"),
    ("theater", "entertainment"),
    # Groceries
    ("grocery", "groceries"),
    ("groceries", "groceries"),
    ("supermarket", "groceries"),
    ("market", "groceries"),
    ("kroger", "groceries"),
    ("safeway", "groceries"),
    ("aldi", "groceries"),
    # Transport / fuel
    ("gas", "transport"),
    ("fuel", "transport"),
    ("shell", "transport"),
    ("exxon", "transport"),
    ("chevron", "transport"),
    ("uber", "transport"),
    ("lyft", "transport"),
    ("transit", "transport"),
    ("parking", "transport"),
    ("car", "transport"),
    ("auto", "transport"),
    # Health / fitness
    ("gym", "health"),
    ("fitness", "health"),
    ("pharmacy", "health"),
    ("cvs", "health"),
    ("walgreens", "health"),
    ("dental", "health"),
    ("medical", "health"),
    # Housing & utilities
    ("rent", "housing"),
    ("mortgage", "housing"),
    ("electric", "utilities"),
    ("water", "utilities"),
    ("internet", "utilities"),
    ("comcast", "utilities"),
    ("utility", "utilities"),
    ("utilities", "utilities"),
    # Dining
    ("restaurant", "dining"),
    ("pizza", "dining"),
    ("cafe", "dining"),
    ("coffee", "dining"),
    ("starbucks", "dining"),
    ("diner", "dining"),
    # Shopping / home
    ("amazon", "shopping"),
    ("walmart", "shopping"),
    ("target", "shopping"),
    ("electronics", "shopping"),
    ("gadget", "shopping"),
    ("dept", "shopping"),
    ("hardware", "home"),
    ("depot", "home"),
    ("lowes", "home"),
    # Financial
    ("insurance", "insurance"),
    ("payroll", "income"),
    ("paycheck", "income"),
    ("salary", "income"),
    # Weak fallback — keep last so specific rules above win.
    ("store", "shopping"),
    ("shop", "shopping"),
]


def categorize_tokens(
    tokens: str | None,
    rules: list[tuple[str, str]] = DEFAULT_KEYWORD_RULES,
) -> str | None:
    """Return the first rule category whose keyword appears in ``tokens``."""
    if not tokens:
        return None
    token_set = set(tokens.split())
    for keyword, category in rules:
        if keyword in token_set:
            return category
    return None


def run_auto_categorization(conn: sqlite3.Connection) -> int:
    """Categorize uncategorized transactions by keyword; returns rows updated.

    Only fills blanks — categories set by the user (directly or via their
    learned ``category_rules``) are never touched. Callers should apply
    ``db.apply_category_rules`` first so user rules take precedence.
    """
    rows = conn.execute(
        """
        SELECT id, description_tokens FROM transactions
        WHERE category IS NULL OR category = ''
        """
    ).fetchall()

    updates = []
    for row in rows:
        category = categorize_tokens(row["description_tokens"])
        if category is not None:
            updates.append((category, row["id"]))

    if updates:
        conn.executemany(
            "UPDATE transactions SET category = ? WHERE id = ?", updates
        )
        conn.commit()
    return len(updates)
