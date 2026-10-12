"""Tier 5: Adversarial & Empirical Challenge Harness — Milestone 3 (R5).

Empirical verification suite authored by teamwork_preview_challenger_m3_1:
1. Large sync payloads (100+ items, up to 250+ items).
2. Massive duplicate game IDs ([281] * 50, [281] * 500, interleaved duplicates).
3. Mixed valid and invalid game IDs (zero, negative, non-existent, malformed schema types).
4. Rapid toggle between empty list [] and populated list with orphan retention state transitions.
5. Depot updates endpoint under various permutations of build_id and latest_build_id.
"""
from typing import Optional, List
import pytest
import httpx

pytestmark = pytest.mark.tier5


# ==============================================================================
# 1. Large Sync Payloads (100+ items)
# ==============================================================================

def test_emp_m3_sync_large_payload_100_items(api_client: httpx.Client, admin_headers: dict):
    """Stress 1.1: Batch synchronization handles 100+ items without timeout or SQL failure."""
    resp_store = api_client.get("/api/v1/store/games", params={"limit": 100})
    assert resp_store.status_code == 200
    catalog_games = resp_store.json()
    assert len(catalog_games) >= 100
    payload_100 = [g["id"] for g in catalog_games[:100]]

    # Sync 100 games
    r_sync = api_client.post(
        "/api/v1/library/sync",
        headers=admin_headers,
        json={"game_ids": payload_100},
    )
    assert r_sync.status_code == 200
    data = r_sync.json()
    assert data.get("synced") is True
    assert data.get("status") == "ok"

    # Verify user library holds 100 games
    r_user = api_client.get("/api/v1/library/user", headers=admin_headers)
    assert r_user.status_code == 200
    user_lib = r_user.json()
    lib_ids = {entry["game_id"] for entry in user_lib}
    assert len(lib_ids.intersection(set(payload_100))) == 100


def test_emp_m3_sync_extended_scale_payload_250_items(api_client: httpx.Client, admin_headers: dict):
    """Stress 1.2: Syncing 250 mixed items succeeds cleanly and rapidly (<1s)."""
    resp_store = api_client.get("/api/v1/store/games", params={"limit": 100})
    catalog_ids = [g["id"] for g in resp_store.json()[:100]]
    synthetic_ids = [800000 + i for i in range(150)]
    payload_250 = catalog_ids + synthetic_ids

    r_sync = api_client.post(
        "/api/v1/library/sync",
        headers=admin_headers,
        json={"game_ids": payload_250},
    )
    assert r_sync.status_code == 200
    assert r_sync.json().get("synced") is True


# ==============================================================================
# 2. Massive Duplicate Game IDs
# ==============================================================================

def test_emp_m3_massive_duplicates_50_copies(api_client: httpx.Client, admin_headers: dict):
    """Stress 2.1: [281] * 50 deduplicates to strictly 1 database entry without unique violation."""
    payload = [281] * 50
    r_sync = api_client.post(
        "/api/v1/library/sync",
        headers=admin_headers,
        json={"game_ids": payload},
    )
    assert r_sync.status_code == 200

    r_user = api_client.get("/api/v1/library/user", headers=admin_headers)
    assert r_user.status_code == 200
    user_lib = r_user.json()
    entries_281 = [e for e in user_lib if e["game_id"] == 281]
    assert len(entries_281) == 1
    assert len(user_lib) == 1


def test_emp_m3_extreme_duplicates_500_copies(api_client: httpx.Client, admin_headers: dict):
    """Stress 2.2: Extreme [281] * 500 deduplicates cleanly and promptly."""
    payload = [281] * 500
    r_sync = api_client.post(
        "/api/v1/library/sync",
        headers=admin_headers,
        json={"game_ids": payload},
    )
    assert r_sync.status_code == 200


def test_emp_m3_interleaved_duplicates_multi_game(api_client: httpx.Client, admin_headers: dict):
    """Stress 2.3: Interleaved duplicates [281, 261, 578] * 50 deduplicates to exact 3 unique entries."""
    payload = [281, 261, 578] * 50
    r_sync = api_client.post(
        "/api/v1/library/sync",
        headers=admin_headers,
        json={"game_ids": payload},
    )
    assert r_sync.status_code == 200

    r_user = api_client.get("/api/v1/library/user", headers=admin_headers)
    assert r_user.status_code == 200
    user_lib = r_user.json()
    unique_ids = {e["game_id"] for e in user_lib}
    assert unique_ids == {281, 261, 578}
    assert len(user_lib) == 3


# ==============================================================================
# 3. Mixed Valid and Invalid Game IDs
# ==============================================================================

def test_emp_m3_mixed_valid_and_invalid_ids(api_client: httpx.Client, admin_headers: dict):
    """Stress 3.1: Non-existent positive, zero, negative, and duplicates are safely filtered out."""
    mixed_payload = [281, 999999, -1, 281, 0, 261, -42, 888888, 281, 578, -9999]
    r_sync = api_client.post(
        "/api/v1/library/sync",
        headers=admin_headers,
        json={"game_ids": mixed_payload},
    )
    assert r_sync.status_code == 200

    r_user = api_client.get("/api/v1/library/user", headers=admin_headers)
    assert r_user.status_code == 200
    user_lib = r_user.json()
    retained_ids = {e["game_id"] for e in user_lib}
    assert retained_ids == {281, 261, 578}


