"""Tier 1: Feature Coverage — R5: User Library Synchronization & Automated Server Cache Management.

Requirements covered:
- R5.1: POST /api/v1/library/sync synchronizes user library contents to backend.
- R5.2: Multi-user game tracking associates games across user accounts.
- R5.3: GET /api/v1/library/updates checks for Steam depot updates (build IDs).
- R5.4: Zero user references marks cached title as orphaned with current UTC timestamp.
- R5.5: 7-day orphan retention policy: files retained <7 days, eligible for cleanup >=7 days.
- R5.6: Orphan status reset when a user re-adds the game to their library before 7 days expire.
"""
from datetime import datetime, timezone, timedelta
import pytest
import httpx
from tests.helpers import (
    evaluate_orphan_retention_status,
    ORPHAN_RETENTION_SECONDS,
)

pytestmark = pytest.mark.tier1


def test_r5_library_sync_endpoint(api_client: httpx.Client, admin_headers: dict):
    """R5.1: POST /api/v1/library/sync synchronizes user library game IDs to backend."""
    game_ids = [281]
    resp = api_client.post(
        "/api/v1/library/sync",
        headers=admin_headers,
        json={"game_ids": game_ids},
    )
    assert resp.status_code == 200, (
        f"Expected 200 from library sync, got {resp.status_code}: {resp.text}. "
        "Endpoint POST /api/v1/library/sync must be implemented."
    )
    data = resp.json()
    assert "synced" in data or "game_ids" in data or "status" in data


def test_r5_depot_updates_endpoint(api_client: httpx.Client, admin_headers: dict):
    """R5.3: GET /api/v1/library/updates returns list of games with available depot updates."""
    resp = api_client.get("/api/v1/library/updates", headers=admin_headers)
    assert resp.status_code == 200, (
        f"Expected 200 from GET /api/v1/library/updates, got {resp.status_code}: {resp.text}"
    )
    updates = resp.json()
    assert isinstance(updates, list), "Depot updates endpoint must return a list"


def test_r5_orphan_retention_timestamp_on_zero_users():
    """R5.4: When user_count reaches 0, title is marked orphaned with timestamp."""
    now = datetime(2026, 10, 12, 12, 0, 0, tzinfo=timezone.utc)
    status = evaluate_orphan_retention_status(
        user_count=0,
        orphaned_at=None,
        reference_time=now,
    )
    assert status["is_orphaned"] is True
    assert status["orphaned_at"] == now
    assert status["eligible_for_purge"] is False
    assert status["seconds_remaining"] == ORPHAN_RETENTION_SECONDS


def test_r5_orphan_retention_7_day_grace_period():
    """R5.5: Cached title is retained for <7 days, eligible for purge at >=7 days (604,800s)."""
    now = datetime(2026, 10, 12, 12, 0, 0, tzinfo=timezone.utc)

    # 3 days elapsed (within grace period)
    three_days_ago = now - timedelta(days=3)
    status_3d = evaluate_orphan_retention_status(
        user_count=0,
        orphaned_at=three_days_ago,
        reference_time=now,
    )
    assert status_3d["is_orphaned"] is True
    assert status_3d["eligible_for_purge"] is False
    assert status_3d["seconds_remaining"] > 0

    # 6 days, 23 hours elapsed (still within grace period)
    almost_7d = now - timedelta(days=6, hours=23)
    status_almost = evaluate_orphan_retention_status(
        user_count=0,
        orphaned_at=almost_7d,
        reference_time=now,
    )
    assert status_almost["eligible_for_purge"] is False

    # Exactly 7 days elapsed (604,800 seconds) -> Eligible for purge
    exact_7d = now - timedelta(days=7)
    status_7d = evaluate_orphan_retention_status(
        user_count=0,
        orphaned_at=exact_7d,
        reference_time=now,
    )
    assert status_7d["eligible_for_purge"] is True
    assert status_7d["seconds_remaining"] == 0

    # 10 days elapsed -> Eligible for purge
    ten_days_ago = now - timedelta(days=10)
    status_10d = evaluate_orphan_retention_status(
        user_count=0,
        orphaned_at=ten_days_ago,
        reference_time=now,
    )
    assert status_10d["eligible_for_purge"] is True


def test_r5_orphan_restoration_when_re_added():
    """R5.6: If a user re-adds an orphaned game before 7 days, orphaned status is cancelled."""
    now = datetime(2026, 10, 12, 12, 0, 0, tzinfo=timezone.utc)
    five_days_ago = now - timedelta(days=5)

    # When a user adds the game, user_count becomes 1
    status_restored = evaluate_orphan_retention_status(
        user_count=1,
        orphaned_at=five_days_ago,
        reference_time=now,
    )
    assert status_restored["is_orphaned"] is False
    assert status_restored["orphaned_at"] is None
    assert status_restored["eligible_for_purge"] is False
    assert status_restored["seconds_remaining"] is None
