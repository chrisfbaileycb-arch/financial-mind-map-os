# Financial Mind-Map OS

Local-first, privacy-sovereign AI operating system for financial management, featuring visual mind-mapping and intelligent cash-flow orchestration.

## Architecture

```
User → Action Report → [Approve/Deny/Snooze]
                          ↓
                    Sync Engine (4h heartbeat)
                     ↙        ↓        ↘
            Accounts    Subscriptions   Household
                     ↘        ↓        ↙
                    SQLite (PII-Hashed)
                          ↓
                Visual Mind-Map UI (Interactive)
                          ↓
          Paycheck-to-Bill Cash Flow Orchestrator
```

## Core Features & Modules

### 1. The Engine
- **Sync Engine:** 4-hour heartbeat-driven account reconciliation.
- **Action Report Loop:** Every sync requires explicit Approve/Deny/Snooze before any operation.
- **Subscription Killer:** Predictive recurring fee detection with cancellation alerts.
- **Shared Vigilance:** Household member relationship graph with spending spike detection.

### 2. Intelligent Cash Flow Orchestration
- **Paycheck-to-Bill Alignment:** Automatically maps upcoming bills against user paycheck cycles (e.g., 15th and 30th). Alerts users if a specific bill must be paid from the *current* paycheck to avoid late fees before the *next* paycheck arrives.

### 3. Visual Mind-Map Interface
- **Interactive Visualization:** A full-screen, node-based interactive map of the user's financial life.
- **Mobile Full-Screen:** Designed to be viewed comprehensively on mobile devices, allowing visual thinkers to literally "see" their money flow, liabilities, and assets interconnected.

### 4. Financial Health & Monetization Engine
- **Credit Report Integration:** Built-in free credit report tracking to show users their current standing.
- **Curated Affiliate Marketplace:** Context-aware recommendations for financial improvement:
  - Refinancing options (e.g., LendingTree) when high-interest debt is detected.
  - Micro-investing apps (round-up spending to invest) targeting younger demographics.
  - *Note: This serves as the primary revenue model while keeping the core app free/low-cost.*

## Three-Bucket Strategy

| Bucket | Tax Treatment | Examples |
|--------|--------------|----------|
| BUCKET_TAX | Deferred | IRA, 401k, HSA |
| BUCKET_TAXABLE | Taxable | Brokerage, Savings, Checking |
| BUCKET_FREE | Exempt | Roth IRA, 529, Municipal Bonds |

## Privacy

All PII is SHA-256 hashed with local salt before storage. No raw PII is ever transmitted. Descriptions are tokenized to safe keywords only.

## Getting Started

```bash
# 1. Install (editable, with dev extras for tests + lint)
pip install -e ".[dev]"        # or: pip install -r requirements.txt

# 2. Configure (optional — sensible defaults apply)
cp .env.example .env           # then set a real PII_SALT

# 3. Initialize the database and load sample data
python -m src migrate
python -m src seed

# 4. Run a single sync heartbeat and inspect the Action Report
python -m src sync
python -m src report

# 5. Export the financial mind-map graph (JSON for a D3/Cytoscape frontend)
python -m src graph
```

To run the engine on its scheduled heartbeat (every `FMM_HEARTBEAT_HOURS`):

```bash
python -m src run
```

### Run the app (API + web UI)

The web app is a React + D3 mind-map with an Approve/Deny/Snooze action inbox,
served by the FastAPI backend.

```bash
# 1. Build the frontend bundle (one time, or after UI changes)
cd frontend && npm install && npm run build && cd ..

# 2. Serve the API + UI on http://127.0.0.1:8000
python -m src serve
```

For UI development with hot reload, run the API and Vite dev server in two
terminals:

```bash
python -m src serve          # API on :8000
cd frontend && npm run dev   # UI on :5173, proxies /api to :8000
```

Key API endpoints (full docs at `/docs` when the server is running):

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/sync` | Run a heartbeat, generate the Action Report |
| `GET`  | `/api/report/latest` | Latest report + items |
| `POST` | `/api/items/{id}/resolve` | Approve / Deny / Snooze an item |
| `GET`  | `/api/graph` | Mind-map graph data |
| `POST` | `/api/{accounts,bills,transactions,members}` | Manual data entry |

### What the sample data demonstrates

`python -m src sync` runs the wired engine end-to-end against the seeded
household:

- **Subscription Killer** detects the recurring Netflix / Spotify / Gym charges
  and proposes cancellations.
- **Cash-Flow Orchestrator** flags bills due before the next paycheck as
  `PAY_NOW` and the rest as `UPCOMING` (auto-pay bills are skipped).
- **Household Vigilance** flags a member whose month-to-date spend exceeds their
  limit.

Every finding becomes an **Action Item** on an **Action Report**, awaiting an
explicit Approve / Deny / Snooze.

## Project Layout

```
src/
  config.py          Environment-driven configuration
  db/                SQLite schema, repository helpers, sample-data seeding
  models/            Shared enums/constants
  cashflow/          Paycheck-to-bill orchestrator (Bill mirrors the bills table)
  sync/              Sync engine, subscription killer, household vigilance
  actions.py         Action Report Loop resolution (approve/deny/snooze effects)
  api/               FastAPI app (sync, reports, resolve, graph, data entry)
  credit/            Credit-report helpers (no integration yet)
  marketplace/       Context-aware affiliate recommendations
  visualization/     Mind-map graph builder (sample + live from the DB)
frontend/            React + D3 web UI (mind-map + action inbox)
tests/               pytest suite (db, cashflow, subscriptions, actions, api, …)
```

## Development

```bash
pip install -e ".[dev]"
pytest            # run the test suite
ruff check .      # lint
```

CI runs lint + tests on Python 3.10–3.12 (see `.github/workflows/ci.yml`).
