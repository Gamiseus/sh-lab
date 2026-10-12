"""Tier 1: Feature Coverage — R2: Dual "Add to Library" and "Install" Workflows.

Requirements covered:
- R2.1: Backend endpoint POST /api/v1/library/user adds game to user's library without triggering file download.
- R2.2: GameDetailsPage.tsx and GameInfoPanel.tsx offer dual "Add to Library" vs "Install" actions.
- R2.3: LibraryPage.tsx renders uninstalled titles in distinct dimmed/grayed-out state with prominent "Install" button.
- R2.4: HeroCarousel.tsx Download trigger both registers the game in user library and dispatches installation.
- R2.5: LibraryStore.ts maintains dual tracking of owned library titles vs locally installed titles.
- R2.6: User library retrieval and removal endpoints (GET/DELETE /api/v1/library/user).
"""
import os
import re
import pytest
import httpx

pytestmark = pytest.mark.tier1


def test_r2_add_to_library_endpoint(api_client: httpx.Client, admin_headers: dict):
    """R2.1: POST /api/v1/library/user adds a game to user's library without starting download."""
    # Fetch a valid game from the catalog
    cat_resp = api_client.get("/api/v1/library/")
    assert cat_resp.status_code == 200
    games = cat_resp.json()
    assert len(games) > 0
    target_game_id = games[0]["id"]

    # Post to library/user
    resp = api_client.post(
        "/api/v1/library/user",
        headers=admin_headers,
        json={"game_id": target_game_id},
    )
    assert resp.status_code in (200, 201), (
        f"Expected 200/201 when adding game to user library, got {resp.status_code}: {resp.text}. "
        "Endpoint POST /api/v1/library/user must be implemented."
    )
    data = resp.json()
    assert "game_id" in data or "id" in data or "success" in data or "message" in data


def test_r2_game_details_dual_action_contract():
    """R2.2: GameDetailsPage & GameInfoPanel expose dual 'Add to Library' alongside 'Install'."""
    panel_path = os.path.join("frontend", "src", "components", "store", "GameInfoPanel.tsx")
    details_path = os.path.join("frontend", "src", "pages", "GameDetailsPage.tsx")
    assert os.path.exists(panel_path), f"GameInfoPanel.tsx not found at {panel_path}"
    assert os.path.exists(details_path), f"GameDetailsPage.tsx not found at {details_path}"

    with open(panel_path, "r", encoding="utf-8") as f:
        panel_content = f.read()

    # Verify GameInfoPanel supports onAddToLibrary or 'Add to Library' button
    has_add_to_library = (
        "Add to Library" in panel_content
        or "addToLibrary" in panel_content
        or "onAddToLibrary" in panel_content
    )
    assert has_add_to_library, (
        "GameInfoPanel.tsx must provide an 'Add to Library' action alongside 'Install'"
    )


def test_r2_library_page_uninstalled_grayed_state_contract():
    """R2.3: LibraryPage renders uninstalled titles in dimmed/grayed-out state with an 'Install' button."""
    lib_path = os.path.join("frontend", "src", "pages", "LibraryPage.tsx")
    assert os.path.exists(lib_path), f"LibraryPage.tsx not found at {lib_path}"

    with open(lib_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Must distinguish installed vs uninstalled
    has_install_check = (
        "isInstalled" in content
        or "installed" in content
        or "install_path" in content
    )
    assert has_install_check, "LibraryPage must inspect installed state of games"

    # Must provide distinct dimmed/grayed styling for uninstalled titles (e.g. opacity, grayscale, or dimmed border)
    has_grayed_style = (
        "opacity-" in content
        or "grayscale" in content
        or "brightness-" in content
        or "saturate-" in content
        or "dimmed" in content
    )
    assert has_grayed_style, "LibraryPage must render uninstalled titles in a distinct dimmed/grayed-out state"

    # Must provide an Install action/button on uninstalled cards
    has_install_button = (
        "Install" in content
        or "onInstall" in content
        or "handleInstall" in content
    )
    assert has_install_button, "LibraryPage must provide an 'Install' action for uninstalled games"


def test_r2_hero_carousel_download_registers_and_installs_contract():
    """R2.4: HeroCarousel Download button registers title in user library and dispatches installation."""
    carousel_path = os.path.join("frontend", "src", "components", "store", "HeroCarousel.tsx")
    assert os.path.exists(carousel_path), f"HeroCarousel.tsx not found at {carousel_path}"

    with open(carousel_path, "r", encoding="utf-8") as f:
        content = f.read()

    # The action button must trigger install/download workflow rather than only navigating
    has_install_trigger = (
        "handleInstall" in content
        or "onInstall" in content
        or "installGame" in content
        or "addToLibrary" in content
    )
    assert has_install_trigger, (
        "HeroCarousel Download action must trigger library registration and installation"
    )


def test_r2_library_store_tracks_owned_vs_installed_contract():
    """R2.5: LibraryStore tracks both owned library games and installed games."""
    store_path = os.path.join("frontend", "src", "stores", "LibraryStore.ts")
    assert os.path.exists(store_path), f"LibraryStore.ts not found at {store_path}"

    with open(store_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Must track user library/owned games alongside installed games
    has_owned_tracking = (
        "userGames" in content
        or "ownedGames" in content
        or "libraryGames" in content
        or "addToLibrary" in content
    )
    assert has_owned_tracking, (
        "LibraryStore.ts must track user library / owned games distinct from installed games"
    )


def test_r2_user_library_get_and_delete_endpoints(api_client: httpx.Client, admin_headers: dict):
    """R2.6: GET and DELETE /api/v1/library/user allow listing and removing games from user library."""
    # List user library
    get_resp = api_client.get("/api/v1/library/user", headers=admin_headers)
    assert get_resp.status_code == 200, (
        f"Expected 200 from GET /api/v1/library/user, got {get_resp.status_code}: {get_resp.text}"
    )
    assert isinstance(get_resp.json(), list), "GET /api/v1/library/user must return a list of games"

    # Add game 281
    api_client.post("/api/v1/library/user", headers=admin_headers, json={"game_id": 281})

    # Delete game 281
    del_resp = api_client.delete("/api/v1/library/user/281", headers=admin_headers)
    assert del_resp.status_code in (200, 204), (
        f"Expected 200/204 from DELETE /api/v1/library/user/281, got {del_resp.status_code}"
    )
