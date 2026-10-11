"""Tier 2: Boundary & Corner Cases — R1: Media Proxy & Audio/Video Boundaries.

Coverage Requirements: >=5 boundary tests for R1.
1. Malicious/unlisted domains rejected with HTTP 403.
2. Domain spoofing attempts (e.g. steamstatic.com.attacker.com) rejected with HTTP 403.
3. Malformed/non-URL parameters rejected with HTTP 400.
4. Empty URL query parameter rejected with HTTP 400.
5. Extreme Range headers on video proxy handled gracefully.
6. Non-existent asset on allowed domain handled without backend 500 crash.
"""
import pytest
import httpx

pytestmark = pytest.mark.tier2

def test_proxy_unauthorized_domain_rejected(api_client: httpx.Client):
    """R1-B.1: Requests to domains outside the proxy allowlist must be rejected with HTTP 403."""
    resp = api_client.get("/api/v1/store/proxy/image?url=https://evil-attacker.com/malicious.png")
    assert resp.status_code == 403, f"Expected 403 Forbidden for unauthorized domain, got {resp.status_code}"
    assert "not in the allowed proxy list" in resp.text.lower() or "forbidden" in resp.text.lower()


def test_proxy_subdomain_spoofing_rejected(api_client: httpx.Client):
    """R1-B.2: Spoofed subdomains (steamstatic.com.attacker.com) must be rejected with HTTP 403."""
    resp = api_client.get(
        "/api/v1/store/proxy/image?url=https://shared.fastly.steamstatic.com.attacker.com/exploit.jpg"
    )
    assert resp.status_code == 403, f"Expected 403 Forbidden for spoofed domain, got {resp.status_code}"


def test_proxy_malformed_url_rejected(api_client: httpx.Client):
    """R1-B.3: Malformed or non-HTTP URLs return HTTP 400 Bad Request."""
    resp = api_client.get("/api/v1/store/proxy/image?url=not_a_valid_url")
    assert resp.status_code == 400, f"Expected 400 Bad Request for malformed URL, got {resp.status_code}"


def test_proxy_empty_url_parameter(api_client: httpx.Client):
    """R1-B.4: Empty URL parameter returns HTTP 400 Bad Request."""
    resp = api_client.get("/api/v1/store/proxy/image?url=")
    assert resp.status_code in (400, 422), f"Expected 400 or 422 for empty URL, got {resp.status_code}"


def test_proxy_video_extreme_range_header(api_client: httpx.Client, video_trailer_url: str):
    """R1-B.5: Video proxy handles single-byte Range request (bytes=0-0)."""
    headers = {"Range": "bytes=0-0"}
    resp = api_client.get(f"/api/v1/store/proxy/video?url={video_trailer_url}", headers=headers)
    assert resp.status_code in (200, 206), f"Expected 200 or 206, got {resp.status_code}"


def test_proxy_upstream_404_handled_gracefully(api_client: httpx.Client):
    """R1-B.6: Upstream 404 on valid domain returns error status without crashing server."""
    resp = api_client.get(
        "/api/v1/store/proxy/image?url=https://shared.fastly.steamstatic.com/nonexistent_image_xyz_999.jpg"
    )
    # Server should return 404, 502, or 500 with handled error, but server must stay alive
    assert resp.status_code in (404, 500, 502)
    # Verify server is still healthy
    health = api_client.get("/docs")
    assert health.status_code == 200, "Backend server became unresponsive after upstream error"
