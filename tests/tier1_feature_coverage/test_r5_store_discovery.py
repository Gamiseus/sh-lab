"""Tier 1: Feature Coverage — R5: Store Discovery, Smooth Filtering & Top-Rated Sorting.

Coverage Requirements: >=5 tests covering primary behavior.
1. Single category filter executes without PostgreSQL jsonb_path_exists syntax error.
2. Multiple category filters execute valid JSONB containment AND logic.
3. Combining genre and category filters returns filtered games with HTTP 200.
4. Top-Rated endpoint defaults to Steam User Score sorting.
5. Top-Rated endpoint supports sorting by Metacritic score.
6. Top-Rated endpoint supports sorting by IGDB rating.
"""
import os
import pytest
import httpx

pytestmark = pytest.mark.tier1

def test_catalog_single_category_filter(api_client: httpx.Client):
    """R5.1: Category filter query executes without HTTP 500 database syntax error."""
    resp = api_client.get("/api/v1/store/games?category=Single-player")
    assert resp.status_code != 500, (
        f"Backend crashed with HTTP 500 on category query: {resp.text}. "
        "PostgreSQL jsonb_path_exists type mismatch must be replaced with JSONB containment."
    )
    assert resp.status_code == 200, f"Expected 200 OK, got {resp.status_code}"
    games = resp.json()
    assert isinstance(games, list), "Expected list of games in response"
    # Every returned game must contain Single-player in categories if games are returned
    for game in games:
        cats = [c.get("description") for c in (game.get("categories") or [])]
        assert "Single-player" in cats, f"Game {game.get('title')} does not contain Single-player category"


def test_catalog_multiple_categories_filter(api_client: httpx.Client):
    """R5.2: Multiple category parameters execute AND filter logic cleanly."""
    resp = api_client.get("/api/v1/store/games?category=Single-player&category=Steam Achievements")
    assert resp.status_code != 500, f"Backend crashed with 500: {resp.text}"
    assert resp.status_code == 200
    games = resp.json()
    assert isinstance(games, list)
    for game in games:
        cats = [c.get("description") for c in (game.get("categories") or [])]
        assert "Single-player" in cats
        assert "Steam Achievements" in cats


def test_catalog_genre_and_category_combined(api_client: httpx.Client):
    """R5.3: Combining genre and category executes without query errors."""
    resp = api_client.get("/api/v1/store/games?genre=Action&category=Single-player")
    assert resp.status_code != 500, f"Backend crashed with 500: {resp.text}"
    assert resp.status_code == 200
    games = resp.json()
    assert isinstance(games, list)


def test_top_rated_default_sort_steam(api_client: httpx.Client):
    """R5.4: Top-Rated discovery defaults to Steam User Score sorting."""
    resp = api_client.get("/api/v1/store/top-rated?limit=10")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    games = resp.json()
    assert isinstance(games, list)
    assert len(games) > 0, "Top-rated endpoint returned 0 games"
    # Verify results are sorted descending by steam_review_percent
    scores = [g.get("steam_review_percent") for g in games if g.get("steam_review_percent") is not None]
    if len(scores) >= 2:
        for i in range(len(scores) - 1):
            assert scores[i] >= scores[i + 1], f"Games not sorted descending by Steam score: {scores}"


def test_top_rated_metacritic_sort(api_client: httpx.Client):
    """R5.5: Top-Rated endpoint supports sorting by Metacritic."""
    resp = api_client.get("/api/v1/store/top-rated?sort_by=metacritic&limit=10")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    games = resp.json()
    assert isinstance(games, list)
    assert len(games) > 0
    scores = [g.get("metacritic_score") for g in games if g.get("metacritic_score") is not None]
    if len(scores) >= 2:
        for i in range(len(scores) - 1):
            assert scores[i] >= scores[i + 1], f"Games not sorted descending by Metacritic: {scores}"


def test_top_rated_igdb_sort(api_client: httpx.Client):
    """R5.6: Top-Rated endpoint supports sorting by IGDB rating."""
    resp = api_client.get("/api/v1/store/top-rated?sort_by=igdb&limit=10")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    games = resp.json()
    assert isinstance(games, list)
    assert len(games) > 0
    scores = [g.get("rating") for g in games if g.get("rating") is not None]
    if len(scores) >= 2:
        for i in range(len(scores) - 1):
            assert scores[i] >= scores[i + 1], f"Games not sorted descending by IGDB rating: {scores}"
