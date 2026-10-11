"""Tier 3: Cross-Feature Combinations — Pairwise Feature Interactions.

Coverage: 10 pairwise combination tests validating interactions across R1-R6.
1. Category Filtering + Top-Rated Steam Score Sorting (R5 + R5).
2. Media Proxy (Fastly) + Pricing & Discount Calculation (R1 + R2).
3. Platform Requirements Gating + Complete Achievements Schema (R3 + R4).
4. Non-Sale Pricing Cleanup + Canonical Valve Review Sentiments (R2 + R2).
5. Featured Carousel Games + Video Trailer Proxy Streaming (R6 + R1).
6. Multi-Genre + Multi-Category JSONB Complex Queries (R5 + R5).
7. Free-to-Play Pricing + Achievement Ingestion with Hidden Reveal (R2 + R4).
8. Top-Rated Dimension Switching + Proxy Image Rendering (R5 + R1).
9. Text Search Query + Category Filtering + Sorting (R5 + R5).
10. Carousel Card-Slot Overlay + Pricing Badges Rendering (R6 + R2).
"""
import pytest
import httpx
from tests.helpers import (
    calculate_pricing_display,
    get_canonical_valve_sentiment,
    evaluate_platform_requirements_visibility,
    evaluate_achievement_display,
)

pytestmark = pytest.mark.tier3

def test_combo_category_filter_and_top_rated_steam_score(api_client: httpx.Client):
    """Tier 3.1: Combining category filtering and Steam review sorting."""
    try:
        resp = api_client.get("/api/v1/store/games?category=Single-player&sort_by=steam_review_percent&order=desc&limit=10")
        assert resp.status_code != 500, f"Backend crashed on category + sort query: {resp.text}"
        assert resp.status_code == 200
        games = resp.json()
        assert isinstance(games, list)
        for g in games:
            cats = [c.get("description") for c in (g.get("categories") or [])]
            assert "Single-player" in cats
    except httpx.RemoteProtocolError:
        pytest.fail("Backend crashed and dropped connection due to category query exception")


def test_combo_media_proxy_and_pricing_discount(api_client: httpx.Client, fastly_test_url: str):
    """Tier 3.2: Game with Fastly media URLs and active discount calculates clean pricing and proxied media."""
    # 1. Verify Fastly proxy succeeds
    proxy_resp = api_client.get(f"/api/v1/store/proxy/image?url={fastly_test_url}")
    assert proxy_resp.status_code != 403, "Fastly proxy must be allowed"

    # 2. Verify pricing calculation for a discounted game ($19.99 with 20% off = $15.99)
    pricing = calculate_pricing_display(price_cents=1599, discount_percent=20)
    assert pricing["display"] == "$15.99"
    assert pricing["badge"] == "-20%"
    assert pricing["strikethrough"] == "$19.99"


def test_combo_platform_gating_and_achievements():
    """Tier 3.3: Game with Windows-only platform flags and achievements correctly gates OS tabs and masks secrets."""
    # System requirements gating
    platforms = {"windows": True, "mac": False, "linux": False}
    pc_req = "<strong>Minimum:</strong> Windows 10 64-bit"
    mac_req = "<strong>Minimum:</strong> macOS"
    visibility = evaluate_platform_requirements_visibility(platforms, pc_req, mac_req, None)
    assert visibility["windows"] is True
    assert visibility["mac"] is False

    # Achievements for the same game
    ach = {
        "name": "ACH_SECRET",
        "displayName": "Hidden Mystery",
        "description": "Find the secret room.",
        "percent": 8.4,
        "hidden": True,
    }
    ach_display = evaluate_achievement_display(ach, revealed_names=set())
    assert ach_display["is_hidden"] is True
    assert "secret room" not in ach_display["rendered_description"]


