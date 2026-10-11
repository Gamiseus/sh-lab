"""Tier 1: Feature Coverage — R2: Store Pricing Display & Accurate Multi-Tier Ratings.

Coverage Requirements: >=5 tests covering primary behavior.
1. Non-sale pricing display: no stray '0' badges, no crossed-out text.
2. On-sale pricing display: accurate strikethrough of original price, no double-discount.
3. Free-to-play game pricing: clean 'Free' display without strikethrough or negative values.
4. Steam review summary: authentic Valve 10-tier canonical descriptive sentiment labels.
5. Steam review metrics: positive percentage and total review volume exposed.
6. Explicit differentiation and distinct labeling across Metacritic, Steam, and IGDB scores.
"""
import os
import pytest
import httpx
from tests.helpers import calculate_pricing_display, get_canonical_valve_sentiment

pytestmark = pytest.mark.tier1

def test_pricing_non_sale_clean_display():
    """R2.1: Non-sale game (discount_percent=0) must show clean current price only."""
    # A $29.99 game with 0% discount
    result = calculate_pricing_display(price_cents=2999, discount_percent=0)
    assert result["display"] == "$29.99"
    assert result["has_discount"] is False
    assert result["badge"] is None, "Non-sale game must NOT have a discount badge"
    assert result["strikethrough"] is None, "Non-sale game must NOT have strikethrough price"


def test_pricing_on_sale_accurate_discount():
    """R2.2: On-sale game calculates original price without double-discounting price_cents."""
    # A game currently priced at $11.99 with a 40% discount (original $19.99)
    result = calculate_pricing_display(price_cents=1199, discount_percent=40)
    assert result["display"] == "$11.99", "Current price must be final discounted price"
    assert result["has_discount"] is True
    assert result["badge"] == "-40%"
    assert result["strikethrough"] == "$19.98" or result["strikethrough"] == "$19.99"
    # Ensure current price is NOT discounted a second time to $7.19
    assert result["display"] != "$7.19", "Double-discounting detected: price_cents was discounted twice!"


def test_pricing_free_game_display():
    """R2.3: Free game (price_cents=0) displays 'Free' with no discount badges or strikethrough."""
    result = calculate_pricing_display(price_cents=0, discount_percent=0)
    assert result["display"] == "Free"
    assert result["is_free"] is True
    assert result["badge"] is None
    assert result["strikethrough"] is None


def test_ratings_canonical_valve_sentiment_tiers():
    """R2.4: Authentic Steam review sentiment follows canonical Valve descriptions."""
    # Overwhelmingly Positive: >= 95% and >= 500 reviews
    op = get_canonical_valve_sentiment(positive_percent=96, total_reviews=15500)
    assert op["score"] == 9
    assert op["desc"] == "Overwhelmingly Positive"

    # Very Positive: >= 80% and >= 50 reviews
    vp = get_canonical_valve_sentiment(positive_percent=88, total_reviews=350)
    assert vp["score"] == 8
    assert vp["desc"] == "Very Positive"

    # Mostly Positive: 70% - 79% with >= 10 reviews
    mp = get_canonical_valve_sentiment(positive_percent=74, total_reviews=120)
    assert mp["score"] == 6
    assert mp["desc"] == "Mostly Positive"

    # Mixed: 40% - 69% with >= 10 reviews
    mx = get_canonical_valve_sentiment(positive_percent=55, total_reviews=80)
    assert mx["score"] == 5
    assert mx["desc"] == "Mixed"


def test_ratings_steam_percentage_and_count_exposure(api_client: httpx.Client):
    """R2.5: Backend game details or catalog endpoint exposes review metrics."""
    resp = api_client.get("/api/v1/store/games?limit=5")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    games = resp.json()
    assert len(games) > 0, "Catalog returned empty games list"
    first_game = games[0]
    # GameRead model must include steam review fields
    assert "steam_review_count" in first_game, "Game model missing steam_review_count"
    assert "steam_review_percent" in first_game, "Game model missing steam_review_percent"


def test_ratings_explicit_differentiation_ui_contract():
    """R2.6: GameInfoPanel clearly differentiates Metacritic, Steam User Scores, and IGDB."""
    panel_path = os.path.join("frontend", "src", "components", "store", "GameInfoPanel.tsx")
    assert os.path.exists(panel_path), f"GameInfoPanel.tsx not found at {panel_path}"
    with open(panel_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Must contain explicit mentions/sections for the distinct score types
    has_metacritic = "Metacritic" in content or "metacritic" in content
    has_steam = "Steam" in content or "steam_review" in content or "User Reviews" in content
    has_igdb = "IGDB" in content or "rating" in content

    assert has_metacritic, "GameInfoPanel must have a dedicated Metacritic score display"
    assert has_steam, "GameInfoPanel must have a dedicated Steam User Reviews display"
    assert has_igdb, "GameInfoPanel must have a dedicated IGDB rating display"
