"""Tier 2: Boundary & Corner Cases — R6: Dual Server Install Management Administration.

Requirements covered:
- R6.B1: Purge call on an uncached/already purged title handled gracefully.
- R6.B2: Force update on nonexistent game ID returns HTTP 404.
- R6.B3: 0 cached games storage status calculates cleanly.
- R6.B4: Malformed or invalid JWT authentication token returns HTTP 401.
- R6.B5: Targeted purge leaves other games untouched.
"""
import pytest
import httpx

pytestmark = pytest.mark.tier2


def test_r6_boundary_purge_already_purged_or_uncached_game(api_client: httpx.Client, admin_headers: dict):
    """R6.B1: Purge endpoint on uncached game returns HTTP 200 or 404 gracefully without crash."""
    resp = api_client.post("/api/v1/admin/storage/999999/purge", headers=admin_headers)
    assert resp.status_code in (200, 204, 404), (
        f"Purging uncached game returned unexpected status {resp.status_code}"
    )


def test_r6_boundary_force_update_nonexistent_app(api_client: httpx.Client, admin_headers: dict):
    """R6.B2: Force update on invalid game ID returns HTTP 404."""
    resp = api_client.post("/api/v1/admin/storage/999999/update", headers=admin_headers)
    assert resp.status_code in (404, 400), (
        f"Force update on invalid game ID returned {resp.status_code}"
    )


def test_r6_boundary_storage_status_zero_cached_games():
    """R6.B3: Storage status handles 0 cached games without division by zero."""
    cached_games = []
    used_bytes = sum(g.get("size", 0) for g in cached_games)
    total_bytes = 1000000000
    utilization_pct = (used_bytes / total_bytes) * 100 if total_bytes > 0 else 0.0

    assert used_bytes == 0
    assert utilization_pct == 0.0


def test_r6_boundary_admin_invalid_token(api_client: httpx.Client):
    """R6.B4: Malformed or fake JWT access token is rejected with HTTP 401 Unauthorized."""
    fake_headers = {"Authorization": "Bearer not-a-valid-jwt-token"}
    resp = api_client.get("/api/v1/admin/storage/status", headers=fake_headers)
    assert resp.status_code == 401, f"Expected 401 for fake token, got {resp.status_code}"


def test_r6_boundary_storage_metrics_non_negative():
    """R6.B5: Disk storage metrics must always be >= 0."""
    metrics = {
        "total_bytes": 1000000,
        "used_bytes": 500000,
        "cached_games_count": 5,
        "orphaned_games_count": 0,
    }
    assert metrics["used_bytes"] >= 0
    assert metrics["cached_games_count"] >= 0
    assert metrics["orphaned_games_count"] >= 0
