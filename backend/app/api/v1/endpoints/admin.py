import logging
import os
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlmodel import Session, select, or_
from pydantic import BaseModel
from app.core.db import get_session
from app.core.config import settings
from app.core.auth import require_admin
from app.core.security import hash_password
from app.models.game import Game
from app.models.user import User, UserRead, UserCreate
from app.models.config import SystemConfig
from app.services.igdb import IGDBClient
from app.services.metadata import MetadataService

logger = logging.getLogger(__name__)

router = APIRouter()

# ============================================================
# User Management Schemas
# ============================================================

class AdminUserCreate(BaseModel):
    username: str
    password: str
    email: Optional[str] = None
    display_name: Optional[str] = None
    is_admin: bool = False

class AdminUserUpdate(BaseModel):
    display_name: Optional[str] = None
    email: Optional[str] = None
    is_admin: Optional[bool] = None
    is_active: Optional[bool] = None
    new_password: Optional[str] = None

# ============================================================
# User Management Endpoints (Admin Only)
# ============================================================

@router.get("/users", response_model=List[UserRead])
async def list_users(
    session: Session = Depends(get_session),
    admin: User = Depends(require_admin)
):
    """List all users (admin only)."""
    users = session.exec(select(User)).all()
    return users

@router.post("/users", response_model=UserRead)
async def create_user(
    user_data: AdminUserCreate,
    session: Session = Depends(get_session),
    admin: User = Depends(require_admin)
):
    """Create a new user (admin only)."""
    # Check if username exists
    existing = session.exec(select(User).where(User.username == user_data.username)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    new_user = User(
        username=user_data.username,
        display_name=user_data.display_name or user_data.username,
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        is_admin=user_data.is_admin,
        is_active=True
    )
    session.add(new_user)
    session.commit()
    session.refresh(new_user)
    return new_user

@router.get("/users/{user_id}", response_model=UserRead)
async def get_user(
    user_id: int,
    session: Session = Depends(get_session),
    admin: User = Depends(require_admin)
):
    """Get a specific user by ID (admin only)."""
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.put("/users/{user_id}", response_model=UserRead)
async def update_user(
    user_id: int,
    user_data: AdminUserUpdate,
    session: Session = Depends(get_session),
    admin: User = Depends(require_admin)
):
    """Update a user (admin only)."""
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user_data.display_name is not None:
        user.display_name = user_data.display_name
    if user_data.email is not None:
        user.email = user_data.email
    if user_data.is_admin is not None:
        user.is_admin = user_data.is_admin
    if user_data.is_active is not None:
        user.is_active = user_data.is_active
    if user_data.new_password:
        user.password_hash = hash_password(user_data.new_password)
    
    session.add(user)
    session.commit()
    session.refresh(user)
    return user

@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    session: Session = Depends(get_session),
    admin: User = Depends(require_admin)
):
    """Delete a user (admin only)."""
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent deleting self
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    
    session.delete(user)
    session.commit()
    return {"status": "success", "message": f"User '{user.username}' deleted"}

# ============================================================
# System Config Endpoints (Admin Only)
# ============================================================

@router.get("/config")
async def get_all_config(
    session: Session = Depends(get_session),
    admin: User = Depends(require_admin)
):
    """Get all system configuration (admin only)."""
    configs = session.exec(select(SystemConfig)).all()
    config_dict = {c.key: c for c in configs}
    
    # helper to check if key exists
    def ensure_env_config(key: str, env_val: Optional[str], desc: str, is_secret: bool):
        if key not in config_dict and env_val:
            config_dict[key] = SystemConfig(
                key=key,
                value=env_val,
                value_type="string",
                description=f"{desc} (from environment)",
                is_secret=is_secret
            )

    from app.core.config import settings
    ensure_env_config("steam_api_key", settings.STEAM_WEB_API_KEY, "Steam Web API Key", True)
    ensure_env_config("steam_username", settings.STEAM_USERNAME, "Steam Username", False)
    ensure_env_config("steam_password", settings.STEAM_PASSWORD, "Steam Password", True)
    
    # Mask secret values
    result = []
    for cfg in config_dict.values():
        result.append({
            "key": cfg.key,
            "value": "***" if cfg.is_secret else cfg.value,
            "value_type": cfg.value_type,
            "description": cfg.description,
            "is_secret": cfg.is_secret
        })
    return result

