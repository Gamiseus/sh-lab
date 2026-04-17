"""
Playtime API endpoints for syncing and retrieving playtime data.
"""
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from pydantic import BaseModel

from app.core.db import get_session
from app.core.auth import get_current_user, get_current_user_optional
from app.models.user import User
from app.models.social import UserPlaytime
from app.models.game import Game

router = APIRouter()

# ============================================================
# Request/Response Schemas
# ============================================================

class PlaytimeSyncRequest(BaseModel):
    game_id: int
    session_minutes: int
    total_local_minutes: int
    last_played: str  # ISO format timestamp

class PlaytimeResponse(BaseModel):
    game_id: int
    total_minutes: int
    sessions_count: int
    last_played: Optional[datetime]

class BulkPlaytimeSyncRequest(BaseModel):
    playtimes: List[PlaytimeSyncRequest]

# ============================================================
# Playtime Endpoints
# ============================================================

@router.post("/sync", response_model=PlaytimeResponse)
async def sync_playtime(
    data: PlaytimeSyncRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Sync playtime from client to server.
    Adds the session minutes to the user's total for this game.
    """
    # Verify game exists
    game = session.get(Game, data.game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    # Get or create playtime record
    statement = select(UserPlaytime).where(
        UserPlaytime.user_id == current_user.id,
        UserPlaytime.game_id == data.game_id
    )
    playtime = session.exec(statement).first()
    
    if not playtime:
        playtime = UserPlaytime(
            user_id=current_user.id,
            game_id=data.game_id,
            total_minutes=0,
            sessions_count=0
        )
    
    # Add session time
    playtime.total_minutes += data.session_minutes
    playtime.sessions_count += 1
    
    # Update last played
    try:
        playtime.last_played = datetime.fromisoformat(data.last_played.replace('Z', '+00:00'))
    except ValueError:
        playtime.last_played = datetime.now(timezone.utc)
    
    session.add(playtime)
    session.commit()
    session.refresh(playtime)
    
    return PlaytimeResponse(
        game_id=playtime.game_id,
        total_minutes=playtime.total_minutes,
        sessions_count=playtime.sessions_count,
        last_played=playtime.last_played
    )

@router.post("/sync/bulk")
async def bulk_sync_playtime(
    data: BulkPlaytimeSyncRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Sync multiple game playtimes at once.
    Useful for initial sync or catching up after offline play.
    """
    results = []
    
    for pt in data.playtimes:
        # Get or create playtime record
        statement = select(UserPlaytime).where(
            UserPlaytime.user_id == current_user.id,
            UserPlaytime.game_id == pt.game_id
        )
        playtime = session.exec(statement).first()
        
        if not playtime:
            playtime = UserPlaytime(
                user_id=current_user.id,
                game_id=pt.game_id,
                total_minutes=0,
                sessions_count=0
            )
        
        # Use max of local or server time (handles offline play)
        if pt.total_local_minutes > playtime.total_minutes:
            playtime.total_minutes = pt.total_local_minutes
        
        playtime.sessions_count += 1
        
        try:
            new_last_played = datetime.fromisoformat(pt.last_played.replace('Z', '+00:00'))
            if not playtime.last_played or new_last_played > playtime.last_played:
                playtime.last_played = new_last_played
        except ValueError:
            pass
        
        session.add(playtime)
        results.append({
            "game_id": pt.game_id,
            "synced": True,
            "server_total": playtime.total_minutes
        })
    
    session.commit()
    
    return {
        "synced_count": len(results),
        "results": results
    }

@router.get("/me", response_model=List[PlaytimeResponse])
async def get_my_playtime(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Get all playtime records for the current user.
    """
    statement = select(UserPlaytime).where(UserPlaytime.user_id == current_user.id)
    playtimes = session.exec(statement).all()
    
    return [
        PlaytimeResponse(
            game_id=pt.game_id,
            total_minutes=pt.total_minutes,
            sessions_count=pt.sessions_count,
            last_played=pt.last_played
        )
        for pt in playtimes
    ]

@router.get("/game/{game_id}", response_model=Optional[PlaytimeResponse])
async def get_game_playtime(
    game_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Get playtime for a specific game for the current user.
    """
    statement = select(UserPlaytime).where(
        UserPlaytime.user_id == current_user.id,
        UserPlaytime.game_id == game_id
    )
    playtime = session.exec(statement).first()
    
    if not playtime:
        return None
    
    return PlaytimeResponse(
        game_id=playtime.game_id,
        total_minutes=playtime.total_minutes,
        sessions_count=playtime.sessions_count,
        last_played=playtime.last_played
    )

@router.get("/leaderboard/{game_id}")
async def get_game_leaderboard(
    game_id: int,
    limit: int = 10,
    session: Session = Depends(get_session)
):
    """
    Get top players by playtime for a game.
    """
    statement = (
        select(UserPlaytime, User)
        .join(User, User.id == UserPlaytime.user_id)
        .where(UserPlaytime.game_id == game_id)
        .where(User.privacy_level == "public")
        .order_by(UserPlaytime.total_minutes.desc())
        .limit(limit)
    )
    
    results = session.exec(statement).all()
    
    return [
        {
            "rank": i + 1,
            "user_id": user.id,
            "username": user.username,
            "display_name": user.display_name,
            "total_minutes": pt.total_minutes,
            "sessions_count": pt.sessions_count
        }
        for i, (pt, user) in enumerate(results)
    ]
