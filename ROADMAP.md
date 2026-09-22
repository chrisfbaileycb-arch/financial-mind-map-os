# Financial Mind-Map OS — Roadmap

This roadmap reflects the current state of the codebase (working engine + React/D3 UI)
and the agreed build strategy: **lead with the differentiators — the visual mind-map and
privacy-first posture — and treat alerts as supporting parity**, since incumbents
(Rocket Money, Monarch) already ship subscription/price alerts and couples features.

## What already works today

- **Engine:** sync heartbeat, Action Report loop (Approve/Deny/Snooze), Subscription
  Killer, paycheck-to-bill Cash Flow Orchestrator, household spending vigilance,
  PII hashing, CSV import.
- **UI:** six views (Map, Net Worth, Cash Flow, Transactions, Spending, Manage) served
  by FastAPI; interactive D3 mind-map with the action inbox.

## Strategic framing

| | |
|---|---|
| **The wedge (why build at all)** | Visual mind-map of your financial life + privacy-first ("your data is yours, PII hashed, never sold") + the Approve/Deny/Snooze intentionality loop. No incumbent does these. |
| **Table stakes (build for parity, don't lead with)** | Subscription & price-increase alerts, couples/household visibility — Rocket Money and Monarch already ship these. |
| **Architecture decision** | Path B: hosted service with privacy as *ethos* (encryption, PII hashing, no data selling) rather than literal local-only — required for bank sync and shared-household alerts. |

## Phase 0 — Deploy & make it touchable

- Deploy the current FastAPI-serves-UI unit to a live URL (Railway / Render / Fly).
- Goal: click through the real app on a phone; validate the experience.

## Phase 1 — Sharpen the wedge (+ cheap parity wins)

No external vendors required; pure Python/JS.

1. **Mind-map polish** — the differentiator. Richer interactions, mobile-friendly
   full-screen graph, clearer money-flow storytelling.
2. **Price-increase alerts** — detect a *sustained* step-up in a recurring charge
   (e.g. Netflix $15.99 → $17.99) and raise a `PRICE_INCREASE` action item.
   Extends `src/sync/subscriptions.py`; parity with Rocket Money's Price Monitoring.
3. **Auto-categorization** — rules-first merchant→category tagging (optionally an
   LLM pass for leftovers) so Spending/Budgets stop showing "uncategorized".

## Phase 2 — Bank connection (this also delivers the family version)

- Integrate **Plaid** (widest coverage; free sandbox) or **Teller** (cheaper, US-only)
  behind the existing import pipeline — Subscription Killer, price alerts, and the
  mind-map work unchanged on live data.
- **Family/household model:** each partner has their own login and explicit
  membership in one household. Each partner may link an individually owned
  account with their own consent; a jointly owned bank account is connected
  once and assigned to the shared household. Scope all accounts, transactions,
  alerts and goals to the household and enforce membership on the server.
  Sharing a view must not require sharing a bank password or app login.
- **Two alert recipients:** a shared account's eligible alerts can reach both
  opted-in members, once per alert per person. Store recipient preferences,
  delivery status and deduplication keys. Allow each person to opt out of a
  channel without removing access to the shared account.
- **User-controlled attention modes:** `daily` (one digest per day), `standard`
  (normal analysis cycle), and `travel` (prompt checks and high-priority alerts
  while away, with an expiry time). These control *our analysis and notification
  cadence*, not the bank's posting speed. A travel-mode request must respect
  the bank aggregator's supported refresh limits, and the UI must display the
  last bank update separately from the last app check. Never label a delayed
  bank feed as live spending detection.
- **Data ingestion:** reconcile provider-added, changed and removed
  transactions idempotently; then rerun the existing household vigilance,
  subscription, price-change and action-report logic. Preserve pending versus
  posted transaction status and avoid duplicate notifications on replacement.

## Phase 3 — Investments & live net worth

- **Brokerage connections:** SnapTrade (Robinhood/Fidelity/Schwab/etc.) or Plaid
  Investments → real holdings and cost basis into the three tax buckets.
- **Market data:** Finnhub / Alpha Vantage / Twelve Data (free tiers) to mark
  holdings to market in the Net Worth view.
- Note: vendor production approval is the calendar bottleneck — start applications
  early; build against sandboxes meanwhile.

## Phase 4 — Monetize & mobile

- Activate the affiliate marketplace (`src/marketplace/`) — refinance, micro-investing.
- **Debt payoff planner** (avalanche/snowball) — pairs with refinance affiliates.
- Package for mobile (the README's hero use case).

## Footnote — Current code versus family product

The current SQLite engine models household members and can flag per-member
spending spikes. It has a single global `FMM_HEARTBEAT_HOURS` scheduler (default
four hours) and a manual Run Sync button. It does not implement bank polling,
per-user daily/travel modes, alert delivery, partner invitations, separate
logins, or household authorization. These are required before offering shared
bank data to separate people in an app-store product.

## Footnote — White-label / small business

The Action Report loop + three-bucket model adapts naturally to small business
(Operating / Payroll / Tax Reserve buckets). Potential later pivot; out of MVP scope.