@router.put("/config/{key}")
async def update_config(
    key: str,
    value: str,
    session: Session = Depends(get_session),
    admin: User = Depends(require_admin)
):
    """Update a system configuration value (admin only)."""
    cfg = session.get(SystemConfig, key)
    if not cfg:
        raise HTTPException(status_code=404, detail=f"Config key '{key}' not found")
    
    cfg.value = value
    cfg.updated_by = admin.id
    session.add(cfg)
    session.commit()
    return {"status": "success", "message": f"Config '{key}' updated"}

# ============================================================
# Game Management Endpoints (Admin Only)
# ============================================================

from app.models.game import GameRead, GameCreate, GameUpdate

class AdminGameCreate(BaseModel):
    title: str
    description: Optional[str] = None
    developer: Optional[str] = None
    publisher: Optional[str] = None
    genres: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    source: Optional[str] = "manual"
    steam_app_id: Optional[int] = None
    executable_path: Optional[str] = None
    launch_args: Optional[str] = None

class AdminGameUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    developer: Optional[str] = None
    publisher: Optional[str] = None
    genres: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    source: Optional[str] = None
    steam_app_id: Optional[int] = None
    igdb_id: Optional[int] = None
    executable_path: Optional[str] = None
    launch_args: Optional[str] = None
    cover_url: Optional[str] = None
    background_url: Optional[str] = None
    trailer_url: Optional[str] = None
    version: Optional[str] = None

@router.get("/games", response_model=List[GameRead])
async def list_games_admin(
    offset: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    session: Session = Depends(get_session),
    admin: User = Depends(require_admin)
):
    """List all games with optional search (admin only)."""
    query = select(Game)
    if search:
        search_term = f"%{search}%"
        from sqlmodel import or_  # already imported at top
        query = query.where(
            or_(
                Game.title.ilike(search_term),
                Game.description.ilike(search_term)
            )
        )
    query = query.order_by(Game.title).offset(offset).limit(limit)
    
    # DEBUG LOGGING
    logger.info(f"DEBUG: Listing games offset={offset} limit={limit} search={search}")
    results = session.exec(query).all()
    logger.info(f"DEBUG: Found {len(results)} games")
    if len(results) > 0:
        logger.info(f"DEBUG: First game: {results[0].title} (ID: {results[0].id})")
        
    return results


# IMPORTANT: This must be BEFORE /games/{game_id} routes to avoid route conflict
@router.get("/games/search")
async def search_games(
    query: str,
    limit: int = 20,
    admin: User = Depends(require_admin)
):
    """
    Fuzzy search Steam store for games to add.
    Returns basic info for each result.
    """
    from app.services.steam_licenses import search_steam_store
    
    if not query or len(query) < 2:
        raise HTTPException(
            status_code=400,
            detail="Query must be at least 2 characters"
        )
    
    results = await search_steam_store(query, limit=limit)
    return {"results": results, "total": len(results)}


@router.post("/games", response_model=GameRead)
async def create_game(
    game_data: AdminGameCreate,
    session: Session = Depends(get_session),
    admin: User = Depends(require_admin)
):
    """Create a new game manually (admin only)."""
    # Check for duplicate title
    existing = session.exec(select(Game).where(Game.title == game_data.title)).first()
    if existing:
        raise HTTPException(status_code=400, detail="A game with this title already exists")
    
    new_game = Game(
        title=game_data.title,
        description=game_data.description,
        developer=game_data.developer,
        publisher=game_data.publisher,
        genres=game_data.genres,
        tags=game_data.tags,
        source=game_data.source or "manual",
        steam_app_id=game_data.steam_app_id,
        executable_path=game_data.executable_path,
        launch_args=game_data.launch_args
    )
    session.add(new_game)
    session.commit()
    session.refresh(new_game)
    
    # Auto-enrich metadata
    try:
        from app.services.metadata import MetadataService  # already imported at top
        service = MetadataService(session)
        await service.enrich_game(new_game)
    except Exception as e:
        logger.info(f"Auto-enrich failed for {new_game.title}: {e}")
        
    return new_game