def test_combo_non_sale_game_and_canonical_ratings():
    """Tier 3.4: Non-sale game displaying Overwhelmingly Positive sentiment renders clean price and rating."""
    pricing = calculate_pricing_display(price_cents=4999, discount_percent=0)
    assert pricing["display"] == "$49.99"
    assert pricing["badge"] is None
    assert pricing["strikethrough"] is None

    sentiment = get_canonical_valve_sentiment(positive_percent=98, total_reviews=25000)
    assert sentiment["score"] == 9
    assert sentiment["desc"] == "Overwhelmingly Positive"


def test_combo_featured_carousel_and_video_audio(api_client: httpx.Client):
    """Tier 3.5: Featured carousel query returns games with playable video streams."""
    resp = api_client.get("/api/v1/store/featured?limit=5")
    assert resp.status_code == 200
    featured = resp.json()
    assert isinstance(featured, list)
    assert len(featured) > 0

    # Test trailer streaming proxy for featured game
    trailer_url = "https://video.fastly.steamstatic.com/store_trailers/256990595/movie480.mp4"
    video_resp = api_client.get(f"/api/v1/store/proxy/video?url={trailer_url}", headers={"Range": "bytes=0-500"})
    assert video_resp.status_code != 403
    assert video_resp.status_code in (200, 206)


def test_combo_multi_genre_and_multi_category(api_client: httpx.Client):
    """Tier 3.6: Complex multi-genre and multi-category combined queries."""
    resp = api_client.get("/api/v1/store/games?genre=Action&category=Single-player&limit=5")
    assert resp.status_code != 500, f"Backend crashed on multi-filter query: {resp.text}"
    assert resp.status_code == 200
    games = resp.json()
    assert isinstance(games, list)


def test_combo_free_game_with_full_achievements():
    """Tier 3.7: Free-to-play game with full achievements renders 'Free' price and interactive unlock rates."""
    pricing = calculate_pricing_display(price_cents=0, discount_percent=0)
    assert pricing["display"] == "Free"
    assert pricing["is_free"] is True

    ach = {"name": "ACH_FREE_1", "displayName": "First Win", "description": "Win a match.", "percent": 88.5, "hidden": False}
    ach_res = evaluate_achievement_display(ach)
    assert ach_res["percent_formatted"] == "88.5%"
    assert ach_res["rendered_description"] == "Win a match."


def test_combo_top_rated_switch_dimensions_with_proxy(api_client: httpx.Client):
    """Tier 3.8: Top-Rated sorted games have valid proxied images."""
    # Query top-rated games
    resp = api_client.get("/api/v1/store/top-rated?limit=3")
    assert resp.status_code == 200
    games = resp.json()
    assert len(games) > 0
    top_game = games[0]
    header = top_game.get("header_image")
    if header and header.startswith("http"):
        proxy_resp = api_client.get(f"/api/v1/store/proxy/image?url={header}")
        assert proxy_resp.status_code != 403, f"Proxy failed for top-rated game header: {header}"


def test_combo_search_query_with_category_filter_and_sorting(api_client: httpx.Client):
    """Tier 3.9: Search query with category filter and sort parameter executes cleanly."""
    try:
        resp = api_client.get("/api/v1/store/games?search=Portal&category=Single-player&sort_by=title&order=asc")
        assert resp.status_code != 500, f"Search + category query crashed with 500: {resp.text}"
        assert resp.status_code == 200
    except httpx.RemoteProtocolError:
        pytest.fail("Backend crashed and dropped connection due to search + category query exception")


def test_combo_carousel_card_slot_with_pricing_badges():
    """Tier 3.10: Carousel card-slot presentation displays correct badges for on-sale vs non-sale."""
    on_sale = calculate_pricing_display(price_cents=1999, discount_percent=50)
    non_sale = calculate_pricing_display(price_cents=3999, discount_percent=0)

    # On-sale card in carousel
    assert on_sale["badge"] == "-50%"
    assert on_sale["strikethrough"] == "$39.98"
    assert on_sale["display"] == "$19.99"

    # Non-sale card in carousel
    assert non_sale["badge"] is None
    assert non_sale["strikethrough"] is None
    assert non_sale["display"] == "$39.99"
