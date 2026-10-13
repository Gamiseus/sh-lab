"""Tier 5: Adversarial Challenge — Milestone 2 (R4) Verification Harness.

Authored by Challenger 2 (teamwork_preview_challenger_m2_2) to independently and
empirically stress-test:
1. POST /api/v1/library/install/{game_id}/request (cached vs uncached vs non-existent vs deduplication)
2. GET /api/v1/library/tasks/{task_id}/stream (SSE stream format, event headers, termination, 404 for invalid task)
3. Directory traversal blocking (HTTP 403) across multiple encodings & HTTP 206 Range partial chunk streaming
4. Frontend contracts, metrics math, and boundary conditions
"""
import os
import re
import json
import pytest
import httpx
from tests.helpers import (
    calculate_download_metrics,
    parse_http_range_header,
)

pytestmark = pytest.mark.tier5


# =========================================================================
# AREA 1: POST /api/v1/library/install/{game_id}/request
# =========================================================================

def test_adv_r4_install_request_cached_game(api_client: httpx.Client, admin_headers: dict):
    """Verify that cached title (game 281: 'Where the Water Tastes Like Wine') returns cached: True, task_id: None."""
    resp = api_client.post("/api/v1/library/install/281/request", headers=admin_headers)
    assert resp.status_code == 200, f"Expected 200 for cached game install request, got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert data["cached"] is True, f"Game 281 must be flagged as cached, got {data}"
    assert data["task_id"] is None, f"Cached game must have task_id=None, got {data.get('task_id')}"
    assert "cached on server" in data.get("message", "").lower()


def test_adv_r4_install_request_uncached_game(api_client: httpx.Client, admin_headers: dict):
    """Verify that uncached title returns cached: False and a valid background task_id."""
    # Find an uncached game from catalog
    games_resp = api_client.get("/api/v1/store/games")
    assert games_resp.status_code == 200
    games = games_resp.json()
    
    # Pick a title not currently cached on disk
    repo_dirs = set(os.listdir(os.path.join("data", "repo"))) if os.path.exists(os.path.join("data", "repo")) else set()
    repo_dirs_normalized = {d.replace("", ":") for d in repo_dirs} | repo_dirs
    uncached_games = [g for g in games if g["title"] not in repo_dirs_normalized]
    assert len(uncached_games) > 0, "Expected at least one uncached game in catalog"
    target_game = uncached_games[0]

    resp = api_client.post(f"/api/v1/library/install/{target_game['id']}/request", headers=admin_headers)
    assert resp.status_code == 200, f"Expected 200 for uncached game install request, got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert data["cached"] is False, f"Game {target_game['id']} ({target_game['title']}) must be uncached, got {data}"
    task_id = data.get("task_id")
    assert task_id is not None and len(str(task_id)) > 0, f"Uncached game must return task_id string, got {task_id}"


def test_adv_r4_install_request_deduplication(api_client: httpx.Client, admin_headers: dict):
    """Verify that repeated requests for an active uncached download return the same deduplicated task_id."""
    resp1 = api_client.post("/api/v1/library/install/734/request", headers=admin_headers)
    assert resp1.status_code == 200
    data1 = resp1.json()

    # Second immediate request
    resp2 = api_client.post("/api/v1/library/install/734/request", headers=admin_headers)
    assert resp2.status_code == 200
    data2 = resp2.json()

    if not data1["cached"] and not data2["cached"]:
        assert data1["task_id"] == data2["task_id"], (
            f"Active download task must be deduplicated: first={data1['task_id']}, second={data2['task_id']}"
        )


def test_adv_r4_install_request_nonexistent_game_404(api_client: httpx.Client, admin_headers: dict):
    """Verify that non-existent game ID returns HTTP 404."""
    resp = api_client.post("/api/v1/library/install/999999/request", headers=admin_headers)
    assert resp.status_code == 404, f"Expected 404 for non-existent game, got {resp.status_code}: {resp.text}"
    assert "not found" in resp.json().get("detail", "").lower()


