"""
Library API endpoints for managing installed games, downloads, and streaming.
"""
from typing import List, Optional
from pathlib import Path
import os
import asyncio
import json
import mimetypes
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Response, Request, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select, SQLModel, Field
from pydantic import BaseModel

from app.core.db import get_session, engine
from app.core.config import settings
from app.core.auth import get_current_user_optional
from app.models.game import Game, GameRead
from app.models.user import User
from app.models.library import UserLibrary, ServerGameCache
from app.services.task_manager import task_manager
from app.services.depot_downloader import depot_downloader, run_depot_download_task

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

# Ensure database tables are created
try:
    SQLModel.metadata.create_all(engine)
except Exception:
    pass

# ============================================================
# Schemas
# ============================================================

class AddUserLibraryRequest(BaseModel):
    game_id: int

class UserLibraryRead(BaseModel):
    id: int
    user_id: int
    game_id: int
    status: str
    added_at: datetime
    installed_at: Optional[datetime] = None
    game: Optional[GameRead] = None

class LibrarySyncRequest(BaseModel):
    game_ids: List[int]

class InstallRequestResponse(BaseModel):
    cached: bool
    task_id: Optional[str] = None
    message: Optional[str] = None

class FileInfo(BaseModel):
    path: str  # Relative path within game folder
    size: int  # Size in bytes
    is_dir: bool

class InstallInfo(BaseModel):
    game_id: int
    title: str
    total_size: int  # Total bytes
    file_count: int
    files: List[FileInfo]
    repo_path: str  # Full path on server

class DepotUpdateRead(BaseModel):
    game_id: int
    title: str
    steam_app_id: Optional[int] = None
    current_build_id: Optional[str] = None
    build_id: Optional[str] = None
    latest_build_id: Optional[str] = None
    has_update: bool = False
    last_check: Optional[datetime] = None
    is_cached: bool = False
    cached_size_bytes: int = 0

router = APIRouter()

# ============================================================
# User Library Management Endpoints
# ============================================================

def _on_game_added(session: Session, game_id: int) -> None:
    """
    R5.6 / R5.B4: When a game is added to a user's library,
    if it was previously orphaned (orphaned_at not None in ServerGameCache),
    reset orphaned_at = None.
    """
    cache_entry = session.exec(
        select(ServerGameCache).where(ServerGameCache.game_id == game_id)
    ).first()
    if cache_entry and cache_entry.orphaned_at is not None:
        cache_entry.orphaned_at = None
        cache_entry.updated_at = utc_now()
        session.add(cache_entry)


def _on_game_removed(session: Session, game_id: int, user_id: int) -> None:
    """
    R5.4 / R5.B4: When a game is removed from a user's library (via sync or delete),
    check if any other users still have this game.
    If total user references across all users drops to 0,
    mark orphaned_at = utc_now() in ServerGameCache if the title is cached.
    """
    other_ref = session.exec(
        select(UserLibrary).where(
            UserLibrary.game_id == game_id,
            UserLibrary.user_id != user_id
        )
    ).first()

    if not other_ref:
        cache_entry = session.exec(
            select(ServerGameCache).where(ServerGameCache.game_id == game_id)
        ).first()

        is_cached = False
        if cache_entry and (cache_entry.is_cached or cache_entry.cached_size_bytes > 0):
            is_cached = True
        else:
            game = session.get(Game, game_id)
            if game:
                repo_path = os.path.abspath(settings.GAMES_REPO_PATH)
                game_folder = os.path.join(repo_path, game.title)
                if os.path.isdir(game_folder):
                    try:
                        with os.scandir(game_folder) as entries:
                            if any(entries):
                                is_cached = True
                                if not cache_entry:
                                    cache_entry = ServerGameCache(
                                        game_id=game.id,
                                        title=game.title,
                                        steam_app_id=game.steam_app_id,
                                        is_cached=True,
                                        cached_at=utc_now()
                                    )
                                    session.add(cache_entry)
                    except OSError:
                        pass

        if is_cached and cache_entry:
            if cache_entry.orphaned_at is None:
                cache_entry.orphaned_at = utc_now()
                cache_entry.updated_at = utc_now()
                session.add(cache_entry)


