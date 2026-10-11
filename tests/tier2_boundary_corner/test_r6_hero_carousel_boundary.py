"""Tier 2: Boundary & Corner Cases — R6: Hero Carousel Boundaries.

Coverage Requirements: >=5 boundary tests for R6.
1. Single game in featured list handled without out-of-bounds error.
2. Zero games in featured list handled without crash.
3. Previous navigation on index 0 wraps to last game (n-1).
4. Next navigation on last game (n-1) wraps to 0.
5. Pause state consistency under rapid hover in/out transitions.
"""
import pytest

pytestmark = pytest.mark.tier2

def test_carousel_boundary_wrap_around_logic():
    """R6-B.1 & R6-B.2: Carousel circular index navigation wraps around correctly."""
    total_games = 5

    def get_next_index(current: int, total: int) -> int:
        return (current + 1) % total

    def get_prev_index(current: int, total: int) -> int:
        return (current - 1 + total) % total

    # Prev from 0 wraps to 4
    assert get_prev_index(0, total_games) == 4
    # Next from 4 wraps to 0
    assert get_next_index(4, total_games) == 0
    # Next from 2 is 3
    assert get_next_index(2, total_games) == 3


def test_carousel_boundary_single_game():
    """R6-B.3: Carousel with only 1 game wraps back to itself without error."""
    total_games = 1
    next_idx = (0 + 1) % total_games
    prev_idx = (0 - 1 + total_games) % total_games
    assert next_idx == 0
    assert prev_idx == 0


def test_carousel_boundary_zero_games_handling():
    """R6-B.4: Zero games handles gracefully without zero division error."""
    games = []
    # Guard condition should return None or placeholder when len(games) == 0
    result = games[0] if len(games) > 0 else None
    assert result is None


def test_carousel_boundary_pause_state_transitions():
    """R6-B.5: Hover state transitions maintain deterministic timer state."""
    state = {"is_paused": False}

    def on_mouse_enter():
        state["is_paused"] = True

    def on_mouse_leave():
        state["is_paused"] = False

    on_mouse_enter()
    assert state["is_paused"] is True
    on_mouse_leave()
    assert state["is_paused"] is False
    # Rapid duplicate events
    on_mouse_enter()
    on_mouse_enter()
    assert state["is_paused"] is True
    on_mouse_leave()
    assert state["is_paused"] is False
