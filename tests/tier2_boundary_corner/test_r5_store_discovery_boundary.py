"""Tier 2: Boundary & Corner Cases — R5: Store Discovery & Filtering Boundaries.

Coverage Requirements: >=5 boundary tests for R5.
1. Empty category query parameter returns HTTP 200 without SQL crash.
2. Non-existent category returns empty list with HTTP 200.
3. Category string with URL-encoded spaces and special characters.
4. Invalid sort parameter on /store/top-rated handled gracefully.
5. Zero limit parameter (`limit=0`) handled gracefully.
6. Extreme limit parameter (`limit=5000`) returns all available records safely.
"""
import pytest
import httpx

pytestmark = pytest.mark.tier2

def test_catalog_boundary_empty_category_parameter(api_client: httpx.Client):
    """R5-B.1: Empty category parameter `category=` returns HTTP 200 without database error."""
    resp = api_client.get("/api/v1/store/games?category=")
    assert resp.status_code != 500, f"Backend crashed with 500 on empty category: {resp.text}"
    assert resp.status_code in (200, 422)


def test_catalog_boundary_nonexistent_category(api_client: httpx.Client):
    """R5-B.2: Non-existent category returns HTTP 200 with an empty list."""
    resp = api_client.get("/api/v1/store/games?category=NonExistentCategoryXYZ_9999")
    assert resp.status_code != 500, f"Backend crashed with 500: {resp.text}"
    assert resp.status_code == 200
    games = resp.json()
    assert isinstance(games, list)
    assert len(games) == 0, f"Expected 0 games for non-existent category, got {len(games)}"


def test_catalog_boundary_category_with_spaces_and_special_chars(api_client: httpx.Client):
    """R5-B.3: Categories containing spaces or special characters parse correctly."""
    try:
        resp = api_client.get("/api/v1/store/games?category=Steam%20Cloud")
        assert resp.status_code != 500, f"Backend crashed with 500: {resp.text}"
        assert resp.status_code == 200
        games = resp.json()
        assert isinstance(games, list)
    except httpx.RemoteProtocolError:
        pytest.fail("Backend crashed and dropped connection due to unhandled database query exception")


def test_top_rated_boundary_invalid_sort_param(api_client: httpx.Client):
    """R5-B.4: Invalid sort_by parameter returns HTTP 422 Validation Error or defaults safely."""
    resp = api_client.get("/api/v1/store/top-rated?sort_by=non_existent_field_drop_table")
    # FastAPI Query with regex validation will return 422, or endpoint falls back to default
    assert resp.status_code in (422, 200)
    assert resp.status_code != 500, f"Backend crashed with 500 on invalid sort parameter: {resp.text}"


def test_top_rated_boundary_limit_zero(api_client: httpx.Client):
    """R5-B.5: limit=0 returns empty list with HTTP 200."""
    resp = api_client.get("/api/v1/store/top-rated?limit=0")
    assert resp.status_code == 200
    games = resp.json()
    assert isinstance(games, list)
    assert len(games) == 0


def test_top_rated_boundary_limit_extreme(api_client: httpx.Client):
    """R5-B.6: limit=5000 returns all available catalog games without server error."""
    resp = api_client.get("/api/v1/store/top-rated?limit=5000")
    assert resp.status_code == 200
    games = resp.json()
    assert isinstance(games, list)
    assert len(games) > 0
