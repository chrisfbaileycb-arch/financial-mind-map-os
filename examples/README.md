# Sample CSVs

Two example bank/card exports you can drop into the **Import CSV** dialog to try
the app, or import from the command line. They include recurring charges so the
Subscription Killer has something to find.

## `sample_transactions.csv` — single signed amount column

| Field | Column |
|-------|--------|
| Date | `Date` |
| Amount | `Amount` (negative = spending) |
| Description | `Description` |

Leave **Flip sign** unchecked (spending is already negative).

## `sample_debit_credit.csv` — separate debit / credit columns

Choose **Separate debit / credit** mode, then:

| Field | Column |
|-------|--------|
| Date | `Posted Date` |
| Debit | `Debit` |
| Credit | `Credit` |
| Description | `Description` |

## Import from the CLI

```python
from src import db
from src.importer import ColumnMapping, import_transactions

conn = db.get_connection()
with open("examples/sample_transactions.csv") as f:
    summary = import_transactions(
        conn, f.read(),
        ColumnMapping(date="Date", amount="Amount", description="Description"),
        account_id="Demo Checking",
    )
print(summary)
```
