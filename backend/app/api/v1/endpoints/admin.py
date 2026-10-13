import logging
import os
import asyncio
import json
import platform
from typing import List, Optional, Any, Dict
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from starlette.responses import StreamingResponse
from sqlmodel import Session, select, or_, func
from pydantic import BaseModel
from app.core.db import get_session
from app.core.config import settings
from app.core.auth import require_admin
from app.core.security import hash_password
from app.models.game import Game
from app.models.user import User, UserRead, UserCreate
from app.models.config import SystemConfig
from app.models.library import ServerGameCache, UserLibrary
from app.services.igdb import IGDBClient
from app.services.metadata import MetadataService
from app.services.task_manager import task_manager
from app.services.steam_licenses import SteamLicenseService, search_steam_store
from app.services.depot_downloader import depot_downloader, run_depot_download_task
from app.services.cache_cleaner import cache_cleaner, _safe_purge_disk_repository

logger = logging.getLogger(__name__)

# Global license service instance for status tracking and token inspection
_license_service = SteamLicenseService()

router = APIRouter()

# ============================================================
# Task Management & Real-Time Console Streaming Endpoints
# ============================================================

@router.get("/tasks")
async def list_admin_tasks(
    admin: User = Depends(require_admin)
):
    """List recent background tasks."""
    return task_manager.get_all_tasks(limit=30)

@router.get("/tasks/active")
async def get_active_tasks(
    admin: User = Depends(require_admin)
):
    """List currently active running tasks."""
    return task_manager.get_active_tasks()

@router.get("/tasks/{task_id}")
async def get_task_details(
    task_id: str,
    admin: User = Depends(require_admin)
):
    """Get full details and logs for a task."""
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    data = task.to_dict()
    data["logs"] = task.logs
    return data

@router.post("/tasks/{task_id}/cancel")
async def cancel_admin_task(
    task_id: str,
    admin: User = Depends(require_admin)
):
    """Cancel a running background task."""
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    task.cancel()
    return {"status": "success", "message": f"Task {task_id} cancellation requested"}

@router.get("/tasks/{task_id}/stream")
async def stream_task_events(
    task_id: str,
    token: Optional[str] = None
):
    """
    Server-Sent Events (SSE) stream for live task logs and progress.
    Supports query parameter 'token' for browser EventSource.
    """
    user = None
    if token:
        from app.core.security import decode_token
        payload = decode_token(token)
        if payload and "sub" in payload:
            sub_val = payload["sub"]
            with Session(engine) as session:
                try:
                    user = session.get(User, int(sub_val))
                except (ValueError, TypeError):
                    user = session.exec(select(User).where(User.username == sub_val)).first()

    if not user or not user.is_admin:
        raise HTTPException(status_code=401, detail="Admin authorization required")

    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    async def event_generator():
        q = asyncio.Queue(maxsize=100)
        task._subscribers.append(q)
        try:
            init_payload = {
                "id": task.id,
                "type": task.type,
                "name": task.name,
                "status": task.status,
                "progress": task.progress,
                "logs": task.logs
            }
            yield f"event: init\ndata: {json.dumps(init_payload)}\n\n"

            if task.status != "running":
                yield f"event: status\ndata: {json.dumps({'status': task.status, 'result': task.result, 'error': task.error})}\n\n"
                return

            while True:
                try:
                    event = await asyncio.wait_for(q.get(), timeout=15.0)
                    yield f"event: {event['type']}\ndata: {json.dumps(event['data'])}\n\n"
                    if event["type"] == "status" and event["data"].get("status") in ("completed", "failed", "cancelled"):
                        break
                except asyncio.TimeoutError:
                    yield ": ping\n\n"
                    if task.status != "running":
                        break
        finally:
            if q in task._subscribers:
                task._subscribers.remove(q)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@router.get("/system/status")
