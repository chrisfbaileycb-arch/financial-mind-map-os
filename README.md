# Financial Mind-Map OS

Local-first, privacy-sovereign AI operating system for financial management.

## Architecture

```
User → Action Report → [Approve/Deny/Snooze]
                          ↓
                    Sync Engine (4h heartbeat)
                     ↙        ↓        ↘
            Accounts    Subscriptions   Household
                     ↘        ↓        ↙
                    SQLite (PII-Hashed)
```

## Three-Bucket Strategy

| Bucket | Tax Treatment | Examples |
|--------|--------------|----------|
| BUCKET_TAX | Deferred | IRA, 401k, HSA |
| BUCKET_TAXABLE | Taxable | Brokerage, Savings, Checking |
| BUCKET_FREE | Exempt | Roth IRA, 529, Municipal Bonds |

## Modules

- **Sync Engine** — 4-hour heartbeat-driven account reconciliation
- **Subscription Killer** — Predictive recurring fee detection with cancellation alerts
- **Shared Vigilance** — Household member relationship graph with spending spike detection
- **Action Report Loop** — Every sync requires explicit Approve/Deny/Snooze before any operation

## Privacy

All PII is SHA-256 hashed with local salt before storage. No raw PII is ever transmitted. Descriptions are tokenized to safe keywords only.

## Getting Started

```bash
pip install -r requirements.txt
python -c "from src.db import migrate; migrate()"
python -m src.sync.engine
```

## CI/CD

Automated schema validation and test suite on every push via GitHub Actions.
