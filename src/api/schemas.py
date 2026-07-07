"""Pydantic request/response models for the API layer."""

from __future__ import annotations

from datetime import date as _date
from typing import Literal

from pydantic import BaseModel, Field, field_validator


def _validate_iso_date(value: str) -> str:
    """Reject non-ISO dates before they can reach storage.

    A malformed date would otherwise poison downstream date parsing (e.g.
    recurring-charge detection during sync).
    """
    _date.fromisoformat(value)
    return value

BucketType = Literal["BUCKET_TAX", "BUCKET_TAXABLE", "BUCKET_FREE"]


class ResolveRequest(BaseModel):
    """Resolve an action item via the Action Report Loop."""

    resolution: Literal["APPROVED", "DENIED", "SNOOZED"]
    snooze_days: int = Field(default=7, ge=1, le=365)


class MemberCreate(BaseModel):
    member_id: str = Field(description="Raw member identifier; hashed before storage.")
    role: str | None = None
    spending_limit: float | None = None
    baseline_monthly: float = 0.0


class AccountCreate(BaseModel):
    account_id: str = Field(description="Raw account identifier; hashed before storage.")
    name: str
    bucket_type: BucketType | None = None
    balance: float = 0.0
    member_id: str | None = None


class HoldingCreate(BaseModel):
    account_hash: str = Field(description="Hash of the account holding the position.")
    symbol: str = Field(pattern=r"^[A-Za-z0-9.\-]{1,12}$")
    quantity: float = Field(gt=0)
    cost_basis: float | None = Field(
        default=None, ge=0, description="Per-share cost basis."
    )
    last_price: float | None = Field(default=None, ge=0)
    label: str | None = Field(default=None, max_length=120)


class HoldingUpdate(BaseModel):
    quantity: float | None = Field(default=None, gt=0)
    cost_basis: float | None = Field(default=None, ge=0)
    last_price: float | None = Field(default=None, ge=0)
    label: str | None = Field(default=None, max_length=120)


class BillCreate(BaseModel):
    merchant: str = Field(description="Raw merchant name; hashed before storage.")
    label: str
    amount: float
    due_day: int = Field(ge=1, le=31)
    grace_period_days: int = 0
    late_fee: float = 0.0
    category: str | None = None
    auto_pay: bool = False


class TransactionCreate(BaseModel):
    account_id: str = Field(description="Raw account identifier; hashed before storage.")
    amount: float = Field(description="Negative = money out, positive = money in.")
    date: str = Field(description="ISO date, e.g. 2026-06-27.")
    merchant: str | None = None
    member_id: str | None = None
    description: str | None = None
    bucket_type: BucketType | None = None

    _check_date = field_validator("date")(_validate_iso_date)


class PaycheckScheduleCreate(BaseModel):
    member_id: str
    pay_day_1: int = Field(ge=1, le=31)
    pay_day_2: int | None = Field(default=None, ge=1, le=31)
    pay_amount: float | None = None


class ColumnMappingModel(BaseModel):
    """Maps CSV columns to transaction fields."""

    date: str
    amount: str | None = None
    debit: str | None = None
    credit: str | None = None
    description: str | None = None
    merchant: str | None = None
    flip_sign: bool = False


class AccountUpdate(BaseModel):
    name: str | None = None
    bucket_type: BucketType | None = None
    balance: float | None = None


class BillUpdate(BaseModel):
    label: str | None = None
    amount: float | None = None
    due_day: int | None = Field(default=None, ge=1, le=31)
    grace_period_days: int | None = None
    late_fee: float | None = None
    category: str | None = None
    auto_pay: bool | None = None
    status: str | None = None


class TransactionUpdate(BaseModel):
    amount: float | None = None
    date: str | None = None
    category: str | None = None
    bucket_type: BucketType | None = None

    @field_validator("date")
    @classmethod
    def _check_date(cls, value: str | None) -> str | None:
        if value is not None:
            _validate_iso_date(value)
        return value


class SplitPart(BaseModel):
    amount: float
    category: str | None = None
    description: str | None = None


class TransactionSplit(BaseModel):
    parts: list[SplitPart] = Field(min_length=1)


class BudgetUpsert(BaseModel):
    category: str
    monthly_limit: float = Field(ge=0)


class GoalCreate(BaseModel):
    label: str
    target_amount: float = Field(gt=0)
    current_amount: float = 0.0
    account_id: str | None = None  # raw id; hashed before storage
    monthly_contribution: float = 0.0


class GoalUpdate(BaseModel):
    label: str | None = None
    target_amount: float | None = None
    current_amount: float | None = None
    monthly_contribution: float | None = None


class CsvImportRequest(BaseModel):
    account_id: str = Field(description="Raw account identifier; hashed before storage.")
    member_id: str | None = None
    csv_text: str = Field(
        max_length=5_000_000,  # ~5 MB guardrail against runaway payloads
        description="Raw CSV file contents, including the header row.",
    )
    mapping: ColumnMappingModel
    run_detection: bool = True
