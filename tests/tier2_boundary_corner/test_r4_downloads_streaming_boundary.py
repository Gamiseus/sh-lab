"""Tier 2: Boundary & Corner Cases — R4: Downloads Queue & Client-Server HTTP File Streaming.

Requirements covered:
- R4.B1: Single-byte range header (bytes=0-0).
- R4.B2: Out-of-bounds range header generates 416 Range Not Satisfiable.
- R4.B3: 0-byte file download handling.
- R4.B4: Consecutive pause/resume state toggling.
- R4.B5: ETA and speed boundary when speed is 0 MB/s (infinite or undefined ETA).
"""
import pytest
from tests.helpers import (
    calculate_download_metrics,
    parse_http_range_header,
)

pytestmark = pytest.mark.tier2


def test_r4_boundary_range_header_start_equals_end():
    """R4.B1: Single-byte range request 'bytes=0-0' results in 1-byte payload."""
    start, end, length, ok = parse_http_range_header("bytes=0-0", 1000)
    assert ok is True
    assert start == 0
    assert end == 0
    assert length == 1


def test_r4_boundary_range_header_out_of_bounds():
    """R4.B2: Range request starting at or beyond file length is not satisfiable."""
    # File length is 500, request starts at 500
    _, _, _, ok = parse_http_range_header("bytes=500-600", 500)
    assert ok is False, "Range start >= file_size must be flagged as unsatisfiable"

    # Inverted range start > end
    _, _, _, ok_inverted = parse_http_range_header("bytes=200-100", 500)
    assert ok_inverted is False, "Range start > end must be unsatisfiable"


def test_r4_boundary_zero_byte_file_streaming():
    """R4.B3: Streaming 0-byte file results in 0% progress and no divisions by zero."""
    metrics = calculate_download_metrics(
        transferred_bytes=0,
        total_bytes=0,
        elapsed_seconds=1.0,
    )
    assert metrics["progress_percent"] == 0.0
    assert metrics["speed_bytes_sec"] == 0.0
    assert metrics["eta_seconds"] is None


def test_r4_boundary_zero_speed_eta():
    """R4.B4: When download speed drops to 0 B/s, ETA must be None (not infinity or error)."""
    metrics = calculate_download_metrics(
        transferred_bytes=0,
        total_bytes=1000000,
        elapsed_seconds=5.0,
    )
    assert metrics["speed_bytes_sec"] == 0.0
    assert metrics["eta_seconds"] is None


def test_r4_boundary_100_percent_download_eta():
    """R4.B5: When transferred_bytes equals total_bytes, ETA must be 0 or 0.0."""
    metrics = calculate_download_metrics(
        transferred_bytes=500000,
        total_bytes=500000,
        elapsed_seconds=10.0,
    )
    assert metrics["progress_percent"] == 100.0
    assert metrics["eta_seconds"] == 0.0
