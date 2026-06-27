"""Tests for the affiliate marketplace targeting logic."""

from __future__ import annotations

from src.marketplace import (
    ProductCategory,
    format_disclosure,
    get_recommendations,
)


def test_high_interest_debt_surfaces_refinancing_and_consolidation():
    recs = get_recommendations(credit_score=700, has_high_interest_debt=True)
    categories = {r.category for r in recs}
    assert ProductCategory.REFINANCING in categories
    assert ProductCategory.DEBT_CONSOLIDATION in categories


def test_no_debt_means_no_refinancing():
    recs = get_recommendations(credit_score=700, has_high_interest_debt=False)
    categories = {r.category for r in recs}
    assert ProductCategory.REFINANCING not in categories
    assert ProductCategory.DEBT_CONSOLIDATION not in categories


def test_young_demographic_gets_micro_investing():
    recs = get_recommendations(user_age_range="18-25")
    categories = {r.category for r in recs}
    assert ProductCategory.MICRO_INVESTING in categories


def test_credit_score_gate_filters_ineligible_products():
    # SoFi consolidation requires a 680+ score; a 600 score should exclude it.
    recs = get_recommendations(credit_score=600, has_high_interest_debt=True)
    ids = {r.id for r in recs}
    assert "sofi_consolidation" not in ids
    # LendingTree (min 580) still qualifies.
    assert "lendingtree_refi" in ids


def test_no_context_yields_no_recommendations():
    assert get_recommendations() == []


def test_disclosure_is_present_and_mentions_commission():
    text = format_disclosure()
    assert "commission" in text.lower()
