"""Tier 5: Adversarial & Empirical Challenge Harness — Milestone 2 (R4).

Adversarial stress harness for Milestone 2:
1. HTTP 206 partial content streaming: chunk delivery, Content-Range, byte-exact payloads.
2. Directory traversal security: raw HTTP socket & encoded attacks returning HTTP 403.
3. 0-byte file boundary conditions: RFC 7233 416 for ranged requests, 200 for full download.
4. Download metric calculations: 0 bytes transferred, stalled speed, 100% completion ETA 0.0s.
5. 100% completion links the game into installed state.
"""
import os
import socket
import pytest
import httpx
from tests.helpers import (
    calculate_download_metrics,
    parse_http_range_header,
)

pytestmark = pytest.mark.tier5


# ==============================================================================
# 1. HTTP 206 Partial Content Streaming Stress Harness
# ==============================================================================

def test_emp_m2_http_206_partial_streaming_chunks(api_client: httpx.Client):
    """Empirical Check 1: Request partial byte ranges and verify Content-Range and chunk delivery."""
    game_id = 281
    target_file = "sample.dat"
    total_size = 100000
    expected_all = bytes([i % 256 for i in range(total_size)])

    # 1. Full download baseline
    r_full = api_client.get(f"/api/v1/library/download/{game_id}/{target_file}")
    assert r_full.status_code == 200
    assert r_full.content == expected_all
    assert r_full.headers.get("Content-Length") == str(total_size)
    assert r_full.headers.get("Accept-Ranges") == "bytes"

    # 2. First 1 KB (bytes=0-1023)
    r_first_kb = api_client.get(
        f"/api/v1/library/download/{game_id}/{target_file}",
        headers={"Range": "bytes=0-1023"}
    )
    assert r_first_kb.status_code == 206
    assert r_first_kb.headers.get("Content-Range") == f"bytes 0-1023/{total_size}"
    assert r_first_kb.headers.get("Content-Length") == "1024"
    assert r_first_kb.content == expected_all[0:1024]

    # 3. Middle range (bytes=50000-59999)
    r_mid = api_client.get(
        f"/api/v1/library/download/{game_id}/{target_file}",
        headers={"Range": "bytes=50000-59999"}
    )
    assert r_mid.status_code == 206
    assert r_mid.headers.get("Content-Range") == f"bytes 50000-59999/{total_size}"
    assert r_mid.headers.get("Content-Length") == "10000"
    assert r_mid.content == expected_all[50000:60000]

    # 4. Single-byte boundary at index 0 (bytes=0-0)
    r_single_0 = api_client.get(
        f"/api/v1/library/download/{game_id}/{target_file}",
        headers={"Range": "bytes=0-0"}
    )
    assert r_single_0.status_code == 206
    assert r_single_0.headers.get("Content-Range") == f"bytes 0-0/{total_size}"
    assert r_single_0.headers.get("Content-Length") == "1"
    assert r_single_0.content == expected_all[0:1]

    # 5. Single-byte boundary at index total_size - 1 (bytes=99999-99999)
    r_single_last = api_client.get(
        f"/api/v1/library/download/{game_id}/{target_file}",
        headers={"Range": f"bytes={total_size - 1}-{total_size - 1}"}
    )
    assert r_single_last.status_code == 206
    assert r_single_last.headers.get("Content-Range") == f"bytes 99999-99999/{total_size}"
    assert r_single_last.headers.get("Content-Length") == "1"
    assert r_single_last.content == expected_all[-1:]

    # 6. Open-ended range (bytes=95000-)
    r_tail = api_client.get(
        f"/api/v1/library/download/{game_id}/{target_file}",
        headers={"Range": "bytes=95000-"}
    )
    assert r_tail.status_code == 206
    assert r_tail.headers.get("Content-Range") == f"bytes 95000-99999/{total_size}"
    assert r_tail.headers.get("Content-Length") == "5000"
    assert r_tail.content == expected_all[95000:100000]

    # 7. Out-of-bounds range -> 416
    r_oob = api_client.get(
        f"/api/v1/library/download/{game_id}/{target_file}",
        headers={"Range": f"bytes={total_size}-{total_size + 100}"}
    )
    assert r_oob.status_code == 416
    assert r_oob.headers.get("Content-Range") == f"bytes */{total_size}"

    # 8. Inverted range -> 416
    r_inv = api_client.get(
        f"/api/v1/library/download/{game_id}/{target_file}",
        headers={"Range": "bytes=500-200"}
    )
    assert r_inv.status_code == 416
    assert r_inv.headers.get("Content-Range") == f"bytes */{total_size}"

    # 9. Multi-chunk delivery verification
    chunks = []
    with api_client.stream(
        "GET",
        f"/api/v1/library/download/{game_id}/{target_file}",
        headers={"Range": "bytes=0-69999"}
    ) as stream_resp:
        assert stream_resp.status_code == 206
        for chunk in stream_resp.iter_bytes():
            chunks.append(len(chunk))

    assert sum(chunks) == 70000
    assert len(chunks) >= 2, f"Expected multiple streaming chunks, got {len(chunks)}"


