# Financial Mind-Map OS

**A local-first, privacy-sovereign personal finance OS** — see your entire
financial life as an interactive mind-map, catch subscription creep and price
hikes automatically, align every bill to your paycheck cycle, and track net
worth marked to real market prices. Nothing happens without your explicit
Approve / Deny / Snooze.

> ⚠️ **Disclaimer:** This software is a personal finance organization tool.
> It does **not** provide financial, investment, tax, or legal advice, and
> its detections and projections are estimates that may be wrong. See
> [DISCLAIMER.md](DISCLAIMER.md) before relying on any output.

---

## Why it's different

The default web app now opens on a visual planning home inspired by the separate
React prototype under `prototypes/financial-mind-map-v2/`. It reads account
balances, goals, cash-flow projections, and pending actions from this app's
existing Python API. Its five life-event cards provide editable savings-goal
estimates and can create a goal in the local SQLite database. The estimate is
simple target ÷ monthly contribution; it does not model returns, taxes,
inflation, or automatically transfer money. The existing map and operational
screens remain available from the navigation. The prototype is retained as a
design reference, not served as a second independent finance product.

| | |
|---|---|
| 🧠 **Visual mind-map** | Your accounts, income, bills, and subscriptions as one interactive D3 node graph — see money flow, not just tables. |
| 🔒 **Privacy-sovereign** | All data in a local SQLite file. PII is SHA-256 hashed with your salt before storage; card/account numbers are stripped from descriptions. No cloud, no telemetry, zero outbound requests unless you opt into a market-data key. |
| ✅ **The Action Report Loop** | Every finding — urgent bill, price hike, spending spike — becomes a card requiring an explicit **Approve / Deny / Snooze**. The app never acts silently. |

## Features

### The engine
- **Sync heartbeat** — reconciles and re-analyzes everything on a schedule
  (default every 4 h) or on demand via **Run Sync**.
- **Subscription Killer** — detects recurring charges by amount/cadence
  clustering and asks "Cancel?"; denying promotes the charge to a tracked
  bill the cash-flow planner can see.
- **Price-increase alerts** — recognizes a sustained step-up in a recurring
  charge (*"Netflix went up $2.00 (12.5%) — from $15.99 to $17.99. Accept?"*).
  Approving syncs the tracked bill so projections use the real price.
- **Paycheck-to-bill orchestration** — projects ~45 days of cash flow against
  your paycheck schedule and flags **PAY NOW** when a bill lands before the
  next check.
- **Auto-categorization** — learned per-merchant rules first (your inline
  edits teach it), keyword defaults fill the rest; nothing you set is ever
  overwritten.
- **Shared Vigilance** — per-member spending baselines and limits with
  spike / over-limit alerts for the household.
- **Budgets & goals** — category budgets with overrun flags; savings goals
  with monthly contributions and funded celebrations.

### Investments
- **Holdings** — positions (symbol, quantity, cost basis) attached to
  accounts; net worth, snapshots, and the mind-map all mark them to market.