def test_adv_r4_install_request_invalid_id_type_422(api_client: httpx.Client, admin_headers: dict):
    """Verify that string game ID returns HTTP 422 Unprocessable Entity."""
    resp = api_client.post("/api/v1/library/install/invalid_string/request", headers=admin_headers)
    assert resp.status_code == 422, f"Expected 422 for string ID, got {resp.status_code}: {resp.text}"


# =========================================================================
# AREA 2: GET /api/v1/library/tasks/{task_id}/stream SSE Stream Events
# =========================================================================

def test_adv_r4_task_sse_stream_nonexistent_task_404(api_client: httpx.Client, admin_token: str):
    """Verify that requesting SSE stream for non-existent task returns HTTP 404."""
    resp = api_client.get(
        "/api/v1/library/tasks/definitely-non-existent-task-id-9999/stream",
        params={"token": admin_token},
        headers={"Accept": "text/event-stream"}
    )
    assert resp.status_code == 404, f"Expected 404 for invalid task stream, got {resp.status_code}: {resp.text}"


def test_adv_r4_task_sse_stream_events_format(api_client: httpx.Client, admin_token: str, admin_headers: dict):
    """Verify that SSE stream returns text/event-stream and sends event: init with valid payload."""
    # Trigger an install request on an uncached game
    games_resp = api_client.get("/api/v1/store/games")
    assert games_resp.status_code == 200
    games = games_resp.json()
    repo_dirs = set(os.listdir(os.path.join("data", "repo"))) if os.path.exists(os.path.join("data", "repo")) else set()
    repo_dirs_normalized = {d.replace("", ":") for d in repo_dirs} | repo_dirs
    uncached_games = [g for g in games if g["title"] not in repo_dirs_normalized]
    assert len(uncached_games) > 0

    target_game = uncached_games[0]
    req_resp = api_client.post(f"/api/v1/library/install/{target_game['id']}/request", headers=admin_headers)
    assert req_resp.status_code == 200
    task_id = req_resp.json().get("task_id")
    assert task_id is not None, f"Expected task_id for uncached game {target_game['id']}"

    # Connect to SSE stream
    with api_client.stream(
        "GET",
        f"/api/v1/library/tasks/{task_id}/stream",
        params={"token": admin_token},
        headers={"Accept": "text/event-stream"},
        timeout=10.0
    ) as stream_resp:
        assert stream_resp.status_code == 200, f"Expected 200 for SSE stream, got {stream_resp.status_code}"
        assert "text/event-stream" in stream_resp.headers.get("content-type", "")
        assert stream_resp.headers.get("cache-control") == "no-cache"

        # Read first SSE frame
        event_name = None
        data_payload = None
        for line in stream_resp.iter_lines():
            if line.startswith("event:"):
                event_name = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                data_payload = json.loads(line.split(":", 1)[1].strip())
            elif line == "":
                # End of SSE message block
                if event_name and data_payload:
                    break

        assert event_name in ("init", "status", "progress"), f"First SSE event unexpected: {event_name}"
        assert data_payload is not None, "Did not receive data payload in SSE event"
        if event_name == "init":
            assert "id" in data_payload
            assert "status" in data_payload
            assert "progress" in data_payload


# =========================================================================
# AREA 3: Path Traversal Protection (HTTP 403) & HTTP 206 Range Streaming
# =========================================================================

@pytest.mark.parametrize("traversal_path", [
    "..%2f..%2f..%2fetc/passwd",
    "%2fetc/passwd",
    "steamapps/..%2f..%2f..%2fetc/passwd",
    "steamapps/..%2f..%2f..%2fetc/shadow",
    "%2e%2e%2f%2e%2e%2fetc/passwd",
])
def test_adv_r4_directory_traversal_attempts_blocked_403(api_client: httpx.Client, traversal_path: str):
    """Verify that path traversal attempts across multiple encodings are strictly blocked with HTTP 403."""
    resp = api_client.get(f"/api/v1/library/download/281/{traversal_path}")
    assert resp.status_code == 403, (
        f"Directory traversal '{traversal_path}' must be blocked with HTTP 403, got {resp.status_code}: {resp.text}"
    )
    assert "access denied" in resp.json().get("detail", "").lower()