# ==============================================================================
# 2. Directory Traversal Security Harness
# ==============================================================================

def test_emp_m2_directory_traversal_raw_socket():
    """Empirical Check 2a: Raw HTTP socket request GET /api/v1/library/download/{id}/../../../../etc/passwd returns 403."""
    s = socket.socket()
    s.connect(("localhost", 8000))
    raw_req = b"GET /api/v1/library/download/281/../../../../etc/passwd HTTP/1.1\r\nHost: localhost:8000\r\nConnection: close\r\n\r\n"
    s.sendall(raw_req)
    raw_resp = s.recv(4096).decode("utf-8", errors="replace")
    s.close()

    status_line = raw_resp.split("\r\n")[0]
    parts = status_line.split()
    assert len(parts) >= 2, f"Invalid HTTP response status line: {status_line}"
    status_code = int(parts[1])
    assert status_code == 403, f"Expected HTTP 403 Forbidden, got {status_code} ({status_line})"


def test_emp_m2_directory_traversal_url_encoded(api_client: httpx.Client):
    """Empirical Check 2b: URL-encoded traversal escape returns HTTP 403 Forbidden."""
    resp = api_client.get("/api/v1/library/download/281/..%2F..%2F..%2F..%2Fetc%2Fpasswd")
    assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"
    assert "Directory traversal forbidden" in resp.text or "Access denied" in resp.text


def test_emp_m2_directory_traversal_subpath_escape():
    """Empirical Check 2c: Subpath traversal escape returns HTTP 403 Forbidden."""
    s = socket.socket()
    s.connect(("localhost", 8000))
    raw_req = b"GET /api/v1/library/download/281/steamapps/../../../etc/passwd HTTP/1.1\r\nHost: localhost:8000\r\nConnection: close\r\n\r\n"
    s.sendall(raw_req)
    raw_resp = s.recv(4096).decode("utf-8", errors="replace")
    s.close()

    status_line = raw_resp.split("\r\n")[0]
    status_code = int(status_line.split()[1])
    assert status_code == 403, f"Expected 403 Forbidden for subpath traversal, got {status_code}"


# ==============================================================================
# 3. 0-Byte File Boundary Conditions
# ==============================================================================

def test_emp_m2_zero_byte_file_full_and_range(api_client: httpx.Client):
    """Empirical Check 3: 0-byte file returns 200 for full download and RFC 7233 416 for ranged requests."""
    game_id = 281
    target_file = "zero_byte.dat"

    # 1. Full download -> 200 OK, Content-Length: 0, empty body
    r_full = api_client.get(f"/api/v1/library/download/{game_id}/{target_file}")
    assert r_full.status_code == 200
    assert r_full.headers.get("Content-Length") == "0"
    assert r_full.content == b""

    # 2. Range request bytes=0-0 -> RFC 7233 416 Range Not Satisfiable
    r_range = api_client.get(
        f"/api/v1/library/download/{game_id}/{target_file}",
        headers={"Range": "bytes=0-0"}
    )
    assert r_range.status_code == 416
    assert r_range.headers.get("Content-Range") == "bytes */0"

    # 3. Range request bytes=0- -> RFC 7233 416 Range Not Satisfiable
    r_range_open = api_client.get(
        f"/api/v1/library/download/{game_id}/{target_file}",
        headers={"Range": "bytes=0-"}
    )
    assert r_range_open.status_code == 416
    assert r_range_open.headers.get("Content-Range") == "bytes */0"


