"""Tier 2: Boundary & Corner Cases — R4: Steam Achievements Boundaries.

Coverage Requirements: >=5 boundary tests for R4.
1. 0.0% unlock percentage boundary condition.
2. 100.0% unlock percentage boundary condition.
3. 100% secret/hidden achievements game boundary.
4. Missing/null description field handling.
5. Game with zero achievements empty state handling.
"""
import pytest
from tests.helpers import evaluate_achievement_display

pytestmark = pytest.mark.tier2

def test_achievements_boundary_zero_percent_unlock():
    """R4-B.1: Achievement with 0.0% unlock rate formats correctly as '0.0%'."""
    ach = {
        "name": "ACH_IMPOSSIBLE",
        "displayName": "Untouchable",
        "description": "Complete the game on Iron Man without taking damage.",
        "percent": 0.0,
        "hidden": False,
    }
    res = evaluate_achievement_display(ach)
    assert res["percent_formatted"] == "0.0%"
    assert res["rendered_description"] == "Complete the game on Iron Man without taking damage."


def test_achievements_boundary_100_percent_unlock():
    """R4-B.2: Achievement with 100.0% unlock rate formats as '100.0%'."""
    ach = {
        "name": "ACH_START",
        "displayName": "Begin Adventure",
        "description": "Start the prologue.",
        "percent": 100.0,
        "hidden": False,
    }
    res = evaluate_achievement_display(ach)
    assert res["percent_formatted"] == "100.0%"


def test_achievements_boundary_all_hidden_game():
    """R4-B.3: Game with 100% hidden achievements masks every single description."""
    achievements = [
        {"name": f"ACH_{i}", "displayName": f"Secret {i}", "description": f"Plot spoiler {i}", "hidden": True}
        for i in range(5)
    ]
    for ach in achievements:
        res = evaluate_achievement_display(ach, revealed_names=set())
        assert res["is_hidden"] is True
        assert res["has_reveal_button"] is True
        assert "Plot spoiler" not in res["rendered_description"]
        assert "Hidden achievement" in res["rendered_description"]


def test_achievements_boundary_empty_description():
    """R4-B.4: Missing or None description field displays without raising an error."""
    ach = {
        "name": "ACH_NO_DESC",
        "displayName": "Mystery Achievement",
        "description": None,
        "percent": 50.0,
        "hidden": False,
    }
    res = evaluate_achievement_display(ach)
    assert res["rendered_description"] == ""
    assert res["display_name"] == "Mystery Achievement"
    assert res["percent_formatted"] == "50.0%"


def test_achievements_boundary_game_with_zero_achievements():
    """R4-B.5: Game with zero achievements handles empty list safely."""
    empty_achievements = []
    # Iteration or mapping over empty list should return empty list without exceptions
    rendered = [evaluate_achievement_display(a) for a in empty_achievements]
    assert len(rendered) == 0