def test_adv_r4_download_nonexistent_file_in_valid_game_404(api_client: httpx.Client):
    """Verify that requesting non-existent file inside valid game returns HTTP 404 (not 403 or 500)."""
    resp = api_client.get("/api/v1/library/download/281/non_existent_file_xyz.bin")
    assert resp.status_code == 404
    assert resp.json().get("detail") == "File not found"


def test_adv_r4_download_nonexistent_game_404(api_client: httpx.Client):
    """Verify that requesting download for non-existent game returns HTTP 404."""
    resp = api_client.get("/api/v1/library/download/999999/sample.dat")
    assert resp.status_code == 404
    assert resp.json().get("detail") == "Game not found"


def test_adv_r4_http_206_range_streaming_matrix(api_client: httpx.Client):
    """Verify full HTTP 206 chunk range streaming matrix against cached sample.dat (100,000 bytes)."""
    file_size = 100000

    # 1. Full download without Range header -> 200 OK
    resp_full = api_client.get("/api/v1/library/download/281/sample.dat")
    assert resp_full.status_code == 200
    assert len(resp_full.content) == file_size
    assert resp_full.headers.get("accept-ranges") == "bytes"
    full_bytes = resp_full.content

    # 2. First 10 bytes: Range: bytes=0-9 -> 206 Partial Content
    resp_r1 = api_client.get("/api/v1/library/download/281/sample.dat", headers={"Range": "bytes=0-9"})
    assert resp_r1.status_code == 206
    assert resp_r1.headers.get("content-range") == f"bytes 0-9/{file_size}"
    assert resp_r1.headers.get("content-length") == "10"
    assert resp_r1.content == full_bytes[0:10]

    # 3. Single first byte: Range: bytes=0-0 -> 206 Partial Content
    resp_single = api_client.get("/api/v1/library/download/281/sample.dat", headers={"Range": "bytes=0-0"})
    assert resp_single.status_code == 206
    assert resp_single.headers.get("content-range") == f"bytes 0-0/{file_size}"
    assert resp_single.headers.get("content-length") == "1"
    assert resp_single.content == full_bytes[0:1]

    # 4. Middle chunk: Range: bytes=1000-1999 -> 206 Partial Content
    resp_mid = api_client.get("/api/v1/library/download/281/sample.dat", headers={"Range": "bytes=1000-1999"})
    assert resp_mid.status_code == 206
    assert resp_mid.headers.get("content-range") == f"bytes 1000-1999/{file_size}"
    assert resp_mid.headers.get("content-length") == "1000"
    assert resp_mid.content == full_bytes[1000:2000]

    # 5. Open-ended tail chunk: Range: bytes=99900- -> 206 Partial Content
    resp_tail = api_client.get("/api/v1/library/download/281/sample.dat", headers={"Range": "bytes=99900-"})
    assert resp_tail.status_code == 206
    assert resp_tail.headers.get("content-range") == f"bytes 99900-99999/{file_size}"
    assert resp_tail.headers.get("content-length") == "100"
    assert resp_tail.content == full_bytes[99900:]

    # 6. Single last byte: Range: bytes=99999-99999 -> 206 Partial Content
    resp_last = api_client.get("/api/v1/library/download/281/sample.dat", headers={"Range": "bytes=99999-99999"})
    assert resp_last.status_code == 206
    assert resp_last.headers.get("content-range") == f"bytes 99999-99999/{file_size}"
    assert resp_last.headers.get("content-length") == "1"
    assert resp_last.content == full_bytes[99999:100000]

    # 7. Out of bounds: Range: bytes=100000-100010 -> 416 Range Not Satisfiable
    resp_oob = api_client.get("/api/v1/library/download/281/sample.dat", headers={"Range": "bytes=100000-100010"})
    assert resp_oob.status_code == 416
    assert resp_oob.headers.get("content-range") == f"bytes */{file_size}"

    # 8. Inverted range: Range: bytes=500-200 -> 416 Range Not Satisfiable
    resp_inv = api_client.get("/api/v1/library/download/281/sample.dat", headers={"Range": "bytes=500-200"})
    assert resp_inv.status_code == 416
    assert resp_inv.headers.get("content-range") == f"bytes */{file_size}"

    # 9. Invalid specifier: Range: bytes=invalid -> 416 Range Not Satisfiable
    resp_inv_spec = api_client.get("/api/v1/library/download/281/sample.dat", headers={"Range": "bytes=invalid"})
    assert resp_inv_spec.status_code == 416


