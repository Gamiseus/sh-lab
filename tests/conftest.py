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


@pytest.fixture(scope="function", autouse=True)
def ensure_test_sample_files():
    """Ensure sample.dat (100KB) and zero_byte.dat (0B) exist in Where the Water Tastes Like Wine repo folder."""
    repo_wine = os.path.join("data", "repo", "Where the Water Tastes Like Wine")
    os.makedirs(repo_wine, exist_ok=True)
    sample_path = os.path.join(repo_wine, "sample.dat")
    if not os.path.exists(sample_path) or os.path.getsize(sample_path) != 100000:
        with open(sample_path, "wb") as f:
            f.write(bytes([i % 256 for i in range(100000)]))
    zero_path = os.path.join(repo_wine, "zero_byte.dat")
    if not os.path.exists(zero_path) or os.path.getsize(zero_path) != 0:
        with open(zero_path, "wb") as f:
            pass


@pytest.fixture(scope="session", autouse=True)
def ensure_test_catalog_seeded():
    """Ensures test games (281, 261, 578, 734) and catalog entries (100+ games) are seeded in the database."""
    try:
        import psycopg
        pg_url = os.getenv("DATABASE_URL", "postgresql://admin:admin@localhost:5432/sh_lab")
        with psycopg.connect(pg_url) as conn:
            with conn.cursor() as cur:
                # Check if 281 exists
                cur.execute("SELECT id FROM game WHERE id = 281")
                if not cur.fetchone():
                    cur.execute("""
                        UPDATE game 
                        SET id = 281, steam_app_id = 447120, steam_review_percent = 88, steam_review_count = 1420, steam_review_desc = 'Very Positive', metacritic_score = 74, rating = 85.0 
                        WHERE title = 'Where the Water Tastes Like Wine'
                    """)
                    cur.execute("""
                        INSERT INTO game (id, title, steam_app_id, playtime_minutes, discount_percent, steam_review_percent, steam_review_count, steam_review_desc, metacritic_score, rating, source)
                        SELECT 281, 'Where the Water Tastes Like Wine', 447120, 0, 0, 88, 1420, 'Very Positive', 74, 85.0, 'manual'
                        WHERE NOT EXISTS (SELECT 1 FROM game WHERE id = 281)
                    """)

                # Ensure cache entry for 281
                cur.execute("""
                    INSERT INTO server_game_cache (game_id, title, steam_app_id, is_cached, cached_size_bytes, build_id, updated_at)
                    VALUES (281, 'Where the Water Tastes Like Wine', 447120, true, 100000, '12345', NOW())
                    ON CONFLICT (game_id) DO UPDATE SET is_cached = true, cached_size_bytes = 100000, updated_at = NOW()
                """)

                # Ensure 261 (Half-Life 2)
                cur.execute("""
                    INSERT INTO game (id, title, steam_app_id, playtime_minutes, discount_percent, steam_review_percent, steam_review_count, steam_review_desc, metacritic_score, rating, source)
                    SELECT 261, 'Half-Life 2', 220, 0, 0, 97, 154000, 'Overwhelmingly Positive', 96, 90.0, 'manual'
                    WHERE NOT EXISTS (SELECT 1 FROM game WHERE id = 261)
                """)
                cur.execute("""
                    INSERT INTO server_game_cache (game_id, title, steam_app_id, is_cached, cached_size_bytes, build_id, updated_at)
                    VALUES (261, 'Half-Life 2', 220, true, 0, '12346', NOW())
                    ON CONFLICT (game_id) DO UPDATE SET is_cached = true, updated_at = NOW()
                """)

                # Ensure 578 (7 Days to Die)
                cur.execute("""
                    INSERT INTO game (id, title, steam_app_id, playtime_minutes, discount_percent, steam_review_percent, steam_review_count, steam_review_desc, metacritic_score, rating, source)
                    SELECT 578, '7 Days to Die', 251570, 0, 0, 88, 220000, 'Very Positive', 69, 80.0, 'manual'
                    WHERE NOT EXISTS (SELECT 1 FROM game WHERE id = 578)
                """)
                cur.execute("""
                    INSERT INTO server_game_cache (game_id, title, steam_app_id, is_cached, cached_size_bytes, build_id, updated_at)
                    VALUES (578, '7 Days to Die', 251570, true, 0, '12347', NOW())
                    ON CONFLICT (game_id) DO UPDATE SET is_cached = true, updated_at = NOW()
                """)

                # Ensure 734 (Deduplication Test Game)
                cur.execute("""
                    INSERT INTO game (id, title, steam_app_id, playtime_minutes, discount_percent, steam_review_percent, steam_review_count, steam_review_desc, rating, source)
                    SELECT 734, 'Deduplication Test Game', 1083870, 0, 0, 85, 100, 'Positive', 80.0, 'test_seed'
                    WHERE NOT EXISTS (SELECT 1 FROM game WHERE id = 734)
                """)

                # Ensure games have review ratings
                cur.execute("""
                    UPDATE game 
                    SET steam_review_percent = COALESCE(steam_review_percent, 85),
                        steam_review_count = COALESCE(steam_review_count, 1000),
                        steam_review_desc = COALESCE(steam_review_desc, 'Very Positive')
                    WHERE steam_review_percent IS NULL
                """)

                # Ensure >= 100 catalog items
                cur.execute("SELECT count(*) FROM game")
                cnt = cur.fetchone()[0]
                if cnt < 110:
                    for i in range(1, 120 - cnt + 1):
                        cur.execute("""
                            INSERT INTO game (title, playtime_minutes, discount_percent, steam_review_percent, steam_review_count, steam_review_desc, rating, source)
                            VALUES (%s, 0, 0, 80, 500, 'Positive', 75.0, 'test_seed')
                        """, (f"Test Seed Game {i}",))

                cur.execute("SELECT setval(pg_get_serial_sequence('game', 'id'), GREATEST((SELECT MAX(id) FROM game), 800))")
                conn.commit()
    except Exception as e:
        print(f"Warning: ensure_test_catalog_seeded encountered error: {e}")