@router.get("/games/{game_id}", response_model=GameRead)
async def get_game_admin(
    game_id: int,
    session: Session = Depends(get_session),
    admin: User = Depends(require_admin)
):
    """Get a game by ID (admin only)."""
    game = session.get(Game, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    return game

@router.put("/games/{game_id}", response_model=GameRead)
async def update_game(
    game_id: int,
    game_data: AdminGameUpdate,
    session: Session = Depends(get_session),
    admin: User = Depends(require_admin)
):
    """Update a game's metadata (admin only)."""
    game = session.get(Game, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    update_data = game_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(game, key, value)
    
    from datetime import datetime, timezone
    game.updated_at = datetime.now(timezone.utc)
    
    session.add(game)
    session.commit()
    session.refresh(game)
    return game

@router.delete("/games/{game_id}")
async def delete_game(
    game_id: int,
    session: Session = Depends(get_session),
    admin: User = Depends(require_admin)
):
    """Delete a game (admin only)."""
    game = session.get(Game, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    title = game.title
    session.delete(game)
    session.commit()
    return {"status": "success", "message": f"Game '{title}' deleted"}

@router.post("/games/{game_id}/rescan-metadata")
async def rescan_game_metadata(
    game_id: int,
    session: Session = Depends(get_session),
    admin: User = Depends(require_admin)
):
    """
    Full Metadata Rescan/Enrichment (admin only).
    Fetches data from IGDB -> Steam -> Merges -> Downloads Assets.
    Overwrites existing fields if new data is found.
    """
    game = session.get(Game, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    from app.services.metadata import MetadataService
    service = MetadataService(session)
    
    try:
        updates = await service.enrich_game(game)
        return {"status": "success", "message": f"Rescanned metadata for {game.title}", "updates": updates}
    except Exception as e:
        return {"status": "error", "message": f"Rescan failed: {str(e)}"}

@router.post("/games/rescan-all-metadata")
async def rescan_all_metadata(
    background_tasks: BackgroundTasks,
    fast_mode: bool = False,
    force_update: bool = False,
    session: Session = Depends(get_session),
    admin: User = Depends(require_admin)
):
    """
    Rescan metadata for ALL games in catalog.
    Runs in background to avoid timeouts.
    fast_mode=True: Skips Steam Store API (faster, uses IGDB only).
    force_update=True: Update games even if they already have IGDB data.
    """
    background_tasks.add_task(background_rescan_all_task, fast_mode, force_update)
    
    mode_str = "Fast Mode (IGDB Only)" if fast_mode else "Full Mode (Steam + IGDB)"
    if not force_update:
        mode_str += " [Skipping Existing]"
        
    return {
        "status": "queued", 
        "message": f"Full catalog rescan started in background ({mode_str}). Check logs for progress."
    }

async def background_rescan_all_task(fast_mode: bool = False, force_update: bool = False):
    """
    Background task to enrich all games sequentially.
    force_update: If False, skips games that already have an IGDB ID.
    """
    logger.info(f"Background Rescan: Starting... (Fast Mode: {fast_mode}, Force: {force_update})")
    import asyncio
    from app.core.db import engine
    from app.services.metadata import MetadataService
    
    delay = 0.25 if fast_mode else 2.0
    
    with Session(engine) as session:
        games = session.exec(select(Game)).all()
        service = MetadataService(session)
        
        success_count = 0
        skipped_count = 0
        
        for i, game in enumerate(games):
            try:
                # Optimized Skip Logic
                if not force_update and game.igdb_id:
                    # If we aren't forcing an update, and we already have IGDB data, skip it.
                    # This dramatically speeds up "filling in the blanks" rescans.
                    skipped_count += 1
                    continue

                logger.info(f"Background Rescan [{i+1}/{len(games)}]: Enriching {game.title}...")
                await service.enrich_game(game, skip_steam=fast_mode)
                success_count += 1
                
                # Rate limit protection
                await asyncio.sleep(delay)
            except Exception as e:
                logger.info(f"Background Rescan Error [{game.title}]: {e}")
                
        logger.info(f"Background Rescan: Complete. Updated {success_count} games. Skipped {skipped_count} (already existing).")

@router.delete("/games/bulk")
async def bulk_delete_games(
    game_ids: List[int],
    session: Session = Depends(get_session),
    admin: User = Depends(require_admin)
):
    """Delete multiple games at once (admin only)."""
    deleted_count = 0
    for game_id in game_ids:
        game = session.get(Game, game_id)
        if game:
            session.delete(game)
            deleted_count += 1
    
    session.commit()
    return {"status": "success", "message": f"Deleted {deleted_count} games"}

# ============================================================
# Game Repository Scanning (Admin Only)
# ============================================================

@router.post("/scan-repository")
async def scan_repository(
    session: Session = Depends(get_session),
    admin: User = Depends(require_admin)
):
    """
    Scans the configured GAMES_REPO_PATH for folders (admin only).
    Each folder is treated as a Game.
    """
    repo_path = settings.GAMES_REPO_PATH
    if not os.path.exists(repo_path):
        try:
            os.makedirs(repo_path)
        except OSError:
            return {"status": "error", "message": f"Repo path {repo_path} does not exist and could not be created."}
            
    added_count = 0
    skipped_count = 0
    errors = []
    scanned_items = []
    
    items = os.listdir(repo_path)
    logger.info(f"Repo Scan: Found {len(items)} items in {repo_path}: {items}")

    for item in items:
        item_path = os.path.join(repo_path, item)
        if os.path.isdir(item_path):
            folder_name = item
            scanned_items.append(folder_name)
            
            # Check DB
            existing = session.exec(select(Game).where(Game.title == folder_name)).first()
            if existing:
                logger.info(f"Repo Scan: '{folder_name}' already in DB. Skipping.")
                skipped_count += 1
                continue
                
            # New Discovery
            logger.info(f"Repo Scan: Discovered '{folder_name}'")
            
            new_game = Game(title=folder_name, source="manual")
            session.add(new_game)
                
            try:
                session.commit()
                session.refresh(new_game)
                
                # Enrich with MetadataService
                from app.services.metadata import MetadataService
                service = MetadataService(session)
                await service.enrich_game(new_game)
                
                added_count += 1
            except Exception as e:
                logger.info(f"Repo Scan Error [{folder_name}]: {e}")
                errors.append(f"Failed to save {folder_name}: {e}")
                
    return {
        "status": "success", 
        "added": added_count,
        "skipped": skipped_count, 
        "scanned": scanned_items,
        "errors": errors, 
        "message": f"Scanned {repo_path}. Found {len(scanned_items)} folders. Added {added_count}. Skipped {skipped_count}."
    }

@router.delete("/clear-catalog")
async def clear_catalog(
    session: Session = Depends(get_session),
    admin: User = Depends(require_admin)
):
    """
    DANGER: Deletes ALL games from the database (admin only).
    Does NOT delete files on disk, only the DB entries.
    """
    statement = select(Game)
    games = session.exec(statement).all()
    count = len(games)
    
    for game in games:
        session.delete(game)
        
    session.commit()
    return {"status": "success", "message": f"Deleted {count} games from catalog."}

# ============================================================
# Steam Integration (Admin Only)
# ============================================================

from app.services.steam_store import get_steam_store_service
from app.models.game import GameRead

@router.post("/games/{game_id}/enrich-steam", response_model=GameRead)
async def enrich_game_from_steam(
    game_id: int,
    session: Session = Depends(get_session),
    admin: User = Depends(require_admin)
):
    """
    Fetch and update game metadata from Steam Store API.
    Requires the game to have a steam_app_id set.
    """
    game = session.get(Game, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    if not game.steam_app_id:
        raise HTTPException(status_code=400, detail="Game has no Steam App ID set")
    
    steam_service = get_steam_store_service()
    steam_data = await steam_service.enrich_game(game.steam_app_id)
    
    if not steam_data:
        raise HTTPException(status_code=404, detail=f"No Steam data found for app ID {game.steam_app_id}")
    
    # Update game with Steam data (don't overwrite title)
    steam_data.pop("title", None)  # Keep our title
    
    for key, value in steam_data.items():
        if value is not None and hasattr(game, key):
            setattr(game, key, value)
    
    from datetime import datetime, timezone
    game.updated_at = datetime.now(timezone.utc)
    
    session.add(game)
    session.commit()
    session.refresh(game)
    
    return game

@router.post("/games/enrich-all-steam")
async def enrich_all_games_from_steam(
    session: Session = Depends(get_session),
    admin: User = Depends(require_admin)
):
    """
    Enrich all games that have a Steam App ID with Steam Store data.
    This is rate-limited to avoid hitting Steam API limits.
    """
    games = session.exec(
        select(Game).where(Game.steam_app_id.isnot(None))
    ).all()
    
    if not games:
        return {"status": "warning", "message": "No games with Steam App IDs found"}
    
    steam_service = get_steam_store_service()
    enriched_count = 0
    errors = []
    
    for game in games:
        try:
            steam_data = await steam_service.enrich_game(game.steam_app_id)
            if steam_data:
                steam_data.pop("title", None)
                for key, value in steam_data.items():
                    if value is not None and hasattr(game, key):
                        setattr(game, key, value)
                session.add(game)
                enriched_count += 1
            else:
                errors.append(f"{game.title}: No Steam data found")
        except Exception as e:
            errors.append(f"{game.title}: {str(e)}")
    
    session.commit()
    
    return {
        "status": "success",
        "enriched_count": enriched_count,
        "total_games": len(games),
        "errors": errors
    }

@router.post("/steam/search")
async def search_steam(
    query: str,
    admin: User = Depends(require_admin)
):
    """Search for games on Steam store (for matching purposes)."""
    steam_service = get_steam_store_service()
    results = await steam_service.search_games(query)
    return {"results": results}


class SteamLoginRequest(BaseModel):
    steam_guard_code: Optional[str] = None

@router.post("/steam/login")
async def test_steam_login(
    request: SteamLoginRequest,
    session: Session = Depends(get_session),
    admin: User = Depends(require_admin)
):
    """
    Test SteamCMD Login.
    Useful for verifying credentials and handling Steam Guard / 2FA.
    """
    # Get configuration
    username = settings.STEAM_USERNAME
    password = settings.STEAM_PASSWORD
    steamcmd_path = settings.STEAMCMD_PATH
    
    # Fall back to DB config
    if not username:
        username_config = session.get(SystemConfig, "steam_username")
        username = username_config.value if username_config else None
    
    if not password:
        password_config = session.get(SystemConfig, "steam_password")
        password = password_config.value if password_config else None
    
    if steamcmd_path == "./steamcmd":
        path_config = session.get(SystemConfig, "steamcmd_path")
        if path_config and path_config.value:
            steamcmd_path = path_config.value
            
    if not username or not password:
        raise HTTPException(status_code=400, detail="Steam credentials missing")
        
    try:
        # Run Login Only (empty commands list)
        stdout, stderr, code = await _license_service.run_steamcmd(
            steamcmd_path=steamcmd_path,
            username=username,
            password=password,
            min_commands=[],
            auth_code=request.steam_guard_code
        )
        
        return {
            "status": "success" if code == 0 else "error",
            "exit_code": code,
            "stdout": stdout,
            "stderr": stderr,
            "message": "Login Successful" if code == 0 else "Login Failed"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "exit_code": -1
        }

# ============================================================
# SteamCMD Management (Admin Only)
# ============================================================

import httpx
import zipfile
import tarfile
import io
import platform

STEAMCMD_WINDOWS_URL = "https://steamcdn-a.akamaihd.net/client/installer/steamcmd.zip"
STEAMCMD_LINUX_URL = "https://steamcdn-a.akamaihd.net/client/installer/steamcmd_linux.tar.gz"

@router.post("/steamcmd/download")
async def download_steamcmd(
    session: Session = Depends(get_session),
    admin: User = Depends(require_admin)
):
    """
    Download and install SteamCMD to the configured path.
    Detects OS and downloads appropriate version.
    """
    # Get configured path
    path_config = session.get(SystemConfig, "steamcmd_path")
    steamcmd_path = path_config.value if path_config else "./steamcmd"
    
    # Determine URL based on OS
    is_windows = platform.system() == "Windows"
    url = STEAMCMD_WINDOWS_URL if is_windows else STEAMCMD_LINUX_URL
    
    try:
        # Create directory
        os.makedirs(steamcmd_path, exist_ok=True)
        
        # Download
        async with httpx.AsyncClient() as client:
            response = await client.get(url, follow_redirects=True)
            response.raise_for_status()
        
        # Extract
        if is_windows:
            # ZIP file
            with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
                zf.extractall(steamcmd_path)
        else:
            # TAR.GZ file
            with tarfile.open(fileobj=io.BytesIO(response.content), mode="r:gz") as tf:
                tf.extractall(steamcmd_path)
        
        # Update config
        installed_config = session.get(SystemConfig, "steamcmd_installed")
        if installed_config:
            installed_config.value = "true"
            session.add(installed_config)
            session.commit()
        
        return {
            "status": "success",
            "message": f"SteamCMD downloaded to {steamcmd_path}",
            "path": steamcmd_path
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to download SteamCMD: {str(e)}"
        }

@router.get("/steamcmd/status")
async def get_steamcmd_status(
    session: Session = Depends(get_session),
    admin: User = Depends(require_admin)
):
    """Check if SteamCMD is installed and ready."""
    path_config = session.get(SystemConfig, "steamcmd_path")
    steamcmd_path = path_config.value if path_config else "./steamcmd"
    
    installed_config = session.get(SystemConfig, "steamcmd_installed")
    is_installed = installed_config and installed_config.value.lower() == "true"
    
    # Check if executable exists
    is_windows = platform.system() == "Windows"
    exe_name = "steamcmd.exe" if is_windows else "steamcmd.sh"
    exe_path = os.path.join(steamcmd_path, exe_name)
    exe_exists = os.path.exists(exe_path)
    
    return {
        "path": steamcmd_path,
        "is_installed": is_installed,
        "executable_exists": exe_exists,
        "executable_path": exe_path if exe_exists else None
    }

# ============================================================
# Steam License Import Endpoints
# ============================================================

from app.services.steam_licenses import SteamLicenseService, search_steam_store

# Global service instance for status tracking
_license_service = SteamLicenseService()


class ImportLicensesRequest(BaseModel):
    batch_size: int = 10
    delay_seconds: float = 2.0
    steam_guard_code: Optional[str] = None


@router.post("/steam/import-licenses")
async def import_steam_licenses(
    request: Optional[ImportLicensesRequest] = None,
    session: Session = Depends(get_session),
    admin: User = Depends(require_admin)
):
    """
    Import all owned paid games from Steam account.
    Uses SteamCMD licenses_print to get owned games,
    fetches metadata, and filters out free games.
    
    If Steam Guard code is required (exit code 5),
    provide 'steam_guard_code' in the request body.
    """
    # Check env vars first, then fall back to DB config
    username = settings.STEAM_USERNAME
    password = settings.STEAM_PASSWORD
    steamcmd_path = settings.STEAMCMD_PATH
    
    # Fall back to DB config if env vars not set
    if not username:
        username_config = session.get(SystemConfig, "steam_username")
        username = username_config.value if username_config else None
    
    if not password:
        password_config = session.get(SystemConfig, "steam_password")
        password = password_config.value if password_config else None
    
    if steamcmd_path == "./steamcmd":
        path_config = session.get(SystemConfig, "steamcmd_path")
        if path_config and path_config.value:
            steamcmd_path = path_config.value
    
    if not username:
        raise HTTPException(
            status_code=400,
            detail="Steam username not configured. Set STEAM_USERNAME env var or configure in Steam tab."
        )
    
    if not password:
        raise HTTPException(
            status_code=400,
            detail="Steam password not configured. Set STEAM_PASSWORD env var or configure in Steam tab."
        )
    
    # Check if SteamCMD executable exists
    is_windows = platform.system() == "Windows"
    exe_name = "steamcmd.exe" if is_windows else "steamcmd.sh"
    exe_path = os.path.join(steamcmd_path, exe_name)
    
    if not os.path.exists(exe_path):
        raise HTTPException(
            status_code=400,
            detail=f"SteamCMD not found at {exe_path}. Download it first from the Steam tab."
        )
    
    # Import settings
    batch_size = request.batch_size if request else 10
    delay_seconds = request.delay_seconds if request else 2.0
    auth_code = request.steam_guard_code if request else None
    
    try:
        # Pass directory path, not executable - the service builds the full path
        result = await _license_service.import_all_licenses(
            session=session,
            steamcmd_path=steamcmd_path,  # Directory, not exe
            username=username,
            password=password,
            batch_size=batch_size,
            delay_seconds=delay_seconds,
            auth_code=auth_code
        )
        
        return {
            "status": "success",
            "total_found": result.total_found,
            "imported": result.imported,
            "skipped_existing": result.skipped_existing,
            "skipped_free": result.skipped_free,
            "skipped_invalid": result.skipped_invalid,
            "errors": result.errors[:10],  # Limit errors shown
            "games_added": result.games_added[:20],  # Limit games shown
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Import failed: {str(e)}"
        )


@router.get("/steam/import-licenses/status")
async def get_import_status(
    admin: User = Depends(require_admin)
):
    """Get the status of an ongoing license import."""
    return _license_service.get_import_status()


class ImportByAppIdRequest(BaseModel):
    steam_app_id: int


@router.post("/games/import-by-appid")
async def import_game_by_appid(
    request: ImportByAppIdRequest,
    session: Session = Depends(get_session),
    admin: User = Depends(require_admin)
):
    """
    Import a single game by Steam App ID.
    Fetches full metadata and adds to the store.
    """
    # Check if already exists
    existing = session.exec(
        select(Game).where(Game.steam_app_id == request.steam_app_id)
    ).first()
    
    if existing:
        return {
            "status": "skipped",
            "message": f"Game already exists: {existing.title}",
            "game_id": existing.id
        }
    
    # Import the game
    status, error = await _license_service.import_single_game(
        session=session,
        app_id=request.steam_app_id
    )
    
    if status == "imported":
        game = session.exec(
            select(Game).where(Game.steam_app_id == request.steam_app_id)
        ).first()
        
        # Auto-enrich metadata (IGDB + Downloads)
        if game:
            try:
                from app.services.metadata import MetadataService
                service = MetadataService(session)
                await service.enrich_game(game)
            except Exception as e:
                logger.info(f"Auto-enrich failed for steam app {request.steam_app_id}: {e}")

        return {
            "status": "success",
            "message": f"Imported: {game.title}" if game else "Game imported",
            "game_id": game.id if game else None
        }
    elif status == "skipped_free":
        return {
            "status": "skipped",
            "message": "This is a free game"
        }
    elif status == "skipped_invalid":
        return {
            "status": "skipped",
            "message": error or "Not a valid game"
        }
    else:
        raise HTTPException(
            status_code=500,
            detail=error or "Failed to import game"
        )


# ============================================================
# Review Moderation (Admin Only)
# ============================================================
from app.models.review import Review

class ReviewModItem(BaseModel):
    id: int
    user_id: int
    game_id: int
    content: str
    rating: int
    is_hidden: bool
    created_at: Optional[str]
    username: str
    game_title: str

@router.get("/reviews", response_model=List[ReviewModItem])
async def list_all_reviews(
    include_hidden: bool = True,
    limit: int = 100,
    offset: int = 0,
    session: Session = Depends(get_session),
    admin: User = Depends(require_admin)
):
    """List all reviews for moderation (admin only)."""
    statement = (
        select(Review, User, Game)
        .join(User, User.id == Review.user_id)
        .join(Game, Game.id == Review.game_id)
    )
    
    if not include_hidden:
        statement = statement.where(Review.is_hidden == False)
    
    statement = statement.order_by(Review.created_at.desc()).offset(offset).limit(limit)
    results = session.exec(statement).all()
    
    return [
        ReviewModItem(
            id=review.id,
            user_id=review.user_id,
            game_id=review.game_id,
            content=review.content[:200] + "..." if len(review.content) > 200 else review.content,
            rating=review.rating,
            is_hidden=review.is_hidden,
            created_at=review.created_at.isoformat() if review.created_at else None,
            username=user.username,
            game_title=game.title
        )
        for review, user, game in results
    ]



@router.delete("/reviews/{review_id}")
async def delete_review_admin(
    review_id: int,
    session: Session = Depends(get_session),
    admin: User = Depends(require_admin)
):
    """Delete any review (admin only)."""
    review = session.get(Review, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    
    session.delete(review)
    session.commit()
    
    return {"message": "Review deleted successfully"}


