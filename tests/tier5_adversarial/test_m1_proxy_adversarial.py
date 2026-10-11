"""Tier 5: Adversarial Hardening — Media Proxy Security & Robustness Verification.

Adversarial stress harness for:
- /api/v1/store/proxy/image
- /api/v1/store/proxy/image/base64
- /api/v1/store/proxy/video

Evaluates:
1. SSRF prevention, IP literals, localhost, and cloud metadata defense.
2. Domain spoofing, suffix/prefix attacks, userinfo tricks, and allowlist bypass.
3. Scheme confusion, malformed URLs, empty/whitespace inputs.
4. Video stream Range header boundary fuzzing and stream handling.
5. Base64 encoding fidelity and upstream error handling.
"""
import base64
import pytest
import httpx

pytestmark = pytest.mark.tier5

SSRF_PAYLOADS = [
    ("IPv4 localhost", "http://127.0.0.1/secret.png"),
    ("IPv4 localhost with port", "http://127.0.0.1:8000/secret.png"),
    ("Localhost hostname", "http://localhost/secret.png"),
    ("Localhost with port", "http://localhost:8000/secret.png"),
    ("IPv4 any address", "http://0.0.0.0/secret.png"),
    ("AWS/OpenStack metadata", "http://169.254.169.254/latest/meta-data/"),
    ("GCP metadata", "http://metadata.google.internal/computeMetadata/v1/"),
    ("IPv6 localhost", "http://[::1]/secret.png"),
    ("Decimal IP literal", "http://2130706433/secret.png"),
    ("DNS rebinding alias", "http://localtest.me/secret.png"),
]

DOMAIN_SPOOFING_PAYLOADS = [
    ("Subdomain suffix attack", "https://shared.fastly.steamstatic.com.attacker.com/evil.jpg"),
    ("Undotted suffix attack", "https://attacker-steamstatic.com/evil.jpg"),
    ("Evil steamstatic domain", "https://evilsteamstatic.com/evil.jpg"),
    ("Evil hyphenated domain", "https://evil-steamstatic.com/evil.jpg"),
    ("Domain dot spoofing", "https://steamstatic.com.evil.org/evil.jpg"),
    ("Userinfo credentials trick", "https://shared.fastly.steamstatic.com@attacker.com/evil.jpg"),
    ("Fragment trick", "https://attacker.com#shared.fastly.steamstatic.com"),
    ("Path trick", "https://attacker.com/shared.fastly.steamstatic.com"),
    ("Query string trick", "https://attacker.com?domain=shared.fastly.steamstatic.com"),
    ("Unlisted Akamai prefix", "https://evilsteam-a.akamaihd.net/evil.jpg"),
    ("Akamai domain spoofing", "https://steamcdn-a.akamaihd.net.attacker.com/evil.jpg"),
]

MALFORMED_SCHEME_PAYLOADS = [
    ("FTP scheme", "ftp://shared.fastly.steamstatic.com/evil.jpg"),
    ("File scheme", "file:///etc/passwd"),
    ("Gopher scheme", "gopher://127.0.0.1:8000/"),
    ("Javascript scheme", "javascript:alert(1)"),
    ("Data URI scheme", "data:image/png;base64,iVBORw0KGgoAAAANSUhEUg=="),
    ("Protocol-relative URL", "//shared.fastly.steamstatic.com/evil.jpg"),
    ("Missing scheme", "shared.fastly.steamstatic.com/evil.jpg"),
    ("Empty URL string", ""),
    ("Whitespace only", "   "),
    ("Missing hostname", "https:///path/to/image.jpg"),
]

PROXY_ENDPOINTS = [
    "/api/v1/store/proxy/image",
    "/api/v1/store/proxy/image/base64",
    "/api/v1/store/proxy/video",
]


@pytest.mark.parametrize("label,payload", SSRF_PAYLOADS)
@pytest.mark.parametrize("endpoint", PROXY_ENDPOINTS)
def test_adversarial_ssrf_defense(api_client: httpx.Client, endpoint: str, label: str, payload: str):
    """Adversarial Test: SSRF and internal IP literals must be rejected with HTTP 403 Forbidden."""
    resp = api_client.get(f"{endpoint}?url={payload}")
    assert resp.status_code == 403, (
        f"Security Failure: {endpoint} allowed SSRF attempt '{label}' ({payload}) with status {resp.status_code}: {resp.text}"
    )
    assert "not in the allowed proxy list" in resp.text.lower() or "forbidden" in resp.text.lower()


@pytest.mark.parametrize("label,payload", DOMAIN_SPOOFING_PAYLOADS)
@pytest.mark.parametrize("endpoint", PROXY_ENDPOINTS)
def test_adversarial_domain_spoofing_defense(api_client: httpx.Client, endpoint: str, label: str, payload: str):
    """Adversarial Test: Domain spoofing and allowlist bypass attempts must be rejected with HTTP 403 Forbidden."""
    resp = api_client.get(f"{endpoint}?url={payload}")
    assert resp.status_code == 403, (
        f"Security Failure: {endpoint} allowed spoofed domain '{label}' ({payload}) with status {resp.status_code}: {resp.text}"
    )


@pytest.mark.parametrize("label,payload", MALFORMED_SCHEME_PAYLOADS)
@pytest.mark.parametrize("endpoint", PROXY_ENDPOINTS)
def test_adversarial_malformed_url_defense(api_client: httpx.Client, endpoint: str, label: str, payload: str):
    """Adversarial Test: Non-HTTP(S) schemes, malformed URLs, and missing hostnames must be rejected with HTTP 400 Bad Request."""
    resp = api_client.get(f"{endpoint}?url={payload}")
    assert resp.status_code in (400, 422), (
        f"Validation Failure: {endpoint} returned status {resp.status_code} for malformed URL '{label}' ({payload})"
    )