@router.get("/user", response_model=List[UserLibraryRead])
def get_user_library(
    session: Session = Depends(get_session),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Get all games tracked in the current user's library."""
    target_user_id = current_user.id if current_user else 1
    statement = select(UserLibrary).where(UserLibrary.user_id == target_user_id)
    entries = session.exec(statement).all()

    result = []
    for entry in entries:
        game = session.get(Game, entry.game_id)
        result.append(UserLibraryRead(
            id=entry.id,
            user_id=entry.user_id,
            game_id=entry.game_id,
            status=entry.status,
            added_at=entry.added_at,
            installed_at=entry.installed_at,
            game=game
        ))
    return result

@router.post("/user", response_model=UserLibraryRead, status_code=200)
def add_to_user_library(
    body: AddUserLibraryRequest,
    session: Session = Depends(get_session),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Add a game to the user's library without file downloads (idempotent)."""
    game = session.get(Game, body.game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    target_user_id = current_user.id if current_user else 1
    existing = session.exec(
        select(UserLibrary).where(
            UserLibrary.user_id == target_user_id,
            UserLibrary.game_id == body.game_id
        )
    ).first()

    if not existing:
        entry = UserLibrary(
            user_id=target_user_id,
            game_id=body.game_id,
            status="uninstalled",
            added_at=utc_now(),
            last_updated=utc_now()
        )
        session.add(entry)
    else:
        entry = existing

    # Reset orphaned status if title was previously orphaned (R5.6)
    _on_game_added(session, body.game_id)

    session.commit()
    session.refresh(entry)

    return UserLibraryRead(
        id=entry.id,
        user_id=entry.user_id,
        game_id=entry.game_id,
        status=entry.status,
        added_at=entry.added_at,
        installed_at=entry.installed_at,
        game=game
    )

@router.post("/user/{game_id}", response_model=UserLibraryRead, status_code=200)
def add_to_user_library_path(
    game_id: int,
    session: Session = Depends(get_session),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Path param variant for adding a game to the user's library."""
    return add_to_user_library(
        body=AddUserLibraryRequest(game_id=game_id),
        session=session,
        current_user=current_user
    )

@router.delete("/user/{game_id}")
def remove_from_user_library(
    game_id: int,
    session: Session = Depends(get_session),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Remove a game from the user's library."""
    target_user_id = current_user.id if current_user else 1
    existing_entries = session.exec(
        select(UserLibrary).where(
            UserLibrary.user_id == target_user_id,
            UserLibrary.game_id == game_id
        )
    ).all()

    if existing_entries:
        for entry in existing_entries:
            session.delete(entry)
        # Check orphan status on other users (R5.4)
        _on_game_removed(session, game_id, target_user_id)
        session.commit()

    return {"success": True, "message": "Game removed from library", "game_id": game_id}

@router.post("/sync")
def sync_library(
    data: LibrarySyncRequest,
    session: Session = Depends(get_session),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    R5.1, R5.2, R5.B1, R5.B3: Batch synchronizes user library game IDs.
    - Associates game IDs with current authenticated user (or fallback 1).
    - Deduplicates incoming game IDs cleanly.
    - Reconciles user library: removes unreferenced games, adds newly added games.
    - Cleanly empties user library if empty list {"game_ids": []} is provided.
    - Updates orphan tracking in ServerGameCache when games are added or removed.
    """
    target_user_id = current_user.id if current_user else 1

    # 1. Deduplicate incoming game IDs preserving order
    unique_ids = list(dict.fromkeys(data.game_ids))

    # 2. Filter valid games from catalog
    valid_game_ids = []
    for gid in unique_ids:
        if session.get(Game, gid):
            valid_game_ids.append(gid)

    desired_ids_set = set(valid_game_ids)

    # 3. Retrieve user's current library entries
    current_entries = session.exec(
        select(UserLibrary).where(UserLibrary.user_id == target_user_id)
    ).all()

    current_by_game_id: dict[int, list[UserLibrary]] = {}
    for entry in current_entries:
        current_by_game_id.setdefault(entry.game_id, []).append(entry)

    current_ids_set = set(current_by_game_id.keys())

    # 4. Reconciliation: Remove games no longer in the synced list
    to_remove_ids = current_ids_set - desired_ids_set
    for remove_gid in to_remove_ids:
        for entry in current_by_game_id[remove_gid]:
            session.delete(entry)
        _on_game_removed(session, remove_gid, target_user_id)

    # 5. Clean up any existing duplicate entries for retained games and disarm orphan
    for retain_gid in desired_ids_set & current_ids_set:
        entries = current_by_game_id[retain_gid]
        if len(entries) > 1:
            for extra_entry in entries[1:]:
                session.delete(extra_entry)
        _on_game_added(session, retain_gid)

    # 6. Add newly synced games
    to_add_ids = [gid for gid in valid_game_ids if gid not in current_ids_set]
    for add_gid in to_add_ids:
        new_entry = UserLibrary(
            user_id=target_user_id,
            game_id=add_gid,
            status="uninstalled",
            added_at=utc_now(),
            last_updated=utc_now()
        )
        session.add(new_entry)
        _on_game_added(session, add_gid)

    session.commit()

    return {
        "status": "ok",
        "synced": True,
        "game_ids": data.game_ids
    }

@router.get("/updates", response_model=List[DepotUpdateRead])
def get_depot_updates(
    game_id: Optional[int] = None,
    available_only: bool = True,
    all: bool = False,
    user_only: bool = False,
    session: Session = Depends(get_session),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    R5.3 & R5.B5: Returns list of games with available depot updates.
    Safely handles null/empty build IDs without crashing.
    """
    query = select(ServerGameCache)
    if game_id is not None:
        query = query.where(ServerGameCache.game_id == game_id)

    cache_entries = session.exec(query).all()

    # If user_only is requested and user is authenticated, filter by user library
    if user_only and current_user:
        target_user_id = current_user.id
        user_game_ids = set(session.exec(
            select(UserLibrary.game_id).where(UserLibrary.user_id == target_user_id)
        ).all())
        cache_entries = [c for c in cache_entries if c.game_id in user_game_ids]

    filter_to_updates_only = available_only and not all
    results: List[DepotUpdateRead] = []

    for entry in cache_entries:
        installed_build = entry.build_id
        latest_build = entry.latest_build_id

        # R5.B5 Boundary check: Null / None / whitespace handling
        has_update = bool(
            installed_build is not None
            and latest_build is not None
            and str(installed_build).strip() != ""
            and str(latest_build).strip() != ""
            and str(installed_build).strip() != str(latest_build).strip()
        )

        if filter_to_updates_only and not has_update:
            continue

        results.append(DepotUpdateRead(
            game_id=entry.game_id,
            title=entry.title,
            steam_app_id=entry.steam_app_id,
            current_build_id=str(installed_build) if installed_build is not None else None,
            build_id=str(installed_build) if installed_build is not None else None,
            latest_build_id=str(latest_build) if latest_build is not None else None,
            has_update=has_update,
            last_check=entry.last_check,
            is_cached=entry.is_cached,
            cached_size_bytes=entry.cached_size_bytes,
        ))

    return results

# ============================================================
# Install Request & Preparation Endpoints (R4.1 & R4.2)
# ============================================================

@router.post("/install/{game_id}/request", response_model=InstallRequestResponse, status_code=200)
async def request_install(
    game_id: int,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    R4.1 & R4.2: Request installation of a game.
    Checks if game files exist in server repository (/data/repo/{title}).
    - If cached: returns {"cached": true, "task_id": null}.
    - If uncached: initiates background SteamCMD download task and returns {"cached": false, "task_id": str}.
    """
    game = session.get(Game, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    repo_path = os.path.abspath(settings.GAMES_REPO_PATH)
    game_folder = os.path.join(repo_path, game.title)

    is_cached = False
    if os.path.exists(game_folder) and os.path.isdir(game_folder):
        try:
            with os.scandir(game_folder) as entries:
                if any(entries):
                    is_cached = True
        except OSError:
            is_cached = False

    if not is_cached:
        try:
            cache_entry = session.exec(
                select(ServerGameCache).where(ServerGameCache.game_id == game_id)
            ).first()
            if cache_entry and cache_entry.is_cached and os.path.exists(game_folder):
                is_cached = True
        except Exception:
            pass

    if is_cached:
        return InstallRequestResponse(
            cached=True,
            task_id=None,
            message="Game files cached on server"
        )

    # Uncached: Trigger background download task
    task = depot_downloader.start_download(
        game_id=game.id,
        game_title=game.title,
        steam_app_id=game.steam_app_id
    )
    background_tasks.add_task(run_depot_download_task, task.id, game.id)

    return InstallRequestResponse(
        cached=False,
        task_id=task.id,
        message=f"Started SteamCMD background depot download for {game.title}"
    )

@router.get("/install/{game_id}/prepare", response_model=InstallInfo)
async def prepare_install(
    game_id: int,
    session: Session = Depends(get_session),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Prepare a game for installation.
    Returns the list of files to download and total size.
    The client uses this to set up the download queue.
    """
    game = session.get(Game, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    repo_path = os.path.abspath(settings.GAMES_REPO_PATH)
    game_folder = os.path.join(repo_path, game.title)

    if not os.path.exists(game_folder):
        raise HTTPException(
            status_code=404,
            detail=f"Game folder not found in repository: {game.title}"
        )

    files = []
    total_size = 0

    for root, dirs, filenames in os.walk(game_folder):
        rel_root = os.path.relpath(root, game_folder)
        if rel_root == ".":
            rel_root = ""

        for filename in filenames:
            file_path = os.path.join(root, filename)
            rel_path = os.path.join(rel_root, filename) if rel_root else filename
            try:
                size = os.path.getsize(file_path)
                total_size += size
                files.append(FileInfo(
                    path=rel_path.replace("\\", "/"),
                    size=size,
                    is_dir=False
                ))
            except OSError:
                continue

    return InstallInfo(
        game_id=game_id,
        title=game.title,
        total_size=total_size,
        file_count=len(files),
        files=files,
        repo_path=game_folder
    )

# ============================================================
# Task SSE Stream Endpoint (R4.3)
# ============================================================

@router.get("/tasks/{task_id}/stream")
async def stream_task_events(
    task_id: str,
    token: Optional[str] = None,
    session: Session = Depends(get_session),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    R4.3: Server-Sent Events (SSE) stream broadcasting download progress, state, and logs.
    """
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

# ============================================================
# File Download & HTTP 206 Chunk Streaming (R4.4 & R4.6)
# ============================================================

@router.get("/download/{game_id}/{file_path:path}")
async def download_file(
    game_id: int,
    file_path: str,
    request: Request,
    session: Session = Depends(get_session)
):
    """
    R4.4 & R4.6: Download a specific file with HTTP 206 Range partial content streaming.
    Blocks directory traversal with HTTP 403.
    """
    game = session.get(Game, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    repo_path = os.path.abspath(settings.GAMES_REPO_PATH)
    game_folder = os.path.abspath(os.path.join(repo_path, game.title))
    full_path = os.path.abspath(os.path.join(game_folder, file_path))

    # Security: Strict directory traversal prevention (R4.6)
    try:
        common = os.path.commonpath([full_path, game_folder])
        if common != game_folder:
            raise HTTPException(status_code=403, detail="Access denied: Directory traversal forbidden")
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied: Invalid path")

    if not os.path.exists(full_path) or not os.path.isfile(full_path):
        raise HTTPException(status_code=404, detail="File not found")

    file_size = os.path.getsize(full_path)
    content_type, _ = mimetypes.guess_type(full_path)
    if not content_type:
        content_type = "application/octet-stream"

    range_header = request.headers.get("range")

    # Boundary handling: 0-byte file (R4.B3)
    if file_size == 0:
        if range_header:
            return Response(
                status_code=416,
                headers={
                    "Content-Range": "bytes */0",
                    "Content-Length": "0"
                }
            )
        return Response(
            content=b"",
            status_code=200,
            headers={
                "Accept-Ranges": "bytes",
                "Content-Length": "0",
                "Content-Type": content_type
            }
        )

    # Range request (HTTP 206 Partial Content)
    if range_header:
        if not range_header.startswith("bytes="):
            raise HTTPException(
                status_code=416,
                detail="Invalid range format",
                headers={"Content-Range": f"bytes */{file_size}"}
            )

        spec = range_header[6:].strip()
        try:
            if "-" in spec:
                start_str, end_str = spec.split("-", 1)
                start = int(start_str) if start_str else 0
                end = int(end_str) if end_str else file_size - 1
            else:
                start = int(spec)
                end = file_size - 1
        except ValueError:
            raise HTTPException(
                status_code=416,
                detail="Invalid range specifier",
                headers={"Content-Range": f"bytes */{file_size}"}
            )

        # Boundary checks: out-of-bounds or inverted range (R4.B1 & R4.B2)
        if start < 0 or end >= file_size or start > end:
            raise HTTPException(
                status_code=416,
                detail="Range Not Satisfiable",
                headers={"Content-Range": f"bytes */{file_size}"}
            )

        content_length = end - start + 1

        def iter_range_chunks():
            with open(full_path, "rb") as f:
                f.seek(start)
                remaining = content_length
                while remaining > 0:
                    chunk_size = min(65536, remaining)
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    remaining -= len(chunk)
                    yield chunk

        return StreamingResponse(
            iter_range_chunks(),
            status_code=206,
            headers={
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Content-Length": str(content_length),
                "Accept-Ranges": "bytes",
                "Content-Type": content_type
            }
        )

    # Full file streaming
    def iter_full_chunks():
        with open(full_path, "rb") as f:
            while True:
                chunk = f.read(65536)
                if not chunk:
                    break
                yield chunk

    return StreamingResponse(
        iter_full_chunks(),
        status_code=200,
        headers={
            "Accept-Ranges": "bytes",
            "Content-Length": str(file_size),
            "Content-Type": content_type
        }
    )

# ============================================================
# Catalog & Installed Queries
# ============================================================

@router.get("/", response_model=List[GameRead])
def read_games(
    offset: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session)
):
    """List all games in the catalog (for reference)."""
    games = session.exec(select(Game).offset(offset).limit(limit)).all()
    return games

@router.get("/installed")
async def get_installed_games():
    """
    Placeholder for getting list of installed games.
    In practice, the client scans local folders and reports back.
    """
    return {
        "message": "Client-side scanning required",
        "hint": "Use the frontend library scanner to detect installed games"
    }
