"""
Library API endpoints for managing installed games and downloads.
"""
from typing import List, Optional
from pathlib import Path
import os
from fastapi import APIRouter, Depends, HTTPException, Response, Request
from fastapi.responses import FileResponse, StreamingResponse
from sqlmodel import Session, select
from pydantic import BaseModel

from app.core.db import get_session
from app.core.config import settings
from app.core.auth import get_current_user_optional
from app.models.game import Game, GameRead
from app.models.user import User

router = APIRouter()

# ============================================================
# Install Preparation
# ============================================================

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
    repo_path: str  # Full path on server (for debug)

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
    
    # Find game folder in repo
    repo_path = settings.GAMES_REPO_PATH
    game_folder = os.path.join(repo_path, game.title)
    
    if not os.path.exists(game_folder):
        raise HTTPException(
            status_code=404, 
            detail=f"Game folder not found in repository: {game.title}"
        )
    
    # Enumerate all files
    files = []
    total_size = 0
    
    for root, dirs, filenames in os.walk(game_folder):
        # Get relative path from game folder
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
                    path=rel_path.replace("\\", "/"),  # Normalize to forward slashes
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
# File Download (for install)
# ============================================================

@router.get("/download/{game_id}/{file_path:path}")
async def download_file(
    game_id: int,
    file_path: str,
    request: Request,
    session: Session = Depends(get_session)
):
    """
    Download a specific file from a game's folder.
    Supports range requests for resumable downloads.
    """
    game = session.get(Game, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    # Construct full path
    repo_path = settings.GAMES_REPO_PATH
    game_folder = os.path.join(repo_path, game.title)
    full_path = os.path.join(game_folder, file_path)
    
    # Security: Ensure path is within game folder (prevent path traversal)
    full_path = os.path.abspath(full_path)
    game_folder = os.path.abspath(game_folder)
    if not full_path.startswith(game_folder):
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not os.path.exists(full_path) or not os.path.isfile(full_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    file_size = os.path.getsize(full_path)
    
    # Check for range request (resumable download)
    range_header = request.headers.get("range")
    
    if range_header:
        # Parse range header: "bytes=start-end"
        try:
            range_spec = range_header.replace("bytes=", "")
            if "-" in range_spec:
                start_str, end_str = range_spec.split("-")
                start = int(start_str) if start_str else 0
                end = int(end_str) if end_str else file_size - 1
            else:
                start = int(range_spec)
                end = file_size - 1
        except ValueError:
            raise HTTPException(status_code=416, detail="Invalid range")
        
        if start >= file_size or end >= file_size or start > end:
            raise HTTPException(status_code=416, detail="Range not satisfiable")
        
        # Return partial content
        content_length = end - start + 1
        
        def iter_file():
            with open(full_path, "rb") as f:
                f.seek(start)
                remaining = content_length
                while remaining > 0:
                    chunk_size = min(8192, remaining)
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    remaining -= len(chunk)
                    yield chunk
        
        return StreamingResponse(
            iter_file(),
            status_code=206,
            headers={
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Content-Length": str(content_length),
                "Accept-Ranges": "bytes",
                "Content-Type": "application/octet-stream"
            }
        )
    
    # Full file download
    return FileResponse(
        full_path,
        headers={
            "Accept-Ranges": "bytes",
            "Content-Length": str(file_size)
        }
    )

# ============================================================
# Library Status
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
