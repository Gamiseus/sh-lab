"""Authoritative specification models and helper logic for SH-LAB requirements.

Derived strictly from ORIGINAL_REQUEST.md and PROJECT.md.
"""
from typing import Dict, Any, Optional, Set
import re

# Canonical Valve 10-Tier Review Rating Sentiment Algorithm
def get_canonical_valve_sentiment(positive_percent: int, total_reviews: int) -> Dict[str, Any]:
    """Calculate the authentic Valve review rating score (0-9) and descriptive sentiment.

    Rules from Valve Steam Store API:
    - Minimum sample size is 10 reviews. Below 10 -> Score 0, 'No user reviews'.
    - Score 9: 'Overwhelmingly Positive' (>=95% positive, >=500 reviews)
    - Score 8: 'Very Positive' (>=80% positive, >=50 reviews)
    - Score 7: 'Positive' (>=80% positive, 10-49 reviews)
    - Score 6: 'Mostly Positive' (70%-79% positive, >=10 reviews)
    - Score 5: 'Mixed' (40%-69% positive, >=10 reviews)
    - Score 4: 'Mostly Negative' (20%-39% positive, >=10 reviews)
    - Score 3: 'Negative' (0%-19% positive, 10-49 reviews)
    - Score 2: 'Very Negative' (0%-19% positive, 50-499 reviews)
    - Score 1: 'Overwhelmingly Negative' (0%-19% positive, >=500 reviews)
    - Score 0: 'No user reviews' (<10 reviews)
    """
    if total_reviews < 10:
        return {"score": 0, "desc": "No user reviews", "tier": "neutral"}
    
    if positive_percent >= 95 and total_reviews >= 500:
        return {"score": 9, "desc": "Overwhelmingly Positive", "tier": "positive"}
    
    if positive_percent >= 80:
        if total_reviews >= 50:
            return {"score": 8, "desc": "Very Positive", "tier": "positive"}
        return {"score": 7, "desc": "Positive", "tier": "positive"}
    
    if positive_percent >= 70:
        return {"score": 6, "desc": "Mostly Positive", "tier": "positive"}
    
    if positive_percent >= 40:
        return {"score": 5, "desc": "Mixed", "tier": "mixed"}
    
    if positive_percent >= 20:
        return {"score": 4, "desc": "Mostly Negative", "tier": "negative"}
    
    # Below 20%
    if total_reviews >= 500:
        return {"score": 1, "desc": "Overwhelmingly Negative", "tier": "negative"}
    if total_reviews >= 50:
        return {"score": 2, "desc": "Very Negative", "tier": "negative"}
    return {"score": 3, "desc": "Negative", "tier": "negative"}


# Pricing Display & Strikethrough Logic
def calculate_pricing_display(price_cents: Optional[int], discount_percent: Optional[int]) -> Dict[str, Any]:
    """Calculate the clean pricing display without double-discounting or stray '0' badges.

    Rules:
    - price_cents in database is already the current final price.
    - If discount_percent > 0:
        - badge: '-{discount_percent}%'
        - original_price_cents = round(price_cents / (1 - discount_percent / 100))
        - strikethrough: '${original_price_cents / 100:.2f}'
        - current_price: '${price_cents / 100:.2f}'
    - If discount_percent == 0 or None:
        - NO badge (must NOT render stray '0')
        - NO strikethrough text
        - current_price: '${price_cents / 100:.2f}' or 'Free' if 0
    """
    discount = discount_percent or 0
    if price_cents is None:
        return {
            "display": "N/A",
            "has_discount": False,
            "badge": None,
            "strikethrough": None,
            "final_cents": None,
            "is_free": False,
        }
    
    if price_cents == 0:
        return {
            "display": "Free",
            "has_discount": False,
            "badge": None,
            "strikethrough": None,
            "final_cents": 0,
            "is_free": True,
        }
    
    formatted_final = f"${price_cents / 100:.2f}"
    
    if discount > 0:
        original_cents = round(price_cents / (1 - discount / 100))
        formatted_original = f"${original_cents / 100:.2f}"
        return {
            "display": formatted_final,
            "has_discount": True,
            "badge": f"-{discount}%",
            "strikethrough": formatted_original,
            "final_cents": price_cents,
            "original_cents": original_cents,
            "is_free": False,
        }
    
    return {
        "display": formatted_final,
        "has_discount": False,
        "badge": None,
        "strikethrough": None,
        "final_cents": price_cents,
        "is_free": False,
    }


# Platform Requirements Gating
def evaluate_platform_requirements_visibility(
    platforms: Optional[Dict[str, bool]],
    pc_requirements: Optional[str] = None,
    mac_requirements: Optional[str] = None,
    linux_requirements: Optional[str] = None,
) -> Dict[str, bool]:
    """Determine whether system requirements tabs must render.

    Rule: System requirements tabs only display for operating systems marked supported
    in the game's platform flags AND having non-empty requirement content.
    """
    plats = platforms or {}
    
    # Helper to check if string contains substantial requirement specs (not just empty tags)
    def has_content(req: Optional[str]) -> bool:
        if not req:
            return False
        # Remove tags and whitespace
        clean = re.sub(r"<[^>]+>", "", req).strip()
        # Exclude boilerplate like "Minimum:" with no specs
        return len(clean) > 8
    
    win_supported = bool(plats.get("windows", True))
    mac_supported = bool(plats.get("mac", False))
    linux_supported = bool(plats.get("linux", False))
    
    return {
        "windows": win_supported and has_content(pc_requirements),
        "mac": mac_supported and has_content(mac_requirements),
        "linux": linux_supported and has_content(linux_requirements),
    }


# Achievements Masking and Revealing
def evaluate_achievement_display(
    achievement: Dict[str, Any],
    revealed_names: Optional[Set[str]] = None,
) -> Dict[str, Any]:
    """Evaluate achievement rendering and secret spoiler masking.

    Rules:
    - hidden achievements mask description by default.
    - interactive reveal button allows unmasking.
    - global unlock percentage is displayed beside title.
    """
    revealed = revealed_names or set()
    name = achievement.get("name", "")
    display_name = achievement.get("displayName") or achievement.get("display_name") or name
    description = achievement.get("description") or ""
    is_hidden = bool(achievement.get("hidden"))
    percent = achievement.get("percent")
    
    is_revealed = name in revealed
    
    if is_hidden and not is_revealed:
        rendered_desc = "Hidden achievement. Details will be revealed once unlocked."
        has_reveal_button = True
    else:
        rendered_desc = description
        has_reveal_button = False
    
    return {
        "name": name,
        "display_name": display_name,
        "rendered_description": rendered_desc,
        "is_hidden": is_hidden,
        "is_revealed": is_revealed,
        "has_reveal_button": has_reveal_button,
        "percent_formatted": f"{float(percent):.1f}%" if percent is not None else None,
    }
