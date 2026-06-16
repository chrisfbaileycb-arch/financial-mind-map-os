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
                Visual Mind-Map UI (Obsidian-style)
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
- **Obsidian-Style Visualization:** A full-screen, node-based interactive map of the user's financial life.
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
pip install -r requirements.txt
python -c "from src.db import migrate; migrate()"
python -m src.sync.engine
```
