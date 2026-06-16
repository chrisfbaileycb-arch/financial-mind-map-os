"""
Credit Report Integration Module

Provides free credit report tracking and score monitoring.
Uses annualcreditreport.com (free by law) and open APIs where available.

Privacy note: Credit data is fetched on-demand and displayed locally.
No credit data is stored in the hashed database — it's ephemeral per session.
"""

from dataclasses import dataclass
from typing import Optional, List
from datetime import date


@dataclass
class CreditFactor:
    """A factor affecting the user's credit score."""
    name: str
    impact: str  # 'positive', 'negative', 'neutral'
    description: str
    weight: float  # 0.0 to 1.0 importance


@dataclass
class CreditSnapshot:
    """Point-in-time credit report snapshot."""
    score: int
    score_range: str  # e.g., "300-850"
    rating: str  # 'Excellent', 'Good', 'Fair', 'Poor'
    report_date: date
    factors: List[CreditFactor]
    total_debt: float
    credit_utilization: float  # percentage
    accounts_open: int
    hard_inquiries_12mo: int


def calculate_rating(score: int) -> str:
    """Convert numeric score to human-readable rating."""
    if score >= 800:
        return "Excellent"
    elif score >= 740:
        return "Very Good"
    elif score >= 670:
        return "Good"
    elif score >= 580:
        return "Fair"
    else:
        return "Poor"


def get_improvement_suggestions(snapshot: CreditSnapshot) -> List[str]:
    """Generate actionable suggestions based on credit snapshot."""
    suggestions = []

    if snapshot.credit_utilization > 30:
        suggestions.append(
            f"Your credit utilization is {snapshot.credit_utilization:.0f}%. "
            f"Aim to keep it below 30% — consider paying down balances or requesting limit increases."
        )

    if snapshot.hard_inquiries_12mo > 3:
        suggestions.append(
            f"You have {snapshot.hard_inquiries_12mo} hard inquiries in the last 12 months. "
            f"Avoid new credit applications for 6+ months to let these age off."
        )

    for factor in snapshot.factors:
        if factor.impact == 'negative' and factor.weight > 0.5:
            suggestions.append(f"High-impact issue: {factor.description}")

    if snapshot.score < 670:
        suggestions.append(
            "Consider a secured credit card or credit-builder loan to establish positive payment history."
        )

    return suggestions


def generate_credit_report_links() -> dict:
    """
    Return links to free credit report resources.
    These are the official, legally mandated free sources.
    """
    return {
        "annual_credit_report": {
            "url": "https://www.annualcreditreport.com",
            "description": "Federally mandated free annual credit reports from all 3 bureaus",
            "frequency": "Once per year per bureau (3 total)"
        },
        "credit_karma": {
            "url": "https://www.creditkarma.com",
            "description": "Free credit score and monitoring (TransUnion & Equifax)",
            "frequency": "Weekly updates"
        },
        "discover_scorecard": {
            "url": "https://www.discover.com/free-credit-score/",
            "description": "Free FICO score — no Discover card required",
            "frequency": "Monthly"
        }
    }
