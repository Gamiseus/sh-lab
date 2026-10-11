"""Tier 2: Boundary & Corner Cases — R3: Platform Compatibility Boundaries.

Coverage Requirements: >=5 boundary tests for R3.
1. Empty platforms dictionary `{}` handled safely without KeyError.
2. Null platforms (`None`) handled safely without exception.
3. Boilerplate HTML with no real specs suppressed on unsupported platforms.
4. Only Linux supported platform edge case.
5. All platforms set to False edge case.
"""
import pytest
from tests.helpers import evaluate_platform_requirements_visibility

pytestmark = pytest.mark.tier2

def test_platform_boundary_empty_platforms_dict():
    """R3-B.1: Empty platforms dictionary `{}` defaults safely to Windows and suppresses Mac/Linux."""
    vis = evaluate_platform_requirements_visibility(
        platforms={},
        pc_requirements="<strong>Minimum:</strong> Windows 10",
        mac_requirements="<strong>Minimum:</strong> macOS",
        linux_requirements="<strong>Minimum:</strong> Linux",
    )
    assert vis["windows"] is True
    assert vis["mac"] is False
    assert vis["linux"] is False


def test_platform_boundary_null_platforms():
    """R3-B.2: Null platforms (`None`) handles gracefully without exceptions."""
    vis = evaluate_platform_requirements_visibility(
        platforms=None,
        pc_requirements="<strong>Minimum:</strong> Windows 10",
        mac_requirements="<strong>Minimum:</strong> macOS",
        linux_requirements="<strong>Minimum:</strong> Linux",
    )
    assert isinstance(vis, dict)
    assert vis["windows"] is True
    assert vis["mac"] is False
    assert vis["linux"] is False


def test_platform_boundary_boilerplate_html_suppression():
    """R3-B.3: Empty boilerplate HTML (`<ul></ul>`) without real specs is suppressed."""
    boilerplate = "<strong>Minimum:</strong><br><ul class=\"bb_ul\"></ul>"
    vis = evaluate_platform_requirements_visibility(
        platforms={"windows": True, "mac": True, "linux": False},
        pc_requirements="<strong>Minimum:</strong> Windows 10, i7 CPU, 16GB RAM",
        mac_requirements=boilerplate,  # Steam API template with no content
        linux_requirements="",
    )
    assert vis["windows"] is True
    assert vis["mac"] is False, "Empty boilerplate HTML should not trigger tab display"
    assert vis["linux"] is False


def test_platform_boundary_only_linux_supported():
    """R3-B.4: Only Linux supported game shows only Linux requirements tab."""
    vis = evaluate_platform_requirements_visibility(
        platforms={"windows": False, "mac": False, "linux": True},
        pc_requirements="Windows 10 specs",
        mac_requirements="macOS specs",
        linux_requirements="<strong>Minimum:</strong> Ubuntu 22.04, Vulkan 1.3",
    )
    assert vis["windows"] is False
    assert vis["mac"] is False
    assert vis["linux"] is True


def test_platform_boundary_all_false_platforms():
    """R3-B.5: Game with all platforms set to False suppresses all requirement tabs."""
    vis = evaluate_platform_requirements_visibility(
        platforms={"windows": False, "mac": False, "linux": False},
        pc_requirements="Specs",
        mac_requirements="Specs",
        linux_requirements="Specs",
    )
    assert vis["windows"] is False
    assert vis["mac"] is False
    assert vis["linux"] is False
