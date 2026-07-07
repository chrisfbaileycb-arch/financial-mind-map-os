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
- **Family/household model:** each partner links their own accounts *with their own
  consent* (aggregator OAuth; the app never sees bank passwords) into one shared
  instance. The shared household view and cross-member alerts fall out of the
  existing `household.py` vigilance — **no multi-user auth build required.**
- Small addition: a **"notify these contacts"** list (both partners' email/phone) so
  CRITICAL/HIGH alerts reach both people (Resend/Postmark for email; SMS later).

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

## Footnote — Full multi-user auth (deferred)

Separate logins, per-account privacy between partners, and household isolation are
**only** needed if (a) selling to many separate households or (b) partners want
accounts private from each other. Neither applies to the MVP; revisit at
productization time.

## Footnote — White-label / small business

The Action Report loop + three-bucket model adapts naturally to small business
(Operating / Payroll / Tax Reserve buckets). Potential later pivot; out of MVP scope.