- **Live prices (optional)** — plug in a free [Finnhub](https://finnhub.io)
  or [Alpha Vantage](https://www.alphavantage.co) API key and every sync
  refreshes quotes; a held symbol moving ≥ 5% raises a portfolio alert. With
  no key the app stays fully offline and values fall back to cost basis.

### The app
Six views served by one FastAPI process: **Map** (mind-map + action inbox),
**Net Worth** (three tax buckets, holdings, history), **Cash Flow**
(paycheck-to-bill timeline), **Transactions** (inline categorize + split),
**Spending** (by month/category + budgets), **Manage** (accounts, bills,
schedules, members), plus **CSV import** with column mapping.

## Quick start

```bash
git clone https://github.com/chrisfbaileycb-arch/financial-mind-map-os
cd financial-mind-map-os
make demo        # install + build UI + seed sample data + serve
# open http://127.0.0.1:8000
```

Step by step instead:

```bash
pip install -e ".[dev]"                # Python engine + dev tools
cp .env.example .env                   # then set a real PII_SALT (required!)
cd frontend && npm install && npm run build && cd ..
python -m src seed                     # optional: sample household
python -m src serve                    # http://127.0.0.1:8000
```

> **Before storing real data:** set a unique `PII_SALT` in `.env`
> (`python -c "import secrets; print(secrets.token_hex(32))"`). The server
> warns at startup while the default salt is in place.

### Load your own data

Click **Import CSV**, pick a bank/card export, and map the columns (date,
amount or debit/credit, description). Accounts are created automatically,
descriptions are tokenized and PII-hashed, and detection runs immediately.
Sample files live in [`examples/`](examples/).

### Common commands

```bash
make help        # all targets
make test        # pytest suite
make lint        # ruff
python -m src sync      # one heartbeat, prints the Action Report
python -m src run       # scheduled heartbeat loop
python -m src graph     # mind-map graph JSON
```

## Configuration

Everything is environment-driven (see [`.env.example`](.env.example) for the
full annotated list):

| Variable | Default | Purpose |
|---|---|---|
| `PII_SALT` | *(dev-only default)* | Salt for PII hashing — **set your own**. |
| `FMM_DB_PATH` | `financial_os.db` | SQLite file location. |
| `FMM_API_HOST` / `FMM_API_PORT` | `127.0.0.1` / `8000` | Server bind (localhost-only by default). |
| `FMM_CORS_ORIGINS` | localhost origins | Allowed browser origins. |
| `FMM_HEARTBEAT_HOURS` | `4` | Sync cadence for `python -m src run`. |
| `FMM_SUB_*` | see file | Subscription-detection tuning. |
| `FMM_SUB_PRICE_INCREASE_*` | `$0.50` / `3%` | Price-hike alert thresholds. |
| `FMM_MARKET_DATA_PROVIDER` | `auto` | `finnhub` / `alphavantage` / `none`. |
| `FMM_FINNHUB_API_KEY` etc. | *(empty)* | Enables live quotes when set. |
| `FMM_PORTFOLIO_MOVE_ALERT_PCT` | `5` | Portfolio-alert threshold. |
| `FMM_HOUSEHOLD_SPIKE_FACTOR` | `1.5` | Spending-spike sensitivity. |

## API

Full interactive docs at `/docs` while the server runs. Highlights:

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/sync` | Run a heartbeat, generate the Action Report |
| `GET`  | `/api/report/latest` | Latest report + items |
| `POST` | `/api/items/{id}/resolve` | Approve / Deny / Snooze an item |
| `GET`  | `/api/graph` | Mind-map graph data |
| `GET/POST/PATCH/DELETE` | `/api/holdings` | Investment positions |
| `POST` | `/api/holdings/refresh` | Mark holdings to market |
| `GET`  | `/api/networth` | Buckets, totals, history |
| `POST` | `/api/import/csv` | Import transactions |
| `GET/POST/PATCH` | `/api/{accounts,bills,transactions,members,budgets,goals}` | Manual data management |

## Architecture

```
User → Action Report → [Approve / Deny / Snooze]
                          ↓
                 Sync Engine (4 h heartbeat)
        ┌──────────┬──────────┼───────────┬─────────────┐
   Subscriptions  Price    Cash-Flow   Household    Portfolio
     (killer)    changes  orchestrator  vigilance  (market data*)
        └──────────┴──────────┼───────────┴─────────────┘
                    SQLite (PII-hashed, local)
                          ↓
        FastAPI ── React + D3 mind-map UI (6 views)

* optional; requires a market-data API key
```

**Three-bucket strategy** for tax-aware organization (not tax advice):

| Bucket | Treatment | Examples |
|--------|-----------|----------|
| `BUCKET_TAX` | Deferred | IRA, 401(k), HSA |
| `BUCKET_TAXABLE` | Taxable | Brokerage, Savings, Checking |
| `BUCKET_FREE` | Exempt | Roth IRA, 529, Municipal bonds |

## Security

Local-first by design: localhost-only binding, CORS allowlist, security
headers, parameterized SQL, validated inputs, PII hashing, and no outbound
traffic unless you configure a market-data key. There is intentionally **no
authentication layer yet** — do not expose the server to the internet. Full
posture and reporting policy: [SECURITY.md](SECURITY.md).

## Testing

```bash
make test    # 120+ tests: engine heuristics, cash flow, API, importer, security
make lint    # ruff
```

## Roadmap

See [ROADMAP.md](ROADMAP.md) — next up: bank aggregation (Plaid/Teller),
consent-based household linking with alert fan-out, brokerage sync
(SnapTrade), deployment packaging, and the affiliate marketplace.

## Legal

- [LICENSE](LICENSE) — proprietary; all rights reserved.
- [DISCLAIMER.md](DISCLAIMER.md) — not financial advice; read before relying
  on any output.
- [SECURITY.md](SECURITY.md) — security posture and vulnerability reporting.