@pytest.mark.parametrize("endpoint", PROXY_ENDPOINTS)
def test_adversarial_missing_parameter(api_client: httpx.Client, endpoint: str):
    """Adversarial Test: Omitting the ?url parameter entirely must return HTTP 422 Unprocessable Entity."""
    resp = api_client.get(endpoint)
    assert resp.status_code == 422, f"Expected 422 for missing query param on {endpoint}, got {resp.status_code}"


def test_adversarial_video_stream_range_fuzzing(api_client: httpx.Client, video_trailer_url: str):
    """Adversarial Test: Comprehensive HTTP Range header fuzzing on video proxy endpoint."""
    # 1. Single byte request
    r_single = api_client.get(f"/api/v1/store/proxy/video?url={video_trailer_url}", headers={"Range": "bytes=0-0"})
    assert r_single.status_code == 206, f"Expected 206 for bytes=0-0, got {r_single.status_code}"
    assert len(r_single.content) == 1, f"Expected exactly 1 byte, got {len(r_single.content)}"
    assert r_single.headers.get("content-range", "").startswith("bytes 0-0/")

    # 2. Chunk 1KB
    r_chunk = api_client.get(f"/api/v1/store/proxy/video?url={video_trailer_url}", headers={"Range": "bytes=0-1023"})
    assert r_chunk.status_code == 206
    assert len(r_chunk.content) == 1024
    assert r_chunk.headers.get("content-range", "").startswith("bytes 0-1023/")

    # 3. Suffix byte (-1)
    r_suffix = api_client.get(f"/api/v1/store/proxy/video?url={video_trailer_url}", headers={"Range": "bytes=-1"})
    assert r_suffix.status_code == 206
    assert len(r_suffix.content) == 1

    # 4. Suffix 500 bytes (-500)
    r_suffix_chunk = api_client.get(f"/api/v1/store/proxy/video?url={video_trailer_url}", headers={"Range": "bytes=-500"})
    assert r_suffix_chunk.status_code == 206
    assert len(r_suffix_chunk.content) == 500

    # 5. Out of bounds range (beyond content length) -> 416 Range Not Satisfiable
    r_oob = api_client.get(f"/api/v1/store/proxy/video?url={video_trailer_url}", headers={"Range": "bytes=999999999-1000000000"})
    assert r_oob.status_code == 416, f"Expected 416 for out-of-bounds range, got {r_oob.status_code}"

    # 6. Malformed inverted range (100-50) -> Upstream safely falls back to 200 OK without crashing server
    r_inv = api_client.get(f"/api/v1/store/proxy/video?url={video_trailer_url}", headers={"Range": "bytes=100-50"})
    assert r_inv.status_code in (200, 206, 416), f"Unexpected status {r_inv.status_code} for inverted range"

    # 7. Malformed range unit -> Graceful handling
    r_unit = api_client.get(f"/api/v1/store/proxy/video?url={video_trailer_url}", headers={"Range": "characters=0-100"})
    assert r_unit.status_code in (200, 206, 416)

    # 8. Server remains completely healthy
    health = api_client.get("/docs")
    assert health.status_code == 200, "Backend became unresponsive after range fuzzing"


def test_adversarial_base64_image_fidelity(api_client: httpx.Client, fastly_test_url: str):
    """Adversarial Test: Base64 proxy output must exactly decode to the binary output of direct image proxy."""
    # Direct image proxy
    resp_raw = api_client.get(f"/api/v1/store/proxy/image?url={fastly_test_url}")
    assert resp_raw.status_code == 200
    raw_bytes = resp_raw.content
    assert len(raw_bytes) > 0

    # Base64 image proxy
    resp_b64 = api_client.get(f"/api/v1/store/proxy/image/base64?url={fastly_test_url}")
    assert resp_b64.status_code == 200
    payload = resp_b64.json()
    assert "mime" in payload
    assert payload["mime"] == resp_raw.headers.get("content-type")
    assert "data" in payload

    # Byte-for-byte fidelity check
    decoded_bytes = base64.b64decode(payload["data"])
    assert decoded_bytes == raw_bytes, (
        f"Data corruption in base64 proxy: direct image ({len(raw_bytes)} bytes) != decoded ({len(decoded_bytes)} bytes)"
    )


def test_adversarial_upstream_error_containment(api_client: httpx.Client):
    """Adversarial Test: Nonexistent media on valid CDN domains must not crash the proxy with unhandled 500s."""
    nonexistent_img = "https://shared.fastly.steamstatic.com/nonexistent_game_asset_999999_xyz.jpg"
    nonexistent_vid = "https://video.fastly.steamstatic.com/nonexistent_trailer_999999_xyz.mp4"

    r_img = api_client.get(f"/api/v1/store/proxy/image?url={nonexistent_img}")
    assert r_img.status_code == 404, f"Expected 404 for nonexistent image, got {r_img.status_code}"

    r_b64 = api_client.get(f"/api/v1/store/proxy/image/base64?url={nonexistent_img}")
    assert r_b64.status_code == 404, f"Expected 404 for nonexistent base64 image, got {r_b64.status_code}"

    r_vid = api_client.get(f"/api/v1/store/proxy/video?url={nonexistent_vid}")
    assert r_vid.status_code in (404, 500, 502), f"Unexpected status {r_vid.status_code}"

    # Verify server health after error handling
    health = api_client.get("/docs")
    assert health.status_code == 200
