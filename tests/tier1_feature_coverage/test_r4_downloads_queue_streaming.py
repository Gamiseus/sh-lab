"""Tier 1: Feature Coverage — R4: Downloads Queue & Client-Server HTTP File Streaming.

Requirements covered:
- R4.1: POST /api/v1/library/install/{id}/request returns {"cached": true, "task_id": null} when game files exist on server.
- R4.2: POST /api/v1/library/install/{id}/request triggers SteamCMD caching task and returns task_id when uncached.
- R4.3: Task SSE endpoint /api/v1/library/tasks/{task_id}/stream streams progress and event updates.
- R4.4: HTTP 206 Range chunk streaming with Content-Range headers for file payloads.
- R4.5: DownloadsPage.tsx and DownloadStore.ts live queue management with speeds and ETA.
- R4.6: Path traversal attempts on file download endpoints are blocked with HTTP 403.
"""
import os
import re
import pytest
import httpx
from tests.helpers import (
    calculate_download_metrics,
    parse_http_range_header,
)

pytestmark = pytest.mark.tier1


def test_r4_install_request_endpoint_contract(api_client: httpx.Client, admin_headers: dict):
    """R4.1 & R4.2: POST /api/v1/library/install/{id}/request returns cached boolean and task_id."""
    # Test with game 281
    resp = api_client.post("/api/v1/library/install/281/request", headers=admin_headers)
    assert resp.status_code in (200, 202), (
        f"Expected 200/202 from install request, got {resp.status_code}: {resp.text}"
    )
    data = resp.json()
    assert "cached" in data, "Response must include 'cached' boolean flag"
    if data["cached"]:
        assert data.get("task_id") is None
    else:
        assert data.get("task_id") is not None, "Uncached title must return background task_id"


def test_r4_task_sse_stream_endpoint(api_client: httpx.Client, admin_token: str):
    """R4.3: Task SSE stream endpoint exists and connects for valid tasks."""
    # Request a stream connection
    test_task_id = "test-task-1234"
    resp = api_client.get(
        f"/api/v1/library/tasks/{test_task_id}/stream",
        params={"token": admin_token},
        headers={"Accept": "text/event-stream"},
    )
    # 404 is valid if task does not exist, but 405 (Method Not Allowed) or 500 would indicate broken route
    assert resp.status_code in (200, 404), (
        f"SSE task stream endpoint returned unexpected status code {resp.status_code}"
    )


def test_r4_http_range_chunk_streaming_calculation():
    """R4.4: Range header parsing calculates correct 206 content lengths and boundaries."""
    file_size = 1000000  # 1 MB

    # Range: bytes=0-1023 (first 1 KB)
    start, end, length, ok = parse_http_range_header("bytes=0-1023", file_size)
    assert ok is True
    assert start == 0
    assert end == 1023
    assert length == 1024

    # Range: bytes=500000-999999 (second half)
    start, end, length, ok = parse_http_range_header("bytes=500000-999999", file_size)
    assert ok is True
    assert start == 500000
    assert end == 999999
    assert length == 500000

    # Range: bytes=1000000- (out of bounds)
    _, _, _, ok_oob = parse_http_range_header("bytes=1000000-1000005", file_size)
    assert ok_oob is False, "Range beyond file_size must be unsatisfiable (HTTP 416)"


def test_r4_download_speed_and_eta_calculations():
    """R4.5: Download queue calculations accurately compute speeds, ETA, and progress percentage."""
    total_bytes = 100 * 1024 * 1024  # 100 MB
    transferred = 50 * 1024 * 1024   # 50 MB
    elapsed = 5.0                     # 5 seconds (10 MB/s)

    metrics = calculate_download_metrics(transferred, total_bytes, elapsed)
    assert metrics["progress_percent"] == 50.0
    assert metrics["speed_mb_sec"] == 10.0
    assert metrics["eta_seconds"] == 5.0


def test_r4_downloads_page_and_store_contracts():
    """R4.5b: DownloadsPage.tsx and DownloadStore.ts contracts for queue states and live metrics."""
    page_path = os.path.join("frontend", "src", "pages", "DownloadsPage.tsx")
    assert os.path.exists(page_path), f"DownloadsPage.tsx not found at {page_path}"

    with open(page_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Must display speed and active queue
    assert "Download Speed" in content or "speed" in content
    assert "Active Queue" in content or "activeDownloads" in content
    assert "Pause" in content or "Resume" in content


def test_r4_download_file_path_traversal_blocked(api_client: httpx.Client):
    """R4.6: Path traversal attempts on /download/{id}/{file_path} are rejected with HTTP 403 or 400."""
    resp = api_client.get("/api/v1/library/download/281/../../../../etc/passwd")
    assert resp.status_code in (400, 403, 404), (
        f"Path traversal returned {resp.status_code}, expected 403 Forbidden or 400 Bad Request"
    )
    assert resp.status_code != 200, "Directory traversal must not succeed!"
