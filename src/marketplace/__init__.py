"""
Curated Affiliate Marketplace

Context-aware financial product recommendations that serve as the
primary revenue model for Financial Mind-Map OS.

Revenue Strategy:
- Affiliate links for refinancing, credit cards, investing apps
- Only shown when contextually relevant (e.g., high-interest debt detected)
- Transparent to user: "We earn a commission if you use this link"

Privacy: No user data is shared with affiliates. Recommendations are
generated locally based on the user's financial profile.
"""

from dataclasses import dataclass
from enum import Enum


class ProductCategory(Enum):
    REFINANCING = "refinancing"
    CREDIT_CARD = "credit_card"
    MICRO_INVESTING = "micro_investing"
    SAVINGS = "savings"
    DEBT_CONSOLIDATION = "debt_consolidation"
    INSURANCE = "insurance"


@dataclass
class AffiliateProduct:
    """A financial product recommendation."""
    id: str
    name: str
    category: ProductCategory
    description: str
    affiliate_url: str
    disclosure: str
    min_credit_score: int | None = None
    max_apr: float | None = None
    target_demographic: str | None = None


# Product catalog — these would be managed via admin panel in production
PRODUCT_CATALOG: list[AffiliateProduct] = [
    AffiliateProduct(
        id="lendingtree_refi",
        name="LendingTree",
        category=ProductCategory.REFINANCING,
        description="Compare refinancing offers from multiple lenders. One form, multiple offers.",
        affiliate_url="https://www.lendingtree.com/?ref=fmmos",  # placeholder
        disclosure="We may earn a commission when you apply through this link.",
        min_credit_score=580,
        max_apr=None,
        target_demographic="homeowners_with_debt"
    ),
    AffiliateProduct(
        id="acorns_invest",
        name="Acorns",
        category=ProductCategory.MICRO_INVESTING,
        description="Round up your everyday purchases and invest the spare change automatically.",
        affiliate_url="https://www.acorns.com/?ref=fmmos",  # placeholder
        disclosure="We may earn a commission when you sign up through this link.",
        min_credit_score=None,
        max_apr=None,
        target_demographic="young_adults_18_35"
    ),
    AffiliateProduct(
        id="stash_invest",
        name="Stash",
        category=ProductCategory.MICRO_INVESTING,
        description="Start investing with as little as $5. Fractional shares and guided portfolios.",
        affiliate_url="https://www.stash.com/?ref=fmmos",  # placeholder
        disclosure="We may earn a commission when you sign up through this link.",
        min_credit_score=None,
        max_apr=None,
        target_demographic="young_adults_18_35"
    ),
    AffiliateProduct(
        id="sofi_consolidation",
        name="SoFi",
        category=ProductCategory.DEBT_CONSOLIDATION,
        description="Consolidate high-interest debt into one lower-rate loan. No fees.",
        affiliate_url="https://www.sofi.com/?ref=fmmos",  # placeholder
        disclosure="We may earn a commission when you apply through this link.",
        min_credit_score=680,
        max_apr=12.99,
        target_demographic="professionals_with_multiple_debts"
    ),
]


def get_recommendations(
    credit_score: int | None = None,
    has_high_interest_debt: bool = False,
    user_age_range: str | None = None,
    total_subscriptions_monthly: float = 0.0
) -> list[AffiliateProduct]:
    """
    Generate contextually relevant product recommendations.
    Only recommends products that match the user's situation.
    """
    recommendations = []

    for product in PRODUCT_CATALOG:
        # Filter by credit score eligibility
        if product.min_credit_score and credit_score:
            if credit_score < product.min_credit_score:
                continue

        # Context-aware matching
        if product.category == ProductCategory.REFINANCING and has_high_interest_debt:
            recommendations.append(product)
        elif product.category == ProductCategory.DEBT_CONSOLIDATION and has_high_interest_debt:
            recommendations.append(product)
        elif product.category == ProductCategory.MICRO_INVESTING:
            if user_age_range in ("18-25", "26-35", "young_adults_18_35"):
                recommendations.append(product)

    return recommendations


def format_disclosure() -> str:
    """Standard FTC-compliant affiliate disclosure."""
    return (
        "DISCLOSURE: Financial Mind-Map OS may earn a commission from "
        "partner links displayed in the Marketplace. Recommendations are "
        "generated locally based on your financial profile. No personal "
        "data is shared with partners. You are never required to use "
        "these services."
    )