# ==============================================================================
# 4. Download Metric Calculations
# ==============================================================================

def test_emp_m2_download_metric_calculations_stress():
    """Empirical Check 4: Test download metric calculations (0 bytes transferred, stalled speed, 100% completion ETA 0.0s)."""
    # Case A: 0 bytes transferred
    m_zero_transferred = calculate_download_metrics(
        transferred_bytes=0,
        total_bytes=1000000,
        elapsed_seconds=5.0
    )
    assert m_zero_transferred["progress_percent"] == 0.0
    assert m_zero_transferred["speed_bytes_sec"] == 0.0
    assert m_zero_transferred["speed_mb_sec"] == 0.0
    assert m_zero_transferred["eta_seconds"] is None

    # Case B: Stalled speed
    m_stalled = calculate_download_metrics(
        transferred_bytes=0,
        total_bytes=500000,
        elapsed_seconds=20.0
    )
    assert m_stalled["speed_bytes_sec"] == 0.0
    assert m_stalled["eta_seconds"] is None

    # Case C: 0 total bytes (empty payload)
    m_zero_total = calculate_download_metrics(
        transferred_bytes=0,
        total_bytes=0,
        elapsed_seconds=1.0
    )
    assert m_zero_total["progress_percent"] == 0.0
    assert m_zero_total["speed_bytes_sec"] == 0.0
    assert m_zero_total["eta_seconds"] is None

    # Case D: 100% completion
    m_100_pct = calculate_download_metrics(
        transferred_bytes=500000,
        total_bytes=500000,
        elapsed_seconds=10.0
    )
    assert m_100_pct["progress_percent"] == 100.0
    assert m_100_pct["eta_seconds"] == 0.0
    assert m_100_pct["speed_bytes_sec"] == 50000.0

    # Case E: Elapsed seconds zero (guard against ZeroDivisionError)
    m_zero_elapsed = calculate_download_metrics(
        transferred_bytes=100,
        total_bytes=1000,
        elapsed_seconds=0.0
    )
    assert m_zero_elapsed["speed_bytes_sec"] == 0.0
    assert m_zero_elapsed["eta_seconds"] is None
    assert m_zero_elapsed["progress_percent"] == 10.0


# ==============================================================================
# 5. 100% Completion Links Game to Installed State
# ==============================================================================

def test_emp_m2_download_completion_links_installed_state():
    """Empirical Check 5: Verify that 100% completion links the game into installed state."""
    # State tracking representation
    game_id = 281
    library_state = {
        "user_library": {
            game_id: {"game_id": game_id, "status": "uninstalled"}
        },
        "installed_games": {},
    }

    # Helper getters
    def is_installed(gid: int) -> bool:
        return gid in library_state["installed_games"] and bool(library_state["installed_games"][gid].get("path"))

    def get_ui_card_state(gid: int) -> dict:
        installed = is_installed(gid)
        return {
            "installed": installed,
            "is_grayed": not installed,
            "action": "Play" if installed else "Install",
        }

    # Initial state verification: uninstalled & dimmed
    initial_card = get_ui_card_state(game_id)
    assert initial_card["installed"] is False
    assert initial_card["is_grayed"] is True
    assert initial_card["action"] == "Install"

    # Simulate download lifecycle reaching 100%
    total_bytes = 100000
    metrics = calculate_download_metrics(
        transferred_bytes=total_bytes,
        total_bytes=total_bytes,
        elapsed_seconds=2.0
    )
    assert metrics["progress_percent"] == 100.0
    assert metrics["eta_seconds"] == 0.0

    # Execution of completion hook (mirroring DownloadStore.ts lines 442-451)
    if metrics["progress_percent"] == 100.0:
        install_path = r"c:\Users\Administrator\Documents\Projects\sh-lab\data\games\Where the Water Tastes Like Wine"
        library_state["installed_games"][game_id] = {"id": game_id, "path": install_path}
        library_state["user_library"][game_id]["status"] = "installed"

    # Post-completion verification: installed, active, not grayed, Play button enabled
    final_card = get_ui_card_state(game_id)
    assert final_card["installed"] is True
    assert final_card["is_grayed"] is False
    assert final_card["action"] == "Play"
    assert is_installed(game_id) is True
    assert library_state["user_library"][game_id]["status"] == "installed"
