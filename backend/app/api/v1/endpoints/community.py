"""
Community API endpoints for user discovery.
"""
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select, func, or_
from pydantic import BaseModel

from app.core.db import get_session
from app.core.auth import get_current_user_optional
from app.models.user import User
from app.models.social import UserPlaytime

router = APIRouter()

# ============================================================
# Response Schemas
# ============================================================

class UserCardData(BaseModel):
    id: int
    username: str
    display_name: Optional[str]
    avatar_url: Optional[str]
    games_count: int
    total_playtime_hours: float
    joined_date: Optional[datetime]

class CommunityResponse(BaseModel):
    users: List[UserCardData]
    total: int
    page: int
    per_page: int

# ============================================================
# Community Endpoints
# ============================================================

@router.get("/users", response_model=CommunityResponse)
async def list_public_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=50),
    sort_by: str = Query("recent", pattern="^(recent|playtime|games|name)$"),
    session: Session = Depends(get_session)
):
    """
    List all public users for community discovery.
    Excludes private profiles.
    """
    offset = (page - 1) * per_page
    
    # Base query - only public users
    base_query = select(User).where(
        User.privacy_level == "public",
        User.is_active == True
    )
    
    # Get total count
    total = session.exec(
        select(func.count(User.id)).where(
            User.privacy_level == "public",
            User.is_active == True
        )
    ).one()
    
    # Build sorted query
    if sort_by == "recent":
        statement = base_query.order_by(User.created_at.desc())
    elif sort_by == "name":
        statement = base_query.order_by(User.display_name.asc().nullslast(), User.username.asc())
    else:
        statement = base_query.order_by(User.created_at.desc())
    
    statement = statement.offset(offset).limit(per_page)
    users = session.exec(statement).all()
    
    if not users:
        return CommunityResponse(users=[], total=total, page=page, per_page=per_page)
    
    # Batch fetch playtime stats for all users in one query (avoids N+1)
    user_ids = [u.id for u in users]
    playtime_stats = session.exec(
        select(
            UserPlaytime.user_id,
            func.count(UserPlaytime.id).label("games_count"),
            func.coalesce(func.sum(UserPlaytime.total_minutes), 0).label("total_minutes")
        )
        .where(UserPlaytime.user_id.in_(user_ids))
        .group_by(UserPlaytime.user_id)
    ).all()
    
    # Build lookup dict: user_id -> (games_count, total_minutes)
    stats_map = {row[0]: (row[1], row[2]) for row in playtime_stats}
    
    # Build response cards
    user_cards = []
    for user in users:
        games_count, total_minutes = stats_map.get(user.id, (0, 0))
        user_cards.append(UserCardData(
            id=user.id,
            username=user.username,
            display_name=user.display_name,
            avatar_url=user.avatar_url,
            games_count=games_count,
            total_playtime_hours=round(total_minutes / 60, 1),
            joined_date=user.created_at
        ))
    
    # Sort by playtime/games if requested (post-query sort since DB sort doesn't include stats)
    if sort_by == "playtime":
        user_cards.sort(key=lambda x: x.total_playtime_hours, reverse=True)
    elif sort_by == "games":
        user_cards.sort(key=lambda x: x.games_count, reverse=True)
    
    return CommunityResponse(
        users=user_cards,
        total=total,
        page=page,
        per_page=per_page
    )

@router.get("/search", response_model=List[UserCardData])
async def search_users(
    q: str = Query(..., min_length=1, max_length=100),
    limit: int = Query(10, ge=1, le=50),
    session: Session = Depends(get_session)
):
    """
    Search for users by username or display name.
    Only returns public profiles.
    """
    search_term = f"%{q}%"
    
    statement = (
        select(User)
        .where(
            User.privacy_level == "public",
            User.is_active == True,
            or_(
                User.username.ilike(search_term),
                User.display_name.ilike(search_term)
            )
        )
        .order_by(User.username.asc())
        .limit(limit)
    )
    
    users = session.exec(statement).all()
    
    user_cards = []
    for user in users:
        playtime_result = session.exec(
            select(
                func.count(UserPlaytime.id),
                func.coalesce(func.sum(UserPlaytime.total_minutes), 0)
            ).where(UserPlaytime.user_id == user.id)
        ).one()
        
        games_count, total_minutes = playtime_result
        
        user_cards.append(UserCardData(
            id=user.id,
            username=user.username,
            display_name=user.display_name,
            avatar_url=user.avatar_url,
            games_count=games_count,
            total_playtime_hours=round(total_minutes / 60, 1),
            joined_date=user.created_at
        ))
    
    return user_cards
