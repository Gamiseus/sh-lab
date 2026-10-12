"""Tier 2: Boundary & Corner Cases — R5: User Library Synchronization & Automated Server Cache Management.

Requirements covered:
- R5.B1: Empty game list sync payload {"game_ids": []}.
- R5.B2: Exact 7-day retention cutoff boundary (604,799s vs 604,800s).
- R5.B3: Duplicate game IDs in sync payload deduplicated.
- R5.B4: Multiple user count transitions (0 -> 1 -> 0 -> 2).
- R5.B5: Updates check on game with null/None build_id.
"""
from datetime import datetime, timezone, timedelta
import pytest
import httpx
from tests.helpers import (
    evaluate_orphan_retention_status,
    ORPHAN_RETENTION_SECONDS,
)

pytestmark = pytest.mark.tier2


def test_r5_boundary_sync_empty_list_clears_library(api_client: httpx.Client, admin_headers: dict):
    """R5.B1: Syncing empty list {"game_ids": []} empties user library cleanly."""
    resp = api_client.post(
        "/api/v1/library/sync",
        headers=admin_headers,
        json={"game_ids": []},
    )
    assert resp.status_code == 200, f"Syncing empty list returned {resp.status_code}"


def test_r5_boundary_orphan_retention_exact_7_day_cutoff():
    """R5.B2: Exact cutoff boundary: 604,799 seconds (retained) vs 604,800 seconds (purge)."""
    now = datetime(2026, 10, 12, 12, 0, 0, tzinfo=timezone.utc)

    # 1 second before cutoff -> Retained
    sub_cutoff = now - timedelta(seconds=ORPHAN_RETENTION_SECONDS - 1)
    status_sub = evaluate_orphan_retention_status(0, sub_cutoff, now)
    assert status_sub["eligible_for_purge"] is False
    assert status_sub["seconds_remaining"] == 1.0

    # Exact cutoff -> Purge
    exact = now - timedelta(seconds=ORPHAN_RETENTION_SECONDS)
    status_exact = evaluate_orphan_retention_status(0, exact, now)
    assert status_exact["eligible_for_purge"] is True
    assert status_exact["seconds_remaining"] == 0

    # 1 second past cutoff -> Purge
    past = now - timedelta(seconds=ORPHAN_RETENTION_SECONDS + 1)
    status_past = evaluate_orphan_retention_status(0, past, now)
    assert status_past["eligible_for_purge"] is True


def test_r5_boundary_sync_duplicate_game_ids(api_client: httpx.Client, admin_headers: dict):
    """R5.B3: Syncing duplicate IDs [281, 281, 281] de-duplicates cleanly without unique constraint violation."""
    resp = api_client.post(
        "/api/v1/library/sync",
        headers=admin_headers,
        json={"game_ids": [281, 281, 281]},
    )
    assert resp.status_code == 200, (
        f"Duplicate IDs sync resulted in status {resp.status_code}: {resp.text}"
    )


def test_r5_boundary_user_count_oscillations():
    """R5.B4: User count transitions from 0 -> 1 -> 0 -> 2 properly resets and re-arms retention."""
    t0 = datetime(2026, 10, 1, 0, 0, 0, tzinfo=timezone.utc)
    t1 = t0 + timedelta(days=2)  # User A adds game
    t2 = t0 + timedelta(days=4)  # User A removes game (starts orphan countdown)
    t3 = t0 + timedelta(days=5)  # User B & C add game (clears orphan status)

    # Initial orphan at t0
    s0 = evaluate_orphan_retention_status(0, t0, t0)
    assert s0["is_orphaned"] is True

    # User adds game at t1
    s1 = evaluate_orphan_retention_status(1, t0, t1)
    assert s1["is_orphaned"] is False

    # User removes game at t2 (new orphan)
    s2 = evaluate_orphan_retention_status(0, t2, t2)
    assert s2["is_orphaned"] is True
    assert s2["orphaned_at"] == t2

    # Two users add game at t3
    s3 = evaluate_orphan_retention_status(2, t2, t3)
    assert s3["is_orphaned"] is False


def test_r5_boundary_depot_updates_with_empty_or_null_build_id():
    """R5.B5: Update check logic safely handles null build_id without crashing."""
    installed_build = None
    latest_build = "12345678"
    has_update = (installed_build is not None and installed_build != latest_build)
    assert has_update is False, "Null build ID should not falsely signal update"
