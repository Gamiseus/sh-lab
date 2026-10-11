"""Tier 1: Feature Coverage — R6: Hero Slideshow & Featured Carousel Redesign.

Coverage Requirements: >=5 tests covering primary behavior.
1. Prominent navigation arrows with visible hover styling (parent group class present).
2. Paced auto-advance interval of 8–10 seconds (8000–10000ms).
3. Hover pausing behavior without unmounting progress indicators.
4. Card-slot carousel presentation with side previews.
5. Compact bottom overlay for title and actions, keeping upper artwork unobstructed.
"""
import os
import re
import pytest

pytestmark = pytest.mark.tier1

def test_carousel_group_class_and_arrows():
    """R6.1: HeroCarousel parent section must contain 'group' class to make arrows visible on hover."""
    carousel_path = os.path.join("frontend", "src", "components", "store", "HeroCarousel.tsx")
    assert os.path.exists(carousel_path), f"HeroCarousel.tsx not found at {carousel_path}"
    with open(carousel_path, "r", encoding="utf-8") as f:
        content = f.read()

    # The section or top container must contain the Tailwind 'group' class
    # so that `group-hover:opacity-100` triggers properly.
    assert re.search(r'className=["\'][^"\']*\bgroup\b[^"\']*["\']', content), (
        "HeroCarousel container is missing the Tailwind 'group' class, causing navigation arrows to stay hidden!"
    )
    # Check navigation buttons exist with accessible aria-labels
    assert "Prev" in content or "prev" in content or "chevron" in content.lower()
    assert "Next" in content or "next" in content or "chevron" in content.lower()


def test_carousel_autoplay_interval_pacing():
    """R6.2: Auto-advance interval must be comfortably paced at 8–10 seconds (8000–10000ms)."""
    carousel_path = os.path.join("frontend", "src", "components", "store", "HeroCarousel.tsx")
    with open(carousel_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Check that autoPlayInterval is configured to 8000ms - 10000ms
    # It must not be set to rushed 6000ms or lower
    assert not re.search(r'autoPlayInterval\s*=\s*[1-6]000\b', content), (
        "Carousel auto-advance interval is too rushed (< 8000ms). Must be 8-10 seconds."
    )
    has_paced_interval = bool(re.search(r'(8000|9000|10000|\b8\s*\*\s*1000|\b10\s*\*\s*1000)', content))
    assert has_paced_interval, "Carousel auto-advance interval must default to 8000–10000ms"


def test_carousel_pause_on_hover_contract():
    """R6.3: Carousel pauses auto-advance when user hovers over section."""
    carousel_path = os.path.join("frontend", "src", "components", "store", "HeroCarousel.tsx")
    with open(carousel_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "onMouseEnter" in content, "Carousel must listen to onMouseEnter to pause auto-advance"
    assert "onMouseLeave" in content, "Carousel must listen to onMouseLeave to resume auto-advance"
    assert "setIsPaused" in content or "isPaused" in content, "Carousel must maintain pause state on hover"


def test_carousel_card_slot_layout_contract():
    """R6.4: Carousel presents card-slot layout with side background previews."""
    carousel_path = os.path.join("frontend", "src", "components", "store", "HeroCarousel.tsx")
    with open(carousel_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Card slot layout references previous/next preview cards or scale/opacity styling
    has_side_previews = (
        "scale-" in content
        or "preview" in content.lower()
        or "side" in content.lower()
        or "opacity-40" in content
        or "opacity-50" in content
    )
    assert has_side_previews, "Carousel must support card-slot layout with side previews"


def test_carousel_compact_bottom_overlay_contract():
    """R6.5: Title, tags, and actions sit in a compact bottom overlay leaving upper artwork visible."""
    carousel_path = os.path.join("frontend", "src", "components", "store", "HeroCarousel.tsx")
    with open(carousel_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Layout should use bottom alignment (e.g. bottom-0, bg-gradient-to-t) rather than
    # full-height left obstruction (e.g. bg-gradient-to-r covering the left 50%)
    has_bottom_overlay = "bottom-0" in content or "bg-gradient-to-t" in content
    assert has_bottom_overlay, (
        "Hero card details must sit in a compact bottom overlay (bottom-0, bg-gradient-to-t) "
        "rather than obstructing the left half of the artwork."
    )
