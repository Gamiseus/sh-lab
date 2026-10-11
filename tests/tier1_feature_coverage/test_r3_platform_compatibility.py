"""Tier 1: Feature Coverage — R3: Platform Compatibility & System Requirements Filtering.

Coverage Requirements: >=5 tests covering primary behavior.
1. Windows-only game suppresses macOS and Linux requirement tabs.
2. Windows + macOS game suppresses Linux requirement tab.
3. Windows + Linux game suppresses macOS requirement tab.
4. Tri-platform game renders all three tabs when requirements exist.
5. Frontend contract: GameDetailsPage checks platforms flags before rendering tabs.
"""
import os
import pytest
from tests.helpers import evaluate_platform_requirements_visibility

pytestmark = pytest.mark.tier1

def test_platform_windows_only_gating():
    """R3.1: Windows-only game (mac=False, linux=False) hides macOS and Linux panels."""
    platforms = {"windows": True, "mac": False, "linux": False}
    pc_req = "<strong>Minimum:</strong> OS: Windows 10 64-bit, CPU: i5-4460"
    mac_req = "<strong>Minimum:</strong> OS: macOS 10.15"  # Non-empty boilerplate from Steam API
    linux_req = "<strong>Minimum:</strong> OS: Ubuntu 20.04"

    visibility = evaluate_platform_requirements_visibility(platforms, pc_req, mac_req, linux_req)
    assert visibility["windows"] is True, "Windows tab should be visible"
    assert visibility["mac"] is False, "macOS tab must NOT be visible when platforms.mac is False"
    assert visibility["linux"] is False, "Linux tab must NOT be visible when platforms.linux is False"


def test_platform_windows_and_mac_gating():
    """R3.2: Dual-platform game (mac=True, linux=False) shows Windows/macOS and hides Linux."""
    platforms = {"windows": True, "mac": True, "linux": False}
    pc_req = "<strong>Minimum:</strong> Windows 10"
    mac_req = "<strong>Minimum:</strong> macOS Monterey"
    linux_req = "<strong>Minimum:</strong> Ubuntu 22.04"

    visibility = evaluate_platform_requirements_visibility(platforms, pc_req, mac_req, linux_req)
    assert visibility["windows"] is True
    assert visibility["mac"] is True
    assert visibility["linux"] is False, "Linux tab must NOT be visible when platforms.linux is False"


def test_platform_windows_and_linux_gating():
    """R3.3: Dual-platform game (mac=False, linux=True) shows Windows/Linux and hides macOS."""
    platforms = {"windows": True, "mac": False, "linux": True}
    pc_req = "<strong>Minimum:</strong> Windows 11"
    mac_req = "<strong>Minimum:</strong> macOS Sonoma"
    linux_req = "<strong>Minimum:</strong> SteamOS / Arch"

    visibility = evaluate_platform_requirements_visibility(platforms, pc_req, mac_req, linux_req)
    assert visibility["windows"] is True
    assert visibility["mac"] is False, "macOS tab must NOT be visible when platforms.mac is False"
    assert visibility["linux"] is True


def test_platform_tri_platform_all_supported():
    """R3.4: Tri-platform game shows Windows, macOS, and Linux tabs."""
    platforms = {"windows": True, "mac": True, "linux": True}
    pc_req = "<strong>Minimum:</strong> Windows 10"
    mac_req = "<strong>Minimum:</strong> macOS 12"
    linux_req = "<strong>Minimum:</strong> Ubuntu 20.04"

    visibility = evaluate_platform_requirements_visibility(platforms, pc_req, mac_req, linux_req)
    assert visibility["windows"] is True
    assert visibility["mac"] is True
    assert visibility["linux"] is True


def test_platform_frontend_ui_contract():
    """R3.5: GameDetailsPage gates macOS and Linux panels with game.platforms check."""
    details_page_path = os.path.join("frontend", "src", "pages", "GameDetailsPage.tsx")
    assert os.path.exists(details_page_path), f"GameDetailsPage.tsx not found at {details_page_path}"
    with open(details_page_path, "r", encoding="utf-8") as f:
        content = f.read()

    # The component must check platforms (e.g. platforms.mac, platforms?.mac, isMacSupported)
    # rather than naively checking `game.mac_requirements` alone.
    has_mac_platform_check = (
        "platforms.mac" in content
        or "platforms?.mac" in content
        or "isMacSupported" in content
        or "is_mac" in content
    )
    has_linux_platform_check = (
        "platforms.linux" in content
        or "platforms?.linux" in content
        or "isLinuxSupported" in content
        or "is_linux" in content
    )

    assert has_mac_platform_check, (
        "GameDetailsPage.tsx must check game.platforms.mac before rendering the macOS requirements panel"
    )
    assert has_linux_platform_check, (
        "GameDetailsPage.tsx must check game.platforms.linux before rendering the Linux requirements panel"
    )
