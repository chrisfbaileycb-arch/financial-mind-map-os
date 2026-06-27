from enum import Enum


class BucketType(Enum):
    TAX = "BUCKET_TAX"          # Deferred: IRA, 401k, HSA
    TAXABLE = "BUCKET_TAXABLE"  # Taxable: Brokerage, Savings, Checking
    FREE = "BUCKET_FREE"        # Exempt: Roth IRA, 529, Municipal Bonds

class ActionStatus(Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    DENIED = "DENIED"
    SNOOZED = "SNOOZED"