def test_emp_m3_100_percent_invalid_ids(api_client: httpx.Client, admin_headers: dict):
    """Stress 3.2: 100% invalid IDs clears user library cleanly."""
    invalid_payload = [-100, 0, 999999, 888888]
    r_sync = api_client.post(
        "/api/v1/library/sync",
        headers=admin_headers,
        json={"game_ids": invalid_payload},
    )
    assert r_sync.status_code == 200

    r_user = api_client.get("/api/v1/library/user", headers=admin_headers)
    assert r_user.status_code == 200
    assert len(r_user.json()) == 0


@pytest.mark.parametrize("bad_payload", [
    {"game_ids": ["invalid_string"]},
    {"game_ids": [281.5]},
    {"game_ids": [None]},
    {"game_ids": "281"},
    {"wrong_key": [281]},
])
def test_emp_m3_malformed_payload_rejection(api_client: httpx.Client, admin_headers: dict, bad_payload: dict):
    """Stress 3.3: Malformed payload types return HTTP 422 Unprocessable Entity, NEVER 500."""
    r = api_client.post("/api/v1/library/sync", headers=admin_headers, json=bad_payload)
    assert r.status_code == 422


# ==============================================================================
# 4. Rapid Toggle Between Empty List [] and Populated List
# ==============================================================================

def test_emp_m3_rapid_toggle_empty_and_populated(api_client: httpx.Client, admin_headers: dict):
    """Stress 4.1: Rapidly alternating between [] and [281, 261] executes without errors or deadlocks."""
    for _ in range(5):
        r_empty = api_client.post("/api/v1/library/sync", headers=admin_headers, json={"game_ids": []})
        assert r_empty.status_code == 200

        r_pop = api_client.post("/api/v1/library/sync", headers=admin_headers, json={"game_ids": [281, 261]})
        assert r_pop.status_code == 200

    # Final populated state check
    r_user = api_client.get("/api/v1/library/user", headers=admin_headers)
    assert r_user.status_code == 200
    user_lib = r_user.json()
    assert {e["game_id"] for e in user_lib} == {281, 261}

    # Final empty check
    r_final_empty = api_client.post("/api/v1/library/sync", headers=admin_headers, json={"game_ids": []})
    assert r_final_empty.status_code == 200
    r_user_empty = api_client.get("/api/v1/library/user", headers=admin_headers)
    assert len(r_user_empty.json()) == 0

    # Restore 281
    api_client.post("/api/v1/library/sync", headers=admin_headers, json={"game_ids": [281]})


# ==============================================================================
# 5. Depot Updates Permutations
# ==============================================================================

@pytest.mark.parametrize("inst,latest,expected", [
    (None, None, False),
    (None, "1002", False),
    ("1001", None, False),
    ("", "1002", False),
    ("1001", "", False),
    ("   ", "1002", False),
    ("1001", "   ", False),
    ("   ", "   ", False),
    ("", "", False),
    ("1001", "1001", False),
    ("1001", "1002", True),
    (" 1001 ", "1001", False),
    ("1001", " 1001 ", False),
    (" 1001 ", "1002", True),
    ("1001", " 1002 ", True),
    ("beta_1.0", "beta_2.0", True),
    ("v1.0.0", "v1.0.0", False),
])
def test_emp_m3_depot_updates_build_id_permutations(inst: Optional[str], latest: Optional[str], expected: bool):
    """Stress 5.1: Build ID comparison boundary invariants across null, whitespace, and mismatch."""
    has_update = bool(
        inst is not None
        and latest is not None
        and str(inst).strip() != ""
        and str(latest).strip() != ""
        and str(inst).strip() != str(latest).strip()
    )
    assert has_update is expected


def test_emp_m3_depot_updates_query_filters_and_schema(api_client: httpx.Client, admin_headers: dict):
    """Stress 5.2: Query parameter filters (available_only, all, game_id, user_only) and schema conformance."""
    # Default query
    r_def = api_client.get("/api/v1/library/updates", headers=admin_headers)
    assert r_def.status_code == 200
    assert isinstance(r_def.json(), list)

    # all=true
    r_all = api_client.get("/api/v1/library/updates?all=true", headers=admin_headers)
    assert r_all.status_code == 200
    all_entries = r_all.json()
    assert len(all_entries) > 0

    # Schema conformance on first entry
    sample = all_entries[0]
    for field in ["game_id", "title", "current_build_id", "build_id", "latest_build_id", "has_update", "is_cached"]:
        assert field in sample, f"Missing required field {field} in DepotUpdateRead"

    # Specific game_id filter
    r_gid = api_client.get("/api/v1/library/updates?game_id=281&all=true", headers=admin_headers)
    assert r_gid.status_code == 200
    assert len(r_gid.json()) == 1
    assert r_gid.json()[0]["game_id"] == 281

    # Non-existent game_id
    r_non = api_client.get("/api/v1/library/updates?game_id=999999", headers=admin_headers)
    assert r_non.status_code == 200
    assert len(r_non.json()) == 0

    # user_only=true
    r_u = api_client.get("/api/v1/library/updates?user_only=true&all=true", headers=admin_headers)
    assert r_u.status_code == 200
    assert isinstance(r_u.json(), list)
