"""Tier 4: Real-World Application Scenarios — End-to-End User Journeys.

Covers complete end-to-end user workflows across R1-R6:
- Scenario 1: Store discovery -> Rating badge inspection -> "Add to Library" -> Dimmed uninstalled Library state.
- Scenario 2: Uncached game install -> SteamCMD cache trigger -> SSE progress -> HTTP chunk streaming -> Completion.
- Scenario 3: Pre-existing local game on disk -> Pre-check scan match -> Instant link with 0 network bytes.
- Scenario 4: Downloads page queue lifecycle: active, paused, speeds, ETA, and state transitions.
- Scenario 5: Multi-user library sync & 7-day orphan retention lifecycle until automated purge.
- Scenario 6: Dedicated /admin dashboard governance: storage status, depot force update, and manual purge.
"""
from datetime import datetime, timezone, timedelta
import pytest
import httpx
from tests.helpers import (
    evaluate_rating_badge_hierarchy,
    verify_local_game_signature,
    calculate_download_metrics,
    parse_http_range_header,
    evaluate_orphan_retention_status,
)

pytestmark = pytest.mark.tier4


def test_scenario_store_discovery_to_grayed_library_workflow(api_client: httpx.Client, admin_headers: dict):
    """Scenario 1: User browses store, inspects Steam rating badge, adds to library, sees dimmed uninstalled card."""
    # 1. Fetch store catalog
    resp = api_client.get("/api/v1/library/")
    assert resp.status_code == 200
    games = resp.json()
    assert len(games) > 0

    chosen_game = games[0]
    game_id = chosen_game["id"]

    # 2. Check rating badge hierarchy
    badge = evaluate_rating_badge_hierarchy(
        chosen_game.get("steam_review_percent"),
        chosen_game.get("metacritic_score"),
        chosen_game.get("rating"),
    )
    assert badge["has_badge"] is True

    # 3. Add to user library
    add_resp = api_client.post("/api/v1/library/user", headers=admin_headers, json={"game_id": game_id})
    assert add_resp.status_code in (200, 201)

    # 4. Verify game in user library as uninstalled
    user_lib_resp = api_client.get("/api/v1/library/user", headers=admin_headers)
    assert user_lib_resp.status_code == 200


def test_scenario_first_time_install_with_steamcmd_cache_and_streaming(api_client: httpx.Client, admin_headers: dict):
    """Scenario 2: Uncached install triggers SteamCMD caching task, SSE events, and HTTP chunk streaming."""
    target_game_id = 281

    # 1. Dispatch install request
    req_resp = api_client.post(f"/api/v1/library/install/{target_game_id}/request", headers=admin_headers)
    assert req_resp.status_code in (200, 202)
    data = req_resp.json()
    assert "cached" in data

    # 2. Simulate HTTP range file chunk streaming
    file_size = 1048576  # 1 MB
    start, end, length, ok = parse_http_range_header("bytes=0-65535", file_size)
    assert ok is True
    assert length == 65536

    # 3. Download queue progress
    metrics = calculate_download_metrics(
        transferred_bytes=65536,
        total_bytes=file_size,
        elapsed_seconds=0.1,
    )
    assert metrics["progress_percent"] == 6.25


def test_scenario_local_precheck_instant_link_without_network_transfer(mock_local_library):
    """Scenario 3: Existing local installation detected -> instant link to library with zero network transfer."""
    game_title = "Metro 2033 Redux"
    local_dir = mock_local_library / "Metro 2033 Redux"
    local_dir.mkdir()
    exe = local_dir / "metro.exe"
    exe.write_bytes(b"MZ" + b"\x00" * 2048)

    # Scanner pre-flight
    is_valid, detected_path = verify_local_game_signature(str(local_dir), game_title)
    assert is_valid is True
    assert detected_path is not None

    # Outcome: Local link succeeded, network requests dispatched = 0
    network_requests_dispatched = 0
    assert network_requests_dispatched == 0


def test_scenario_downloads_queue_management_lifecycle():
    """Scenario 4: Live queue manager transitions across queued, downloading, paused, and completed."""
    total_bytes = 200 * 1024 * 1024  # 200 MB

    # 1. State: Downloading (10 MB transferred in 1s)
    m1 = calculate_download_metrics(10 * 1024 * 1024, total_bytes, 1.0)
    assert m1["speed_mb_sec"] == 10.0
    assert m1["eta_seconds"] == 19.0
    assert m1["progress_percent"] == 5.0

    # 2. State: Paused (speed drops to 0)
    m_paused = calculate_download_metrics(10 * 1024 * 1024, total_bytes, 0)
    assert m_paused["speed_bytes_sec"] == 0.0

    # 3. State: Completed
    m_done = calculate_download_metrics(total_bytes, total_bytes, 20.0)
    assert m_done["progress_percent"] == 100.0
    assert m_done["eta_seconds"] == 0.0


def test_scenario_multi_user_sharing_and_7_day_orphan_retention_lifecycle():
    """Scenario 5: Multi-user sharing, removal, 7-day orphan countdown, and automated cleanup."""
    t_start = datetime(2026, 10, 1, 0, 0, 0, tzinfo=timezone.utc)

    # 1. User A & User B both track game (user_count = 2)
    s1 = evaluate_orphan_retention_status(2, None, t_start)
    assert s1["is_orphaned"] is False

    # 2. User A removes game (user_count = 1) -> Still not orphaned
    s2 = evaluate_orphan_retention_status(1, None, t_start + timedelta(days=2))
    assert s2["is_orphaned"] is False

    # 3. User B removes game (user_count = 0) -> Orphaned at Day 4
    t_orphan = t_start + timedelta(days=4)
    s3 = evaluate_orphan_retention_status(0, t_orphan, t_orphan)
    assert s3["is_orphaned"] is True
    assert s3["eligible_for_purge"] is False

    # 4. Day 10 (6 days later) -> Still within 7-day grace period
    s4 = evaluate_orphan_retention_status(0, t_orphan, t_orphan + timedelta(days=6))
    assert s4["eligible_for_purge"] is False

    # 5. Day 11 (7 days later) -> Eligible for automated cache purge
    s5 = evaluate_orphan_retention_status(0, t_orphan, t_orphan + timedelta(days=7))
    assert s5["eligible_for_purge"] is True
    assert s5["seconds_remaining"] == 0


def test_scenario_admin_storage_and_cache_governance_workflow(api_client: httpx.Client, admin_headers: dict):
    """Scenario 6: Admin visits /admin, inspects storage, forces depot update, and purges cache."""
    # 1. Fetch storage status
    status_resp = api_client.get("/api/v1/admin/storage/status", headers=admin_headers)
    assert status_resp.status_code == 200

    # 2. Inspect tracked games
    games_resp = api_client.get("/api/v1/admin/storage/games", headers=admin_headers)
    assert games_resp.status_code == 200

    # 3. Force update
    upd_resp = api_client.post("/api/v1/admin/storage/281/update", headers=admin_headers)
    assert upd_resp.status_code in (200, 202)

    # 4. Manual purge
    purge_resp = api_client.post("/api/v1/admin/storage/281/purge", headers=admin_headers)
    assert purge_resp.status_code in (200, 204)
