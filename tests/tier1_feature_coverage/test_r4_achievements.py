"""Tier 1: Feature Coverage — R4: Steam Achievements Ingestion & Interactive Display.

Coverage Requirements: >=5 tests covering primary behavior.
1. Complete achievement schema fields (name, displayName, description, icon, percent, hidden).
2. Global unlock percentage formatted display.
3. Hidden achievements masked by default with spoiler protection.
4. Interactive reveal toggle unmasks hidden achievement description.
5. Non-hidden public achievements display description openly.
"""
import os
import pytest
from tests.helpers import evaluate_achievement_display

pytestmark = pytest.mark.tier1

def test_achievements_schema_completeness():
    """R4.1: Achievement model includes complete required metadata."""
    sample_achievement = {
        "name": "ACH_KILL_DRAGON",
        "displayName": "Dragon Slayer",
        "description": "Defeat the ancient dragon in the volcanic peak.",
        "icon": "https://shared.fastly.steamstatic.com/achievements/dragon.jpg",
        "percent": 34.8,
        "hidden": False,
    }
    display = evaluate_achievement_display(sample_achievement)
    assert display["name"] == "ACH_KILL_DRAGON"
    assert display["display_name"] == "Dragon Slayer"
    assert display["rendered_description"] == "Defeat the ancient dragon in the volcanic peak."
    assert display["percent_formatted"] == "34.8%"
    assert display["is_hidden"] is False


def test_achievements_hidden_masking_default():
    """R4.2: Hidden achievement description is masked by default with spoiler placeholder."""
    hidden_achievement = {
        "name": "ACH_SECRET_ENDING",
        "displayName": "True Path",
        "description": "Discover the secret ending by sparing the antagonist.",
        "icon": "https://shared.fastly.steamstatic.com/achievements/secret.jpg",
        "percent": 12.5,
        "hidden": True,
    }
    display = evaluate_achievement_display(hidden_achievement, revealed_names=set())
    assert display["is_hidden"] is True
    assert display["is_revealed"] is False
    assert display["has_reveal_button"] is True
    # The secret description must NOT be revealed in the rendered description
    assert "sparing the antagonist" not in display["rendered_description"]
    assert "Hidden achievement" in display["rendered_description"]


def test_achievements_interactive_reveal_toggle():
    """R4.3: Clicking reveal unmasks the hidden achievement description."""
    hidden_achievement = {
        "name": "ACH_SECRET_ENDING",
        "displayName": "True Path",
        "description": "Discover the secret ending by sparing the antagonist.",
        "icon": "https://shared.fastly.steamstatic.com/achievements/secret.jpg",
        "percent": 12.5,
        "hidden": True,
    }
    # User clicks reveal -> ACH_SECRET_ENDING is added to revealed set
    revealed_set = {"ACH_SECRET_ENDING"}
    display = evaluate_achievement_display(hidden_achievement, revealed_names=revealed_set)
    assert display["is_revealed"] is True
    assert display["has_reveal_button"] is False
    # Now the authentic description is visible
    assert display["rendered_description"] == "Discover the secret ending by sparing the antagonist."


def test_achievements_global_unlock_percentage_formatting():
    """R4.4: Global unlock percentage is displayed as a clean single-decimal percentage."""
    ach1 = {"name": "A1", "percent": 74.0321}
    ach2 = {"name": "A2", "percent": 0.499}
    ach3 = {"name": "A3", "percent": 100.0}

    assert evaluate_achievement_display(ach1)["percent_formatted"] == "74.0%"
    assert evaluate_achievement_display(ach2)["percent_formatted"] == "0.5%"
    assert evaluate_achievement_display(ach3)["percent_formatted"] == "100.0%"


def test_achievements_frontend_ui_contract():
    """R4.5: GameDetailsPage renders full achievements with reveal button and percentages."""
    details_page_path = os.path.join("frontend", "src", "pages", "GameDetailsPage.tsx")
    assert os.path.exists(details_page_path), f"GameDetailsPage.tsx not found at {details_page_path}"
    with open(details_page_path, "r", encoding="utf-8") as f:
        content = f.read()

    # The achievements tab must support description and reveal mechanism or percent
    has_description = "description" in content
    has_reveal = "reveal" in content.lower() or "hidden" in content.lower() or "spoiler" in content.lower()
    has_percent = "percent" in content or "%" in content

    assert has_description, "Achievements UI must render achievement descriptions"
    assert has_reveal, "Achievements UI must support hidden achievement reveal toggling"
    assert has_percent, "Achievements UI must render global unlock percentages"
