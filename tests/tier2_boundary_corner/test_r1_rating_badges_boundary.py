"""Tier 2: Boundary & Corner Cases — R1: Storefront Rating Badges.

Requirements covered:
- R1.B1: Exact sentiment boundary percentages (70%, 69%, 40%, 39%, 0%, 100%).
- R1.B2: Value 0% positive distinction from None (0% renders red badge, None falls back to Metacritic).
- R1.B3: Metacritic score 0 distinction from None (0 renders Metacritic badge, None falls back to IGDB).
- R1.B4: IGDB floating-point rounding corners (.49 vs .50, 99.9 vs 100.0).
- R1.B5: Out-of-bounds rating values handled without throwing uncaught exceptions.
"""
import pytest
from tests.helpers import evaluate_rating_badge_hierarchy

pytestmark = pytest.mark.tier2


def test_r1_boundary_exact_sentiment_thresholds():
    """R1.B1: Test exact boundary thresholds: 70% (emerald), 69% (amber), 40% (amber), 39% (red)."""
    # 70% is the lower boundary for emerald/positive
    b70 = evaluate_rating_badge_hierarchy(70, None, None)
    assert b70["sentiment"] == "positive"
    assert b70["color_cue"] == "emerald"

    # 69% is the upper boundary for amber/mixed
    b69 = evaluate_rating_badge_hierarchy(69, None, None)
    assert b69["sentiment"] == "mixed"
    assert b69["color_cue"] == "amber"

    # 40% is the lower boundary for amber/mixed
    b40 = evaluate_rating_badge_hierarchy(40, None, None)
    assert b40["sentiment"] == "mixed"
    assert b40["color_cue"] == "amber"

    # 39% is the upper boundary for red/negative
    b39 = evaluate_rating_badge_hierarchy(39, None, None)
    assert b39["sentiment"] == "negative"
    assert b39["color_cue"] == "red"

    # 100% upper boundary
    b100 = evaluate_rating_badge_hierarchy(100, None, None)
    assert b100["sentiment"] == "positive"
    assert b100["color_cue"] == "emerald"


def test_r1_boundary_zero_percent_vs_missing_rating():
    """R1.B2: steam_review_percent=0 must render a red badge, while None falls back to Metacritic."""
    # Explicit 0%
    b_zero = evaluate_rating_badge_hierarchy(steam_percent=0, metacritic_score=85, igdb_rating=80.0)
    assert b_zero["has_badge"] is True
    assert b_zero["badge_type"] == "steam"
    assert b_zero["value"] == 0
    assert b_zero["sentiment"] == "negative"
    assert "0%" in b_zero["display_text"]

    # None falls back to Metacritic 85
    b_none = evaluate_rating_badge_hierarchy(steam_percent=None, metacritic_score=85, igdb_rating=80.0)
    assert b_none["has_badge"] is True
    assert b_none["badge_type"] == "metacritic"
    assert b_none["value"] == 85


def test_r1_boundary_metacritic_zero_vs_missing():
    """R1.B3: metacritic_score=0 must render Metacritic badge, while None falls back to IGDB."""
    # Explicit 0
    b_zero_meta = evaluate_rating_badge_hierarchy(steam_percent=None, metacritic_score=0, igdb_rating=75.0)
    assert b_zero_meta["has_badge"] is True
    assert b_zero_meta["badge_type"] == "metacritic"
    assert b_zero_meta["value"] == 0

    # None falls back to IGDB 75
    b_none_meta = evaluate_rating_badge_hierarchy(steam_percent=None, metacritic_score=None, igdb_rating=75.0)
    assert b_none_meta["has_badge"] is True
    assert b_none_meta["badge_type"] == "igdb"
    assert b_none_meta["value"] == 75


def test_r1_boundary_igdb_rounding_corner_cases():
    """R1.B4: IGDB floating-point ratings round to nearest integer correctly."""
    # Round half-up / standard rounding
    assert evaluate_rating_badge_hierarchy(None, None, 75.4)["value"] == 75
    assert evaluate_rating_badge_hierarchy(None, None, 75.5)["value"] == 76
    assert evaluate_rating_badge_hierarchy(None, None, 99.9)["value"] == 100
    assert evaluate_rating_badge_hierarchy(None, None, 0.4)["value"] == 0


def test_r1_boundary_negative_or_extreme_values():
    """R1.B5: Out-of-bounds percentages (>100 or <0) handled gracefully without failure."""
    # Extreme > 100% clamped or marked positive
    b_over = evaluate_rating_badge_hierarchy(105, None, None)
    assert b_over["has_badge"] is True
    assert b_over["sentiment"] == "positive"

    # Extreme negative < 0 marked negative
    b_under = evaluate_rating_badge_hierarchy(-5, None, None)
    assert b_under["has_badge"] is True
    assert b_under["sentiment"] == "negative"
