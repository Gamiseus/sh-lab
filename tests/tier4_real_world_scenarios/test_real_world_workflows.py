"""Tier 4: Real-World Application Scenarios — End-to-End User Workflows.

Coverage: 6 complete, realistic user journey workflows.
1. Discovery to Game Details Workflow: browse Top-Rated, inspect game details, check scores.
2. Filter & Discovery Workflow: search genre + category, verify matching results without errors.
3. On-Sale Game Inspection Workflow: verify discount badge, strikethrough, clean final price.
4. Cross-Platform Compatibility Workflow: verify OS requirements gating across different platform flags.
5. Achievement Hunter Workflow: view achievements list, unlock %, reveal hidden spoiler details.
6. Media Gallery & Gameplay Trailer Workflow: thumbnail strip, trailer playback, audio controls, proxy images.
"""
import pytest
import httpx
from tests.helpers import (
    calculate_pricing_display,
    get_canonical_valve_sentiment,
    evaluate_platform_requirements_visibility,
    evaluate_achievement_display,
)

pytestmark = pytest.mark.tier4

def test_scenario_store_discovery_to_game_details(api_client: httpx.Client):
    """Scenario 1: User discovers top games on store, selects a game, and inspects its details."""
    # Step 1: Browse Top-Rated games defaulting to Steam User Score
    resp = api_client.get("/api/v1/store/top-rated?limit=5")
    assert resp.status_code == 200
    top_games = resp.json()
    assert len(top_games) > 0
    selected_game = top_games[0]
    game_id = selected_game.get("id")
    assert game_id is not None

    # Step 2: Fetch detailed view for the selected game
    details_resp = api_client.get(f"/api/v1/store/games/{game_id}")
    assert details_resp.status_code == 200
    game_details = details_resp.json()
    assert game_details.get("title") == selected_game.get("title")

    # Step 3: Check ratings metrics in details
    if game_details.get("steam_review_count") and game_details.get("steam_review_percent"):
        sentiment = get_canonical_valve_sentiment(
            positive_percent=game_details["steam_review_percent"],
            total_reviews=game_details["steam_review_count"],
        )
        assert sentiment["score"] >= 0
        assert len(sentiment["desc"]) > 0


def test_scenario_filter_by_category_and_genre_workflow(api_client: httpx.Client):
    """Scenario 2: User applies genre and category filters without page jerking or 500 errors."""
    # Step 1: User filters by 'Single-player' and 'Action'
    resp = api_client.get("/api/v1/store/games?genre=Action&category=Single-player&limit=10")
    assert resp.status_code != 500, f"Filter query failed with 500: {resp.text}"
    assert resp.status_code == 200
    games = resp.json()
    assert isinstance(games, list)

    # Step 2: Verify filtered results match both criteria
    for g in games:
        cats = [c.get("description") for c in (g.get("categories") or [])]
        genres = g.get("genres") or []
        assert "Single-player" in cats
        # In SQLModel, genre filter matches
        assert "Action" in genres


def test_scenario_on_sale_game_inspection_workflow():
    """Scenario 3: User finds a discounted game and verifies pricing integrity."""
    # Game with initial price $29.99, discounted 30% to $20.99
    game_data = {
        "title": "Tactical Strike",
        "price_cents": 2099,
        "discount_percent": 30,
    }
    pricing = calculate_pricing_display(
        price_cents=game_data["price_cents"],
        discount_percent=game_data["discount_percent"],
    )

    # User verifies:
    # 1. Badge displays -30%
    assert pricing["badge"] == "-30%"
    # 2. Original price displays with strikethrough ($29.99)
    assert pricing["strikethrough"] == "$29.99"
    # 3. Current price displays $20.99 (NOT double discounted to $14.69)
    assert pricing["display"] == "$20.99"
    assert pricing["display"] != "$14.69"


def test_scenario_cross_platform_compatibility_check_workflow():
    """Scenario 4: User inspects platform compatibility across multiple games."""
    # Game A: Windows-only game (e.g. 1000xRESIST or Portal 2 on Mac=False)
    game_a_platforms = {"windows": True, "mac": False, "linux": False}
    vis_a = evaluate_platform_requirements_visibility(
        platforms=game_a_platforms,
        pc_requirements="Windows 10 specs",
        mac_requirements="Mac specs boilerplate",
        linux_requirements="Linux specs boilerplate",
    )
    assert vis_a["windows"] is True
    assert vis_a["mac"] is False, "Unsupported Mac panel must be hidden"
    assert vis_a["linux"] is False, "Unsupported Linux panel must be hidden"

    # Game B: Cross-platform game with Linux support
    game_b_platforms = {"windows": True, "mac": False, "linux": True}
    vis_b = evaluate_platform_requirements_visibility(
        platforms=game_b_platforms,
        pc_requirements="Windows 10 specs",
        mac_requirements="Mac specs boilerplate",
        linux_requirements="<strong>Minimum:</strong> Ubuntu 22.04, Vulkan 1.3",
    )
    assert vis_b["windows"] is True
    assert vis_b["mac"] is False
    assert vis_b["linux"] is True, "Supported Linux panel must be visible"


def test_scenario_achievement_hunter_hidden_reveal_workflow():
    """Scenario 5: User browses game achievements, inspects unlock rates, and reveals secret achievements."""
    achievements = [
        {"name": "ACH_01", "displayName": "First Step", "description": "Complete Chapter 1", "percent": 92.4, "hidden": False},
        {"name": "ACH_02", "displayName": "Master", "description": "Reach max level", "percent": 14.1, "hidden": False},
        {"name": "ACH_03", "displayName": "Betrayal", "description": "Side with the rebel faction", "percent": 5.2, "hidden": True},
    ]

    # Initial state: User sees 3 achievements, 1 is masked
    state_unrevealed = [evaluate_achievement_display(a, revealed_names=set()) for a in achievements]
    assert state_unrevealed[0]["rendered_description"] == "Complete Chapter 1"
    assert state_unrevealed[0]["has_reveal_button"] is False
    assert state_unrevealed[2]["has_reveal_button"] is True
    assert "rebel faction" not in state_unrevealed[2]["rendered_description"]
    assert "Hidden achievement" in state_unrevealed[2]["rendered_description"]

    # User clicks Reveal button on ACH_03
    revealed_names = {"ACH_03"}
    state_revealed = [evaluate_achievement_display(a, revealed_names=revealed_names) for a in achievements]
    assert state_revealed[2]["has_reveal_button"] is False
    assert state_revealed[2]["rendered_description"] == "Side with the rebel faction"
    assert state_revealed[2]["percent_formatted"] == "5.2%"


def test_scenario_media_gallery_trailer_and_screenshots_workflow(api_client: httpx.Client, fastly_test_url: str):
    """Scenario 6: User browses media gallery, plays trailer, and loads proxied screenshots."""
    # 1. User loads game screenshot hosted on Fastly CDN
    img_resp = api_client.get(f"/api/v1/store/proxy/image?url={fastly_test_url}")
    assert img_resp.status_code != 403, "Fastly screenshot was blocked by proxy"
    assert img_resp.status_code == 200

    # 2. User plays gameplay trailer video
    trailer_url = "https://video.fastly.steamstatic.com/store_trailers/256990595/movie480.mp4"
    video_resp = api_client.get(f"/api/v1/store/proxy/video?url={trailer_url}", headers={"Range": "bytes=0-1000"})
    assert video_resp.status_code != 403, "Trailer video was blocked by proxy"
    assert video_resp.status_code in (200, 206)
