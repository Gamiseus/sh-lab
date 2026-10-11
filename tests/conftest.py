"""Global pytest fixtures and test harness configuration for SH-LAB E2E tests."""
import os
import pytest
import httpx

BASE_URL = os.getenv("SHLAB_API_URL", "http://localhost:8000")

@pytest.fixture(scope="session")
def base_url() -> str:
    return BASE_URL

@pytest.fixture(scope="session")
def api_client(base_url: str):
    """Synchronous HTTP client for invoking backend endpoints."""
    with httpx.Client(base_url=base_url, timeout=15.0) as client:
        yield client

@pytest.fixture(scope="session")
def fastly_test_url() -> str:
    """Canonical Fastly Steam CDN header image URL (Metro Last Light, App 43160)."""
    return "https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/43160/header.jpg"

@pytest.fixture(scope="session")
def akamai_test_url() -> str:
    """Canonical Akamai Steam CDN header image URL (Counter-Strike, App 10)."""
    return "https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/10/header.jpg"

@pytest.fixture(scope="session")
def cloudflare_test_url() -> str:
    """Canonical Cloudflare Steam CDN header image URL."""
    return "https://shared.cloudflare.steamstatic.com/store_item_assets/steam/apps/10/header.jpg"

@pytest.fixture(scope="session")
def video_trailer_url() -> str:
    """Canonical Steam gameplay video trailer stream URL."""
    return "https://video.fastly.steamstatic.com/store_trailers/256990595/movie480.mp4"
