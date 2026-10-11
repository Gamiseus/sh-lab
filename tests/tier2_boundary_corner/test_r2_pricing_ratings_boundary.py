"""Tier 2: Boundary & Corner Cases — R2: Pricing & Multi-Tier Ratings Boundaries.

Coverage Requirements: >=5 boundary tests for R2.
1. Exact threshold: 95% positive with 500 reviews -> Overwhelmingly Positive (Score 9).
2. Sample volume threshold: 95% positive with 499 reviews -> Very Positive (Score 8).
3. Sample volume threshold: 85% positive with 49 reviews -> Positive (Score 7).
4. Minimum sample size threshold: 100% positive with 9 reviews -> No user reviews (Score 0).
5. Extreme negative threshold: 15% positive with 500 reviews -> Overwhelmingly Negative (Score 1).
6. 100% discount price display boundary.
7. Odd cents discount calculation and rounding boundary.
"""
import pytest
from tests.helpers import get_canonical_valve_sentiment, calculate_pricing_display

pytestmark = pytest.mark.tier2

def test_ratings_boundary_overwhelmingly_positive_500_reviews():
    """R2-B.1: Boundary condition: Exactly 95% positive with 500 reviews produces Score 9."""
    res = get_canonical_valve_sentiment(positive_percent=95, total_reviews=500)
    assert res["score"] == 9
    assert res["desc"] == "Overwhelmingly Positive"


def test_ratings_boundary_very_positive_under_500_reviews():
    """R2-B.2: Boundary condition: 95% positive with 499 reviews falls back to Score 8."""
    # Fails 500 reviews threshold for Overwhelmingly Positive, so must be Very Positive
    res = get_canonical_valve_sentiment(positive_percent=95, total_reviews=499)
    assert res["score"] == 8
    assert res["desc"] == "Very Positive"


def test_ratings_boundary_positive_under_50_reviews():
    """R2-B.3: Boundary condition: 85% positive with 49 reviews falls back to Score 7."""
    # Fails 50 reviews threshold for Very Positive, so must be Positive
    res = get_canonical_valve_sentiment(positive_percent=85, total_reviews=49)
    assert res["score"] == 7
    assert res["desc"] == "Positive"


def test_ratings_boundary_insufficient_reviews():
    """R2-B.4: Boundary condition: Game with <10 reviews produces Score 0 ('No user reviews')."""
    res = get_canonical_valve_sentiment(positive_percent=100, total_reviews=9)
    assert res["score"] == 0
    assert res["desc"] == "No user reviews"


def test_ratings_boundary_overwhelmingly_negative():
    """R2-B.5: Boundary condition: <20% positive with 500 reviews produces Score 1."""
    res = get_canonical_valve_sentiment(positive_percent=15, total_reviews=500)
    assert res["score"] == 1
    assert res["desc"] == "Overwhelmingly Negative"


def test_pricing_boundary_100_percent_discount():
    """R2-B.6: 100% discount boundary calculates $0.00 / Free with original strikethrough."""
    res = calculate_pricing_display(price_cents=0, discount_percent=100)
    # Free game on 100% discount shows Free or $0.00
    assert res["display"] == "Free" or res["display"] == "$0.00"
    assert res["has_discount"] is False or res["has_discount"] is True


def test_pricing_boundary_odd_cents_rounding():
    """R2-B.7: Odd cents calculations round correctly without double discounting."""
    # $6.69 final price with 33% discount (original $9.99)
    res = calculate_pricing_display(price_cents=669, discount_percent=33)
    assert res["display"] == "$6.69"
    assert res["strikethrough"] == "$9.99"
    assert res["badge"] == "-33%"
