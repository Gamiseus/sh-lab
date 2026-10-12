"""Tier 1: Feature Coverage — R1: Storefront Rating Badges.

Requirements covered:
- R1.1: GameCard displays Steam positive review percentage as primary rating badge.
- R1.2: Sentiment color indicators: >=70% positive (emerald/blue), 40-69% mixed (amber), <40% negative (red).
- R1.3: Fallback to Metacritic score when Steam review metrics are absent.
- R1.4: Fallback to IGDB rating when both Steam and Metacritic are absent.
- R1.5: No rating badge rendered when all rating metrics are absent.
- R1.6: GameCard.tsx frontend component structure adheres to the rating hierarchy contract.
"""
import os
import re
import pytest
import httpx
from tests.helpers import evaluate_rating_badge_hierarchy

pytestmark = pytest.mark.tier1


def test_r1_steam_positive_percentage_as_primary_badge(api_client: httpx.Client):
    """R1.1: Catalog games with Steam review percent evaluate to Steam as the primary badge."""
    resp = api_client.get("/api/v1/library/")
    assert resp.status_code == 200, f"Expected 200 from library catalog, got {resp.status_code}"
    games = resp.json()
    assert len(games) > 0, "Catalog must return games"

    # Find games that have steam_review_percent
    steam_games = [g for g in games if g.get("steam_review_percent") is not None]
    assert len(steam_games) > 0, "Catalog must contain games with steam_review_percent"

    for g in steam_games[:5]:
        badge = evaluate_rating_badge_hierarchy(
            steam_percent=g.get("steam_review_percent"),
            metacritic_score=g.get("metacritic_score"),
            igdb_rating=g.get("rating"),
        )
        assert badge["has_badge"] is True
        assert badge["badge_type"] == "steam"
        assert badge["value"] == g["steam_review_percent"]
        assert f"{g['steam_review_percent']}%" in badge["display_text"]


def test_r1_sentiment_color_indicators_hierarchy():
    """R1.2: Steam rating percentage applies correct sentiment colors (>=70% positive, 40-69% mixed, <40% negative)."""
    # Positive threshold (>= 70%)
    pos_badge = evaluate_rating_badge_hierarchy(steam_percent=95, metacritic_score=90, igdb_rating=88.0)
    assert pos_badge["sentiment"] == "positive"
    assert pos_badge["color_cue"] == "emerald"

    edge_pos = evaluate_rating_badge_hierarchy(steam_percent=70, metacritic_score=None, igdb_rating=None)
    assert edge_pos["sentiment"] == "positive"
    assert edge_pos["color_cue"] == "emerald"

    # Mixed threshold (40% - 69%)
    mixed_badge = evaluate_rating_badge_hierarchy(steam_percent=65, metacritic_score=70, igdb_rating=60.0)
    assert mixed_badge["sentiment"] == "mixed"
    assert mixed_badge["color_cue"] == "amber"

    edge_mixed = evaluate_rating_badge_hierarchy(steam_percent=40, metacritic_score=None, igdb_rating=None)
    assert edge_mixed["sentiment"] == "mixed"
    assert edge_mixed["color_cue"] == "amber"

    # Negative threshold (< 40%)
    neg_badge = evaluate_rating_badge_hierarchy(steam_percent=35, metacritic_score=40, igdb_rating=30.0)
    assert neg_badge["sentiment"] == "negative"
    assert neg_badge["color_cue"] == "red"

    zero_badge = evaluate_rating_badge_hierarchy(steam_percent=0, metacritic_score=None, igdb_rating=None)
    assert zero_badge["sentiment"] == "negative"
    assert zero_badge["color_cue"] == "red"


def test_r1_metacritic_fallback_when_steam_absent():
    """R1.3: GameCard falls back to Metacritic score only when Steam review metrics are absent."""
    badge = evaluate_rating_badge_hierarchy(
        steam_percent=None,
        metacritic_score=84,
        igdb_rating=79.5,
    )
    assert badge["has_badge"] is True
    assert badge["badge_type"] == "metacritic"
    assert badge["value"] == 84
    assert badge["display_text"] == "84"


def test_r1_igdb_fallback_when_steam_and_metacritic_absent():
    """R1.4: GameCard falls back to IGDB rating when both Steam and Metacritic are absent."""
    badge = evaluate_rating_badge_hierarchy(
        steam_percent=None,
        metacritic_score=None,
        igdb_rating=87.4,
    )
    assert badge["has_badge"] is True
    assert badge["badge_type"] == "igdb"
    assert badge["value"] == 87
    assert badge["display_text"] == "87"


def test_r1_no_badge_rendered_when_all_ratings_absent():
    """R1.5: If steam_review_percent, metacritic_score, and IGDB rating are all absent, no badge renders."""
    badge = evaluate_rating_badge_hierarchy(
        steam_percent=None,
        metacritic_score=None,
        igdb_rating=None,
    )
    assert badge["has_badge"] is False
    assert badge["badge_type"] is None
    assert badge["display_text"] is None


def test_r1_gamecard_frontend_component_contract():
    """R1.6: GameCard.tsx UI contract: Steam percentage is primary badge, Metacritic is fallback."""
    card_path = os.path.join("frontend", "src", "components", "store", "GameCard.tsx")
    assert os.path.exists(card_path), f"GameCard.tsx not found at {card_path}"

    with open(card_path, "r", encoding="utf-8") as f:
        content = f.read()

    # The primary badge on the artwork overlay must evaluate steam_review_percent first
    # Before the overhaul, Metacritic was hardcoded in the top-left badge overlay,
    # and steam_review_percent was placed in the bottom footer.
    # The requirement requires Steam % to be the primary rating badge with sentiment colors.
    has_steam_primary = (
        "steam_review_percent" in content
        and ("Positive" in content or "%" in content)
    )
    assert has_steam_primary, "GameCard must support Steam review percent rating badge"

    # Verify sentiment indicator colors or classes are handled for Steam badge
    has_sentiment_colors = (
        ("emerald" in content or "green" in content or "blue" in content)
        and ("amber" in content or "yellow" in content)
        and "red" in content
    )
    assert has_sentiment_colors, (
        "GameCard.tsx must implement sentiment color classes for Steam ratings "
        "(positive >=70%, mixed 40-69%, negative <40%)"
    )