async def get_system_status(
    session: Session = Depends(get_session),
    admin: User = Depends(require_admin)
):
    """System health check, diagnostics, and counts for admin dashboard."""
    from app.models.review import Review
    from app.models.news import NewsPost
    import shutil

    games_count = len(session.exec(select(Game.id)).all())
    users_count = len(session.exec(select(User.id)).all())
    reviews_count = len(session.exec(select(Review.id)).all())
    news_count = len(session.exec(select(NewsPost.id)).all())

    path_config = session.get(SystemConfig, "steamcmd_path")
    steamcmd_path = path_config.value if path_config else "./steamcmd"
    is_windows = platform.system() == "Windows"
    exe_name = "steamcmd.exe" if is_windows else "steamcmd.sh"
    steamcmd_exe = os.path.join(steamcmd_path, exe_name)
    steamcmd_ready = os.path.exists(steamcmd_exe)

    data_dir = settings.DATA_DIR
    disk_total = 0
    disk_free = 0
    if os.path.exists(data_dir):
        try:
            total, used, free = shutil.disk_usage(data_dir)
            disk_total = round(total / (1024**3), 1)
            disk_free = round(free / (1024**3), 1)
        except Exception:
            pass

    return {
        "status": "healthy",
        "counts": {
            "games": games_count,
            "users": users_count,
            "reviews": reviews_count,
            "news": news_count
        },
        "steamcmd": {
            "ready": steamcmd_ready,
            "path": steamcmd_exe
        },
        "storage": {
            "data_dir": data_dir,
            "repo_dir": settings.GAMES_REPO_PATH,
            "total_gb": disk_total,
            "free_gb": disk_free,
            "used_gb": round(max(0.0, disk_total - disk_free), 1),
            "percent_used": round(((disk_total - disk_free) / disk_total * 100), 1) if disk_total > 0 else 0
        },
        "disk": {
            "data_dir": data_dir,
            "total_gb": disk_total,
            "free_gb": disk_free,
            "used_gb": round(max(0.0, disk_total - disk_free), 1),
            "percent_used": round(((disk_total - disk_free) / disk_total * 100), 1) if disk_total > 0 else 0
        },
        "active_tasks": len(task_manager.get_active_tasks())
    }

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
    """Update or create a system configuration value (admin only)."""
    cfg = session.get(SystemConfig, key)
    is_secret = key in ("steam_password", "steam_api_key", "secret_key", "igdb_client_secret")
    if not cfg:
        cfg = SystemConfig(
            key=key,
            value=value,
            value_type="string",
            description=f"Setting for {key}",
            is_secret=is_secret,
            updated_by=admin.id
        )
        session.add(cfg)
    else:
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
    """Delete a game (admin only). Safely cleans up dependent reviews and playtime."""
    game = session.get(Game, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    from app.models.review import Review
    from app.models.social import UserPlaytime

    reviews = session.exec(select(Review).where(Review.game_id == game_id)).all()
    for r in reviews:
        session.delete(r)
    playtimes = session.exec(select(UserPlaytime).where(UserPlaytime.game_id == game_id)).all()
    for p in playtimes:
        session.delete(p)

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
    Runs asynchronously with real-time SSE progress & log streaming.
    """
    active = [t for t in task_manager.get_active_tasks() if t["type"] == "enrich_all"]
    if active:
        return {"status": "already_running", "task_id": active[0]["id"], "message": "Metadata enrichment is already in progress"}

    mode_label = "Fast Mode (IGDB Only)" if fast_mode else "Full Mode (Steam + IGDB)"
    task = task_manager.create_task("enrich_all", f"Enrich Metadata ({mode_label})")
    background_tasks.add_task(background_rescan_all_task, task.id, fast_mode, force_update)
    
    return {
        "status": "queued",
        "task_id": task.id,
        "message": f"Catalog metadata enrichment started ({mode_label}). Stream logs via console."
    }

async def background_rescan_all_task(task_id: str, fast_mode: bool = False, force_update: bool = False):
    """
    Background task to enrich all games sequentially with live streaming logs.
    """
    from app.core.db import engine
    from app.services.metadata import MetadataService
    task = task_manager.get_task(task_id)
    if not task:
        return

    mode_str = "Fast Mode (IGDB Only)" if fast_mode else "Full Mode (Steam + IGDB)"
    task.log(f"Starting catalog-wide metadata enrichment: {mode_str}")
    delay = 0.25 if fast_mode else 1.5

    with Session(engine) as session:
        games = session.exec(select(Game)).all()
        total_games = len(games)
        if not games:
            task.complete({"updated": 0, "skipped": 0, "total": 0}, "No games in catalog to enrich.")
            return

        task.log(f"Found {total_games} games in catalog to process")
        service = MetadataService(session)
        updated = 0
        skipped = 0
        errors = 0

        for i, game in enumerate(games):
            if task.is_cancelled:
                task.log("Enrichment cancelled by operator", level="warning")
                break

            task.set_progress(i, total_games, f"Enriching {game.title} ({i+1}/{total_games})")

            if not force_update and game.igdb_id:
                task.log(f"[{i+1}/{total_games}] Skipping '{game.title}' (already has IGDB data)")
                skipped += 1
                continue

            task.log(f"[{i+1}/{total_games}] Enriching metadata for '{game.title}'...")
            try:
                updates = await service.enrich_game(game, skip_steam=fast_mode)
                updated_keys = list(updates.keys())
                if updated_keys:
                    task.log(f"[{i+1}/{total_games}] Updated '{game.title}': {len(updated_keys)} fields ({', '.join(updated_keys)})", level="success")
                    updated += 1
                else:
                    task.log(f"[{i+1}/{total_games}] No new metadata found for '{game.title}'", level="warning")
                    skipped += 1
                await asyncio.sleep(delay)
            except Exception as e:
                task.log(f"[{i+1}/{total_games}] Failed to enrich '{game.title}': {e}", level="error")
                errors += 1

    summary = f"Enrichment complete. Updated: {updated}, Skipped: {skipped}, Errors: {errors}."
    task.complete({"updated": updated, "skipped": skipped, "errors": errors, "total": total_games}, summary)

@router.delete("/games/bulk")
async def bulk_delete_games(
    game_ids: List[int],
    session: Session = Depends(get_session),
    admin: User = Depends(require_admin)
):
    """Delete multiple games at once (admin only)."""
    from app.models.review import Review
    from app.models.social import UserPlaytime

    deleted_count = 0
    for game_id in game_ids:
        game = session.get(Game, game_id)
        if game:
            reviews = session.exec(select(Review).where(Review.game_id == game_id)).all()
            for r in reviews:
                session.delete(r)
            playtimes = session.exec(select(UserPlaytime).where(UserPlaytime.game_id == game_id)).all()
            for p in playtimes:
                session.delete(p)
            session.delete(game)
            deleted_count += 1
    
    session.commit()
    return {"status": "success", "message": f"Deleted {deleted_count} games"}

# ============================================================
# Game Repository Scanning (Admin Only)
# ============================================================

@router.post("/scan-repository")
async def scan_repository(
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
    admin: User = Depends(require_admin)
):
    """
    Scans the configured GAMES_REPO_PATH asynchronously.
    Updates progress and logs lines in real-time via the Task Manager and SSE.
    """
    active = [t for t in task_manager.get_active_tasks() if t["type"] == "scan_repo"]
    if active:
        return {"status": "already_running", "task_id": active[0]["id"], "message": "A repository scan is already running"}

    task = task_manager.create_task("scan_repo", "Repository Scan")
    background_tasks.add_task(run_scan_repo_task, task.id)
    return {
        "status": "queued",
        "task_id": task.id,
        "message": "Repository scan started in background. Stream logs via console."
    }

async def run_scan_repo_task(task_id: str):
    from app.core.db import engine
    from app.services.metadata import MetadataService
    task = task_manager.get_task(task_id)
    if not task:
        return

    task.log("Starting repository scan...")
    repo_path = settings.GAMES_REPO_PATH
    task.log(f"Scanning directory: {repo_path}")

    if not os.path.exists(repo_path):
        try:
            os.makedirs(repo_path, exist_ok=True)
            task.log(f"Created repository directory at: {repo_path}")
        except Exception as e:
            task.fail(f"Could not access or create repo path {repo_path}: {e}")
            return

    try:
        raw_items = os.listdir(repo_path)
    except Exception as e:
        task.fail(f"Failed to read directory {repo_path}: {e}")
        return

    items = [item for item in raw_items if os.path.isdir(os.path.join(repo_path, item))]
    task.log(f"Found {len(items)} folder(s) in {repo_path}")

    if not items:
        task.complete({"added": 0, "skipped": 0, "total": 0}, "No game directories found in repository.")
        return

    added = 0
    skipped = 0
    errors = 0

    with Session(engine) as session:
        service = MetadataService(session)
        for i, folder_name in enumerate(items):
            if task.is_cancelled:
                task.log("Scan cancelled by operator", level="warning")
                break

            task.set_progress(i, len(items), f"Processing {folder_name} ({i+1}/{len(items)})")
            
            existing = session.exec(select(Game).where(Game.title == folder_name)).first()
            if existing:
                task.log(f"[{i+1}/{len(items)}] '{folder_name}' already exists in catalog. Skipping.")
                skipped += 1
                continue

            task.log(f"[{i+1}/{len(items)}] Discovered new game: '{folder_name}'")
            new_game = Game(title=folder_name, source="manual")
            session.add(new_game)
            try:
                session.commit()
                session.refresh(new_game)
                task.log(f"[{i+1}/{len(items)}] Fetching metadata for '{folder_name}'...")
                await service.enrich_game(new_game)
                task.log(f"[{i+1}/{len(items)}] Added and enriched: '{folder_name}'", level="success")
                added += 1
            except Exception as e:
                task.log(f"[{i+1}/{len(items)}] Error saving {folder_name}: {e}", level="error")
                errors += 1

    summary = f"Repository scan finished. Added: {added}, Skipped: {skipped}, Errors: {errors}."
    task.complete({"added": added, "skipped": skipped, "errors": errors, "total": len(items)}, summary)

@router.delete("/clear-catalog")
async def clear_catalog(
    session: Session = Depends(get_session),
    admin: User = Depends(require_admin)
):
    """
    DANGER: Deletes ALL games from the database (admin only).
    Safely cleans up reviews and playtimes first. Does NOT delete files on disk.
    """
    from app.models.review import Review
    from app.models.social import UserPlaytime

    reviews = session.exec(select(Review)).all()
    for r in reviews:
        session.delete(r)
        
    playtimes = session.exec(select(UserPlaytime)).all()
    for p in playtimes:
        session.delete(p)

    statement = select(Game)
    games = session.exec(statement).all()
    count = len(games)
    
    for game in games:
        session.delete(game)
        
    session.commit()
    return {"status": "success", "message": f"Deleted {count} games, {len(reviews)} reviews, and {len(playtimes)} playtime records."}

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
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
    admin: User = Depends(require_admin)
):
    """
    Test SteamCMD Login asynchronously with real-time log streaming.
    """
    username = settings.STEAM_USERNAME
    password = settings.STEAM_PASSWORD
    steamcmd_path = settings.STEAMCMD_PATH
    
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
            
    has_token = _license_service.has_cached_token(username, steamcmd_path) if username else False

    if not username or (not password and not has_token):
        raise HTTPException(status_code=400, detail="Steam credentials missing. Please set username and password first.")
        
    task = task_manager.create_task("steam_login", "Steam Login Test")
    background_tasks.add_task(run_steam_login_task, task.id, steamcmd_path, username, password, request.steam_guard_code)
    return {
        "status": "queued",
        "task_id": task.id,
        "message": "Steam login test started. Stream logs via console."
    }

async def run_steam_login_task(task_id: str, steamcmd_path: str, username: str, password: Optional[str], auth_code: Optional[str]):
    task = task_manager.get_task(task_id)
    if not task:
        return

    is_windows = platform.system() == "Windows"
    exe_name = "steamcmd.exe" if is_windows else "steamcmd.sh"
    executable = os.path.join(steamcmd_path, exe_name)

    if not os.path.exists(executable):
        task.fail(f"SteamCMD not found at {executable}. Download it first from the Steam tab.")
        return

    task.log(f"Starting SteamCMD at {executable}...")

    has_token = _license_service.has_cached_token(username, steamcmd_path)
    if auth_code:
        task.log(f"Logging in as user '{username}' with Steam Guard code (saving machine token)...")
        login_args = ["+login", username, password or "", auth_code, "1"]
    elif has_token:
        task.log(f"Logging in as user '{username}' using saved machine token (password-free)...")
        login_args = ["+login", username]
    else:
        task.log(f"Logging in as user: {username}")
        login_args = ["+login", username, password, "1"] if password else ["+login", username]

    cmd = [executable, *login_args, "+quit"]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        async def read_stream(stream, is_err=False):
            while True:
                line = await stream.readline()
                if not line:
                    break
                text = line.decode("utf-8", errors="replace").strip()
                if text:
                    masked = text.replace(password, "******") if password else text
                    level = "error" if is_err else "info"
                    if "Logged in OK" in masked or "Success" in masked:
                        level = "success"
                    elif "Steam Guard" in masked or "FAILED" in masked:
                        level = "warning"
                    task.log(masked, level=level)

        await asyncio.gather(
            read_stream(proc.stdout, is_err=False),
            read_stream(proc.stderr, is_err=True)
        )
        rc = await proc.wait()

        if rc == 0:
            task.complete({"exit_code": 0}, "SteamCMD authenticated successfully!")
        elif rc == 5:
            task.complete({"exit_code": 5}, "Steam Guard code required. Enter code above and re-test.")
        else:
            task.fail(f"SteamCMD exited with code {rc}.")
    except Exception as e:
        task.fail(f"SteamCMD execution failed: {e}")

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
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
    admin: User = Depends(require_admin)
):
    """
    Download and install SteamCMD asynchronously with live log streaming.
    """
    active = [t for t in task_manager.get_active_tasks() if t["type"] == "steamcmd_download"]
    if active:
        return {"status": "already_running", "task_id": active[0]["id"], "message": "SteamCMD download is already running"}

    path_config = session.get(SystemConfig, "steamcmd_path")
    steamcmd_path = path_config.value if path_config else "./steamcmd"

    task = task_manager.create_task("steamcmd_download", "Download SteamCMD")
    background_tasks.add_task(run_steamcmd_download_task, task.id, steamcmd_path)
    return {
        "status": "queued",
        "task_id": task.id,
        "message": "SteamCMD download started in background. Stream logs via console."
    }

async def run_steamcmd_download_task(task_id: str, steamcmd_path: str):
    from app.core.db import engine
    task = task_manager.get_task(task_id)
    if not task:
        return

    is_windows = platform.system() == "Windows"
    url = STEAMCMD_WINDOWS_URL if is_windows else STEAMCMD_LINUX_URL
    os_name = "Windows" if is_windows else "Linux"

    task.log(f"Preparing SteamCMD setup for {os_name}...")
    task.log(f"Destination folder: {steamcmd_path}")
    task.log(f"Downloading from {url}...")

    try:
        os.makedirs(steamcmd_path, exist_ok=True)
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.get(url, follow_redirects=True)
            resp.raise_for_status()

        content = resp.content
        mb_size = round(len(content) / (1024 * 1024), 2)
        task.log(f"Downloaded {mb_size} MB archive. Extracting files...", level="info")

        if is_windows:
            with zipfile.ZipFile(io.BytesIO(content)) as zf:
                zf.extractall(steamcmd_path)
        else:
            with tarfile.open(fileobj=io.BytesIO(content), mode="r:gz") as tf:
                tf.extractall(steamcmd_path)

        exe_name = "steamcmd.exe" if is_windows else "steamcmd.sh"
        exe_path = os.path.join(steamcmd_path, exe_name)
        if not is_windows and os.path.exists(exe_path):
            try:
                os.chmod(exe_path, 0o755)
            except Exception:
                pass

        if os.path.exists(exe_path):
            task.log(f"Verified executable: {exe_path}", level="success")
            with Session(engine) as session:
                installed_cfg = session.get(SystemConfig, "steamcmd_installed")
                if not installed_cfg:
                    installed_cfg = SystemConfig(key="steamcmd_installed", value="true", value_type="bool", description="SteamCMD installation status")
                    session.add(installed_cfg)
                else:
                    installed_cfg.value = "true"
                    session.add(installed_cfg)
                session.commit()
            task.complete({"path": exe_path}, f"SteamCMD successfully installed to {steamcmd_path}")
        else:
            task.fail(f"Extraction completed but executable not found at {exe_path}")
    except Exception as e:
        task.fail(f"SteamCMD download/extraction failed: {e}")

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

    username = settings.STEAM_USERNAME or (session.get(SystemConfig, "steam_username").value if session.get(SystemConfig, "steam_username") else None)
    has_token = _license_service.has_cached_token(username, steamcmd_path) if username else False

    return {
        "path": steamcmd_path,
        "is_installed": is_installed,
        "executable_exists": exe_exists,
        "executable_path": exe_path if exe_exists else None,
        "has_cached_token": has_token,
        "username": username
    }

# ============================================================
# Steam License Import Endpoints
# ============================================================


class ImportLicensesRequest(BaseModel):
    batch_size: int = 10
    delay_seconds: float = 2.0
    steam_guard_code: Optional[str] = None


@router.post("/steam/import-licenses")
async def import_steam_licenses(
    background_tasks: BackgroundTasks,
    request: Optional[ImportLicensesRequest] = None,
    session: Session = Depends(get_session),
    admin: User = Depends(require_admin)
):
    """
    Import all owned paid games from Steam account asynchronously.
    Updates progress and streams logs in real-time.
    """
    active = [t for t in task_manager.get_active_tasks() if t["type"] == "import_licenses"]
    if active:
        return {"status": "already_running", "task_id": active[0]["id"], "message": "License import is already running"}

    username = settings.STEAM_USERNAME or (session.get(SystemConfig, "steam_username").value if session.get(SystemConfig, "steam_username") else None)
    password = settings.STEAM_PASSWORD or (session.get(SystemConfig, "steam_password").value if session.get(SystemConfig, "steam_password") else None)
    steamcmd_path = settings.STEAMCMD_PATH
    if steamcmd_path == "./steamcmd":
        cfg = session.get(SystemConfig, "steamcmd_path")
        if cfg and cfg.value:
            steamcmd_path = cfg.value

    has_token = _license_service.has_cached_token(username, steamcmd_path) if username else False

    if not username:
        raise HTTPException(status_code=400, detail="Steam username not configured. Configure in Steam tab.")
    if not password and not has_token:
        raise HTTPException(status_code=400, detail="Steam password not configured. Configure in Steam tab.")

    is_windows = platform.system() == "Windows"
    exe_name = "steamcmd.exe" if is_windows else "steamcmd.sh"
    exe_path = os.path.join(steamcmd_path, exe_name)
    if not os.path.exists(exe_path):
        raise HTTPException(status_code=400, detail=f"SteamCMD not found at {exe_path}. Download it first from the Steam tab.")

    batch_size = request.batch_size if request else 10
    delay_seconds = request.delay_seconds if request else 2.0
    auth_code = request.steam_guard_code if request else None

    task = task_manager.create_task("import_licenses", "Steam License Import")
    background_tasks.add_task(run_import_licenses_task, task.id, steamcmd_path, username, password, batch_size, delay_seconds, auth_code)
    return {
        "status": "queued",
        "task_id": task.id,
        "message": "Steam license import started in background. Stream logs via console."
    }

async def run_import_licenses_task(task_id: str, steamcmd_path: str, username: str, password: Optional[str], batch_size: int, delay_seconds: float, auth_code: Optional[str]):
    from app.core.db import engine
    task = task_manager.get_task(task_id)
    if not task:
        return

    task.log("Starting Steam license import process...")
    task.log(f"Fetching license package list for account '{username}' via SteamCMD...")

    with Session(engine) as session:
        try:
            result = await _license_service.import_all_licenses(
                session=session,
                steamcmd_path=steamcmd_path,
                username=username,
                password=password,
                batch_size=batch_size,
                delay_seconds=delay_seconds,
                auth_code=auth_code,
                task=task
            )
            if result.errors:
                for err in result.errors[:10]:
                    task.log(f"Warning: {err}", level="warning")
            summary = f"Import complete. Imported: {result.imported} new games."
            task.complete({
                "total_found": result.total_found,
                "imported": result.imported,
                "skipped_existing": result.skipped_existing,
                "skipped_free": result.skipped_free,
                "skipped_invalid": result.skipped_invalid,
                "skipped_demo": result.skipped_demo,
                "skipped_online_only": result.skipped_online_only,
                "errors": result.errors[:10],
                "games_added": result.games_added[:20]
            }, summary)
        except Exception as e:
            logger.error(f"License import task failed: {e}", exc_info=True)
            task.fail(f"License import failed: {e}")

@router.get("/steam/import-licenses/status")
async def get_import_status(
    admin: User = Depends(require_admin)
):
    """Get the status of an ongoing license import."""
    active = [t for t in task_manager.get_active_tasks() if t["type"] == "import_licenses"]
    if active:
        return {"running": True, "phase": active[0]["progress"]["message"], "progress": active[0]["progress"]["current"], "total": active[0]["progress"]["total"]}
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


# ============================================================
# Server Storage & Install Administration (R6.1 - R6.4, R6.7)
# ============================================================

class StorageStatusResponse(BaseModel):
    total_bytes: int
    used_bytes: int
    cached_games_count: int
    orphaned_games_count: int
    free_bytes: Optional[int] = None
    utilization_pct: Optional[float] = None
    total_storage: Optional[int] = None
    used_storage: Optional[int] = None
    cached_count: Optional[int] = None
    orphaned_count: Optional[int] = None


class StorageGameRead(BaseModel):
    id: int
    game_id: int
    title: str
    steam_app_id: Optional[int] = None
    user_count: int = 0
    cached_size_bytes: int = 0
    build_id: Optional[str] = None
    latest_build_id: Optional[str] = None
    last_check: Optional[datetime] = None
    is_cached: bool = False
    orphaned_at: Optional[datetime] = None
    purged_at: Optional[datetime] = None
    cached_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class StorageUpdateResponse(BaseModel):
    status: str = "queued"
    message: str
    game_id: int
    task_id: Optional[str] = None


class StoragePurgeResponse(BaseModel):
    status: str = "purged"
    message: str
    game_id: int
    freed_bytes: int = 0
    purged_at: Optional[datetime] = None


@router.get("/storage/status", response_model=StorageStatusResponse)
async def get_storage_status(
    session: Session = Depends(get_session),
    admin: User = Depends(require_admin)
):
    """
    R6.1: Get server storage footprint metrics.
    Returns total storage bytes, used bytes, cached game count, and orphaned game count.
    Guarantees non-negative metrics and safe 0-count calculations.
    """
    import shutil
    repo_path = os.path.abspath(settings.GAMES_REPO_PATH)
    try:
        os.makedirs(repo_path, exist_ok=True)
        total_disk, _, _ = shutil.disk_usage(repo_path)
    except Exception:
        total_disk = 100 * 1024 * 1024 * 1024

    cached_entries = session.exec(
        select(ServerGameCache).where(ServerGameCache.is_cached == True)
    ).all()

    used_bytes = sum(max(0, entry.cached_size_bytes) for entry in cached_entries)
    cached_count = len(cached_entries)
    orphaned_count = sum(1 for entry in cached_entries if entry.orphaned_at is not None)

    free_bytes = max(0, total_disk - used_bytes)
    utilization_pct = round((used_bytes / total_disk) * 100.0, 2) if total_disk > 0 else 0.0

    return StorageStatusResponse(
        total_bytes=max(0, total_disk),
        used_bytes=max(0, used_bytes),
        cached_games_count=max(0, cached_count),
        orphaned_games_count=max(0, orphaned_count),
        total_storage=max(0, total_disk),
        used_storage=max(0, used_bytes),
        cached_count=max(0, cached_count),
        orphaned_count=max(0, orphaned_count),
        free_bytes=free_bytes,
        utilization_pct=utilization_pct,
    )


@router.get("/storage/games", response_model=List[StorageGameRead])
async def list_storage_games(
    session: Session = Depends(get_session),
    admin: User = Depends(require_admin)
):
    """
    R6.2: Get catalog of tracked games with associated user counts,
    cached storage size, build IDs, and cache statuses.
    """
    games = session.exec(select(Game).order_by(Game.title)).all()
    cache_entries = session.exec(select(ServerGameCache)).all()
    cache_map = {entry.game_id: entry for entry in cache_entries}

    user_counts_query = (
        select(UserLibrary.game_id, func.count(func.distinct(UserLibrary.user_id)))
        .group_by(UserLibrary.game_id)
    )
    user_counts_map = dict(session.exec(user_counts_query).all())

    seen_game_ids = set()
    results: List[StorageGameRead] = []

    for game in games:
        seen_game_ids.add(game.id)
        cache = cache_map.get(game.id)
        u_count = user_counts_map.get(game.id, 0)

        results.append(StorageGameRead(
            id=game.id,
            game_id=game.id,
            title=game.title,
            steam_app_id=game.steam_app_id,
            user_count=u_count,
            cached_size_bytes=cache.cached_size_bytes if cache else 0,
            build_id=cache.build_id if cache else None,
            latest_build_id=cache.latest_build_id if cache else None,
            last_check=cache.last_check if cache else None,
            is_cached=cache.is_cached if cache else False,
            orphaned_at=cache.orphaned_at if cache else None,
            purged_at=cache.purged_at if cache else None,
            cached_at=cache.cached_at if cache else None,
            updated_at=cache.updated_at if cache else None,
        ))

    for cache in cache_entries:
        if cache.game_id not in seen_game_ids:
            seen_game_ids.add(cache.game_id)
            u_count = user_counts_map.get(cache.game_id, 0)
            results.append(StorageGameRead(
                id=cache.game_id,
                game_id=cache.game_id,
                title=cache.title,
                steam_app_id=cache.steam_app_id,
                user_count=u_count,
                cached_size_bytes=cache.cached_size_bytes,
                build_id=cache.build_id,
                latest_build_id=cache.latest_build_id,
                last_check=cache.last_check,
                is_cached=cache.is_cached,
                orphaned_at=cache.orphaned_at,
                purged_at=cache.purged_at,
                cached_at=cache.cached_at,
                updated_at=cache.updated_at,
            ))

    return results


@router.post("/storage/{game_id}/update", response_model=StorageUpdateResponse, status_code=200)
async def force_update_storage_game(
    game_id: int,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
    admin: User = Depends(require_admin)
):
    """
    R6.3: Force SteamCMD update / re-validation for a specific game.
    Dispatches background depot download task with validate flag.
    Returns HTTP 200/202 with task ID or 404 if game nonexistent.
    """
    game = session.get(Game, game_id)
    if not game:
        raise HTTPException(status_code=404, detail=f"Game with ID {game_id} not found")

    now = datetime.now(timezone.utc)
    cache_entry = session.exec(
        select(ServerGameCache).where(ServerGameCache.game_id == game_id)
    ).first()
    if not cache_entry:
        cache_entry = ServerGameCache(
            game_id=game.id,
            title=game.title,
            steam_app_id=game.steam_app_id,
            last_check=now,
            updated_at=now
        )
        session.add(cache_entry)
    else:
        cache_entry.last_check = now
        cache_entry.updated_at = now
        session.add(cache_entry)
    session.commit()

    task = depot_downloader.start_download(
        game_id=game.id,
        game_title=game.title,
        steam_app_id=game.steam_app_id
    )
    background_tasks.add_task(run_depot_download_task, task.id, game.id)

    return StorageUpdateResponse(
        status="queued",
        message=f"SteamCMD update/re-validation initiated for '{game.title}'",
        game_id=game.id,
        task_id=task.id
    )


@router.post("/storage/{game_id}/purge", response_model=StoragePurgeResponse, status_code=200)
async def purge_storage_game(
    game_id: int,
    session: Session = Depends(get_session),
    admin: User = Depends(require_admin)
):
    """
    R6.4: Manually purge cached files on server disk and reset ServerGameCache record.
    Overrides the 7-day orphan retention countdown for immediate reclamation.
    """
    purge_info = cache_cleaner.purge_game_cache(game_id, session=session)

    if purge_info:
        return StoragePurgeResponse(
            status="purged",
            message=f"Purged cached files for '{purge_info['title']}'",
            game_id=game_id,
            freed_bytes=purge_info.get("freed_bytes", 0),
            purged_at=purge_info.get("purged_at")
        )

    game = session.get(Game, game_id)
    if not game:
        raise HTTPException(
            status_code=404,
            detail=f"Game with ID {game_id} not found"
        )

    freed_bytes = _safe_purge_disk_repository(game.title)
    now = datetime.now(timezone.utc)

    cache_entry = session.exec(
        select(ServerGameCache).where(ServerGameCache.game_id == game.id)
    ).first()
    if not cache_entry:
        cache_entry = ServerGameCache(
            game_id=game.id,
            title=game.title,
            steam_app_id=game.steam_app_id,
            is_cached=False,
            cached_size_bytes=0,
            purged_at=now,
            updated_at=now
        )
    else:
        cache_entry.is_cached = False
        cache_entry.cached_size_bytes = 0
        cache_entry.purged_at = now
        cache_entry.updated_at = now
    session.add(cache_entry)
    session.commit()

    return StoragePurgeResponse(
        status="purged",
        message=f"Game '{game.title}' is not cached on server",
        game_id=game.id,
        freed_bytes=freed_bytes,
        purged_at=now
    )