def test_adv_r4_zero_byte_file_boundaries(api_client: httpx.Client):
    """Verify 0-byte file handling: 200 without range, 416 with range (RFC 7233)."""
    # Without range
    resp_no_range = api_client.get("/api/v1/library/download/281/zero_byte.dat")
    assert resp_no_range.status_code == 200
    assert len(resp_no_range.content) == 0
    assert resp_no_range.headers.get("content-length") == "0"

    # With range -> 416 Range Not Satisfiable with bytes */0
    resp_with_range = api_client.get(
        "/api/v1/library/download/281/zero_byte.dat",
        headers={"Range": "bytes=0-0"}
    )
    assert resp_with_range.status_code == 416
    assert resp_with_range.headers.get("content-range") == "bytes */0"
    assert resp_with_range.headers.get("content-length") == "0"


# =========================================================================
# AREA 4: Frontend Store Contract (DownloadStore.ts) and DownloadsPage.tsx
# =========================================================================

def test_adv_r4_download_metrics_oracle_boundaries():
    """Stress-test download metrics math across zero, infinity, and boundary states."""
    # Zero transferred, zero total, zero elapsed
    m1 = calculate_download_metrics(0, 0, 0.0)
    assert m1["progress_percent"] == 0.0
    assert m1["speed_bytes_sec"] == 0.0
    assert m1["speed_mb_sec"] == 0.0
    assert m1["eta_seconds"] is None

    # Zero elapsed seconds (prevent division by zero)
    m2 = calculate_download_metrics(1024, 2048, 0.0)
    assert m2["speed_bytes_sec"] == 0.0
    assert m2["eta_seconds"] is None
    assert m2["progress_percent"] == 50.0

    # 100% completion
    m3 = calculate_download_metrics(1000000, 1000000, 10.0)
    assert m3["progress_percent"] == 100.0
    assert m3["eta_seconds"] == 0.0

    # Transferred exceeds total (cap at 100%)
    m4 = calculate_download_metrics(1500000, 1000000, 10.0)
    assert m4["progress_percent"] == 100.0
    assert m4["eta_seconds"] == 0.0

    # Standard progression
    total = 10 * 1024 * 1024  # 10 MB
    transferred = 5 * 1024 * 1024  # 5 MB
    elapsed = 1.0  # 1 sec -> 5 MB/s
    m5 = calculate_download_metrics(transferred, total, elapsed)
    assert m5["progress_percent"] == 50.0
    assert m5["speed_mb_sec"] == 5.0
    assert m5["eta_seconds"] == 1.0


def test_adv_r4_frontend_contracts_tokens_and_exports():
    """Verify that DownloadStore.ts and DownloadsPage.tsx fulfill all required tokens and exports."""
    store_file = os.path.join("frontend", "src", "stores", "DownloadStore.ts")
    assert os.path.isfile(store_file), f"DownloadStore.ts missing at {store_file}"
    with open(store_file, "r", encoding="utf-8") as f:
        store_src = f.read()

    assert "useDownloadStore" in store_src
    assert "calculateDownloadMetrics" in store_src
    assert "formatSpeed" in store_src
    assert "formatBytes" in store_src
    assert "formatETA" in store_src
    assert "activeDownload" in store_src
    assert "queue" in store_src
    assert "paused" in store_src
    assert "completed" in store_src
    assert "addInstalledGame" in store_src  # Verification of R2 library state transition link

    page_file = os.path.join("frontend", "src", "pages", "DownloadsPage.tsx")
    assert os.path.isfile(page_file), f"DownloadsPage.tsx missing at {page_file}"
    with open(page_file, "r", encoding="utf-8") as f:
        page_src = f.read()

    assert "Download Speed" in page_src
    assert "Active Queue" in page_src
    assert "activeDownloads" in page_src
    assert "Pause" in page_src
    assert "Resume" in page_src
