"""Global pytest fixtures and test harness configuration for SH-LAB E2E tests."""
import os
import shutil
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
def admin_token(api_client: httpx.Client) -> str:
    """Authenticates as the default admin user and returns a valid JWT access token."""
    login_resp = api_client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin"},
    )
    if login_resp.status_code == 200:
        data = login_resp.json()
        return data.get("access_token", "")
    return ""

@pytest.fixture(scope="session")
def admin_headers(admin_token: str) -> dict:
    """Authorization headers for admin-authenticated requests."""
    if not admin_token:
        return {}
    return {
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "application/json",
    }

@pytest.fixture(scope="session")
def regular_user_token(api_client: httpx.Client, admin_headers: dict) -> str:
    """Ensures a non-admin regular user exists and returns its JWT access token."""
    username = "testuser_e2e"
    password = "Password123!"
    
    # Try logging in first
    login_resp = api_client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    if login_resp.status_code == 200:
        return login_resp.json().get("access_token", "")
    
    # If login fails, attempt to create via admin endpoint or register
    create_resp = api_client.post(
        "/api/v1/admin/users",
        headers=admin_headers,
        json={
            "username": username,
            "password": password,
            "email": f"{username}@example.com",
            "is_admin": False,
        },
    )
    if create_resp.status_code in (200, 201):
        login_resp = api_client.post(
            "/api/v1/auth/login",
            json={"username": username, "password": password},
        )
        if login_resp.status_code == 200:
            return login_resp.json().get("access_token", "")
    
    return ""

@pytest.fixture(scope="session")
def regular_headers(regular_user_token: str) -> dict:
    """Authorization headers for regular user requests."""
    if not regular_user_token:
        return {}
    return {
        "Authorization": f"Bearer {regular_user_token}",
        "Content-Type": "application/json",
    }

@pytest.fixture
def mock_local_library(tmp_path):
    """Sets up a temporary simulated local library folder on disk for pre-check tests."""
    lib_dir = tmp_path / "sh_games_lib"
    lib_dir.mkdir(parents=True, exist_ok=True)
    yield lib_dir
    shutil.rmtree(lib_dir, ignore_errors=True)
