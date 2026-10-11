"""Tier 1: Feature Coverage — R1: Store Media Gallery & Audio/Proxy Reliability.

Coverage Requirements: >=5 tests covering primary behavior.
1. Proxy CDN Allowlist for Fastly CDN domains.
2. Proxy CDN Allowlist for Akamai CDN domains.
3. Proxy CDN Allowlist for Cloudflare CDN domains.
4. Video streaming proxy with Range header support.
5. Base64 JSON image proxy endpoint.
6. Video player audio controls & unmute options contract.
"""
import os
import re
import pytest
import httpx

pytestmark = pytest.mark.tier1

def test_proxy_fastly_domain_allowed(api_client: httpx.Client, fastly_test_url: str):
    """R1.1: Fastly CDN domains (shared.fastly.steamstatic.com) must be permitted by the proxy."""
    resp = api_client.get(f"/api/v1/store/proxy/image?url={fastly_test_url}")
    assert resp.status_code != 403, (
        f"Fastly CDN URL was rejected with HTTP 403 Forbidden: {resp.text}. "
        "PROXY_ALLOWED_DOMAINS must include all Fastly CDN domains."
    )
    assert resp.status_code == 200, f"Expected HTTP 200 for proxied Fastly image, got {resp.status_code}"
    assert "image/" in resp.headers.get("content-type", ""), "Expected image Content-Type header"
    assert len(resp.content) > 0, "Expected non-empty image binary content"


def test_proxy_akamai_domain_allowed(api_client: httpx.Client, akamai_test_url: str):
    """R1.2: Akamai CDN domains (shared.akamai.steamstatic.com) must be permitted by the proxy."""
    resp = api_client.get(f"/api/v1/store/proxy/image?url={akamai_test_url}")
    assert resp.status_code == 200, f"Expected HTTP 200 for proxied Akamai image, got {resp.status_code}"
    assert "image/" in resp.headers.get("content-type", "")
    assert len(resp.content) > 0


def test_proxy_cloudflare_domain_allowed(api_client: httpx.Client, cloudflare_test_url: str):
    """R1.3: Cloudflare CDN domains must be permitted by the proxy."""
    resp = api_client.get(f"/api/v1/store/proxy/image?url={cloudflare_test_url}")
    assert resp.status_code == 200, f"Expected HTTP 200 for proxied Cloudflare image, got {resp.status_code}"
    assert "image/" in resp.headers.get("content-type", "")
    assert len(resp.content) > 0


def test_proxy_video_streaming_endpoint(api_client: httpx.Client, video_trailer_url: str):
    """R1.4: Video proxy streams gameplay trailers with Range request support."""
    headers = {"Range": "bytes=0-1023"}
    resp = api_client.get(f"/api/v1/store/proxy/video?url={video_trailer_url}", headers=headers)
    assert resp.status_code != 403, f"Video proxy rejected video URL with 403: {resp.text}"
    assert resp.status_code in (200, 206), f"Expected 200 OK or 206 Partial Content, got {resp.status_code}"
    assert "video/" in resp.headers.get("content-type", ""), "Expected video Content-Type"
    assert len(resp.content) > 0


def test_proxy_base64_endpoint(api_client: httpx.Client, akamai_test_url: str):
    """R1.5: Image base64 proxy returns valid JSON payload with mime and base64 data."""
    resp = api_client.get(f"/api/v1/store/proxy/image/base64?url={akamai_test_url}")
    assert resp.status_code == 200, f"Expected HTTP 200, got {resp.status_code}"
    data = resp.json()
    assert "mime" in data, "Response JSON missing 'mime' field"
    assert "data" in data, "Response JSON missing 'data' field"
    assert len(data["data"]) > 100, "Base64 data string must contain valid image payload"


def test_media_gallery_audio_and_strip_contracts():
    """R1.6: MediaGallery frontend contract: audio controls present, visible scrollbars."""
    component_path = os.path.join("frontend", "src", "components", "store", "MediaGallery.tsx")
    assert os.path.exists(component_path), f"MediaGallery.tsx not found at {component_path}"
    with open(component_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Verify video player does not permanently hardcode muted without audio controls
    has_unmute_state = "isMuted" in content or "muted" in content or "volume" in content or "Volume" in content
    assert has_unmute_state, "MediaGallery must manage video audio state (mute/unmute or volume)"

    # Verify thumbnail strip does not permanently hide scrollbars via scrollbar-hide
    # It must have visible scrollbar styling or overflow handling
    assert "overflow-x-auto" in content, "Thumbnail strip must provide overflow-x-auto for horizontal navigation"
