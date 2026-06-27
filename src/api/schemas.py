"""Pydantic request/response models for the API layer."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

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


class PaycheckScheduleCreate(BaseModel):
    member_id: str
    pay_day_1: int = Field(ge=1, le=31)
    pay_day_2: int | None = Field(default=None, ge=1, le=31)
    pay_amount: float | None = None
