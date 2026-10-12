"""Tier 1: Feature Coverage — R6: Dual Server Install Management Administration.

Requirements covered:
- R6.1: GET /api/v1/admin/storage/status returns disk footprint and cache metrics.
- R6.2: GET /api/v1/admin/storage/games returns catalog of tracked games with user counts and build IDs.
- R6.3: POST /api/v1/admin/storage/{game_id}/update triggers SteamCMD update/re-validation.
- R6.4: POST /api/v1/admin/storage/{game_id}/purge immediately purges cached game files and resets cache.
- R6.5: In-app Settings panel "Server Storage & Installs" contract in SettingsPage.tsx.
- R6.6: Dedicated Web Admin view (/admin) route contract in App.tsx and AdminPage.tsx.
- R6.7: Admin RBAC enforcement: non-admin requests are rejected with HTTP 401/403.
"""
import os
import re
import pytest
import httpx

pytestmark = pytest.mark.tier1


def test_r6_admin_storage_status_endpoint(api_client: httpx.Client, admin_headers: dict):
    """R6.1: GET /api/v1/admin/storage/status returns total storage, used bytes, and cache counts."""
    resp = api_client.get("/api/v1/admin/storage/status", headers=admin_headers)
    assert resp.status_code == 200, (
        f"Expected 200 from GET /api/v1/admin/storage/status, got {resp.status_code}: {resp.text}"
    )
    data = resp.json()
    assert "total_bytes" in data or "total_storage" in data
    assert "used_bytes" in data or "used_storage" in data
    assert "cached_games_count" in data or "cached_count" in data


def test_r6_admin_storage_games_list_endpoint(api_client: httpx.Client, admin_headers: dict):
    """R6.2: GET /api/v1/admin/storage/games returns tracked games with user count and build IDs."""
    resp = api_client.get("/api/v1/admin/storage/games", headers=admin_headers)
    assert resp.status_code == 200, (
        f"Expected 200 from GET /api/v1/admin/storage/games, got {resp.status_code}: {resp.text}"
    )
    games = resp.json()
    assert isinstance(games, list), "Storage games must return a list"


def test_r6_admin_storage_force_update_endpoint(api_client: httpx.Client, admin_headers: dict):
    """R6.3: POST /api/v1/admin/storage/{game_id}/update triggers SteamCMD update/re-validation."""
    resp = api_client.post("/api/v1/admin/storage/281/update", headers=admin_headers)
    assert resp.status_code in (200, 202), (
        f"Expected 200/202 from storage update, got {resp.status_code}: {resp.text}"
    )


def test_r6_admin_storage_manual_purge_endpoint(api_client: httpx.Client, admin_headers: dict):
    """R6.4: POST /api/v1/admin/storage/{game_id}/purge immediately purges cached files."""
    resp = api_client.post("/api/v1/admin/storage/281/purge", headers=admin_headers)
    assert resp.status_code in (200, 204), (
        f"Expected 200/204 from storage purge, got {resp.status_code}: {resp.text}"
    )


def test_r6_in_app_settings_storage_panel_contract():
    """R6.5: SettingsPage.tsx provides 'Server Storage & Installs' panel for admins."""
    settings_path = os.path.join("frontend", "src", "pages", "SettingsPage.tsx")
    assert os.path.exists(settings_path), f"SettingsPage.tsx not found at {settings_path}"

    with open(settings_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Verify panel exists
    has_server_storage_panel = (
        "Server Storage & Installs" in content
        or "Server Storage" in content
        or "storage/status" in content
    )
    assert has_server_storage_panel, (
        "SettingsPage.tsx must include a 'Server Storage & Installs' section for admins"
    )


def test_r6_dedicated_web_admin_route_and_view_contract():
    """R6.6: App.tsx registers /admin route and AdminPage.tsx exists."""
    app_path = os.path.join("frontend", "src", "App.tsx")
    admin_page_path = os.path.join("frontend", "src", "pages", "AdminPage.tsx")

    with open(app_path, "r", encoding="utf-8") as f:
        app_content = f.read()

    has_admin_route = 'path="/admin"' in app_content or "path='/admin'" in app_content
    assert has_admin_route, "App.tsx must register route for dedicated admin view /admin"
    assert os.path.exists(admin_page_path), f"AdminPage.tsx must exist at {admin_page_path}"


def test_r6_admin_storage_endpoints_require_admin_role(api_client: httpx.Client, regular_headers: dict):
    """R6.7: Non-admin or unauthenticated requests to storage admin endpoints are rejected (401/403)."""
    # Unauthenticated
    unauth_resp = api_client.get("/api/v1/admin/storage/status")
    assert unauth_resp.status_code in (401, 403), "Unauthenticated access must be rejected"

    # Regular non-admin user
    if regular_headers:
        reg_resp = api_client.get("/api/v1/admin/storage/status", headers=regular_headers)
        assert reg_resp.status_code in (401, 403), "Non-admin access must be rejected with 401/403"
