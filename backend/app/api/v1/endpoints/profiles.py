"""
User Profile API endpoints.
"""
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlmodel import Session, select, func, col
from pydantic import BaseModel
import os
import shutil
import uuid

from app.core.db import get_session
from app.core.auth import get_current_user, get_current_user_optional
from app.models.user import User, UserUpdate, UserRead
from app.models.game import Game
from app.models.social import UserPlaytime, Friendship
from app.models.review import Review
from app.core.config import settings
from app.models.config import SystemConfig

router = APIRouter()

# ============================================================
# Response Schemas
# ============================================================

class GameWithPlaytime(BaseModel):
    id: int
    title: str
    cover_url: Optional[str]
    total_minutes: int
    last_played: Optional[datetime]
    sessions_count: int

class ProfileStats(BaseModel):
    games_count: int
    total_playtime_minutes: int
    reviews_count: int
    joined_date: Optional[datetime]



class ReviewSummary(BaseModel):
    id: int
    game_id: int
    game_title: str
    game_cover: Optional[str]
    rating: int
    is_recommended: Optional[bool]
    content: str
    created_at: Optional[datetime]

class FavoriteGameDisplay(BaseModel):
    id: int
    title: str
    cover_url: Optional[str]
    total_minutes: int
    user_rating: Optional[int]

class PublicProfile(BaseModel):
    id: int
    username: str
    display_name: Optional[str]
    avatar_url: Optional[str]
    bio: Optional[str]
    background_url: Optional[str]
    privacy_level: str
    favorite_games: List[FavoriteGameDisplay] = []
    stats: ProfileStats
    is_friend: bool = False
    friend_status: Optional[str] = None  # 'pending', 'accepted', 'sent'

class ImageInfo(BaseModel):
    url: str
    filename: str
    type: str
    created_at: datetime
    is_server: bool = False

# ============================================================
# Helper Functions
# ============================================================

def get_enriched_favorites(session: Session, game_ids: List[int], user_id: int) -> List[FavoriteGameDisplay]:
    """Fetch enriched data for favorite games (ordered)."""
    if not game_ids:
        return []
        
    # 1. Fetch games
    games = session.exec(select(Game).where(col(Game.id).in_(game_ids))).all()
    games_map = {g.id: g for g in games}
    
    # 2. Fetch playtime
    playtime_recs = session.exec(
        select(UserPlaytime).where(
            UserPlaytime.user_id == user_id,
            col(UserPlaytime.game_id).in_(game_ids)
        )
    ).all()
    playtime_map = {p.game_id: p.total_minutes for p in playtime_recs}
    
    # 3. Fetch reviews
    reviews = session.exec(
        select(Review).where(
            Review.user_id == user_id,
            col(Review.game_id).in_(game_ids)
        )
    ).all()
    rating_map = {r.game_id: r.rating for r in reviews}
    
    # 4. Assemble in ORDER of game_ids
    result = []
    for gid in game_ids:
        game = games_map.get(gid)
        if not game:
            continue
            
        result.append(FavoriteGameDisplay(
            id=game.id,
            title=game.title,
            cover_url=game.cover_url,
            total_minutes=playtime_map.get(gid, 0),
            user_rating=rating_map.get(gid)
        ))
        
    return result

def get_user_stats(session: Session, user_id: int) -> ProfileStats:
    """Calculate user's profile stats."""
    # Games count (from playtime records)
    games_count = session.exec(
        select(func.count(UserPlaytime.id)).where(UserPlaytime.user_id == user_id)
    ).one()
    
    # Total playtime
    total_playtime = session.exec(
        select(func.sum(UserPlaytime.total_minutes)).where(UserPlaytime.user_id == user_id)
    ).one() or 0
    
    # Reviews count
    reviews_count = session.exec(
        select(func.count(Review.id)).where(Review.user_id == user_id)
    ).one()
    
    # Get user for join date
    user = session.get(User, user_id)
    
    return ProfileStats(
        games_count=games_count,
        total_playtime_minutes=total_playtime,
        reviews_count=reviews_count,
        joined_date=user.created_at if user else None
    )

def check_privacy(
    target_user: User,
    current_user: Optional[User],
    session: Session
) -> bool:
    """Check if current user can view target user's profile."""
    if target_user.privacy_level == "public":
        return True
    
    if current_user is None:
        return False
    
    if current_user.id == target_user.id:
        return True
    
    if current_user.is_admin:
        return True
    
    if target_user.privacy_level == "friends":
        # Check if they are friends
        friendship = session.exec(
            select(Friendship).where(
                ((Friendship.user_id == current_user.id) & (Friendship.friend_id == target_user.id)) |
                ((Friendship.user_id == target_user.id) & (Friendship.friend_id == current_user.id)),
                Friendship.status == "accepted"
            )
        ).first()
        return friendship is not None
    
    return False

def get_friend_status(session: Session, user_id: int, target_id: int) -> Optional[str]:
    """Get friendship status between two users."""
    if user_id == target_id:
        return None
    
    # Check if current user sent request
    sent = session.exec(
        select(Friendship).where(
            Friendship.user_id == user_id,
            Friendship.friend_id == target_id
        )
    ).first()
    
    if sent:
        return "sent" if sent.status == "pending" else sent.status
    
    # Check if target user sent request
    received = session.exec(
        select(Friendship).where(
            Friendship.user_id == target_id,
            Friendship.friend_id == user_id
        )
    ).first()
    
    if received:
        return "pending" if received.status == "pending" else received.status
    
    return None

# ============================================================
# Profile Endpoints
# ============================================================

@router.get("/me", response_model=PublicProfile)
async def get_own_profile(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get own full profile including stats."""
    stats = get_user_stats(session, current_user.id)
    
    favorites = get_enriched_favorites(session, current_user.favorite_game_ids or [], current_user.id)
    
    return PublicProfile(
        id=current_user.id,
        username=current_user.username,
        display_name=current_user.display_name,
        avatar_url=current_user.avatar_url,
        bio=current_user.bio,
        background_url=current_user.background_url,
        privacy_level=current_user.privacy_level,
        favorite_games=favorites,
        stats=stats,
        is_friend=False,
        friend_status=None
    )

@router.put("/me", response_model=UserRead)
async def update_own_profile(
    profile_data: UserUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Update own profile."""
    # Update fields
    if profile_data.display_name is not None:
        current_user.display_name = profile_data.display_name
    if profile_data.email is not None:
        current_user.email = profile_data.email
    if profile_data.avatar_url is not None:
        current_user.avatar_url = profile_data.avatar_url
    if profile_data.bio is not None:
        current_user.bio = profile_data.bio
    if profile_data.background_url is not None:
        current_user.background_url = profile_data.background_url
    if profile_data.privacy_level is not None:
        if profile_data.privacy_level not in ["public", "friends", "private"]:
            raise HTTPException(status_code=400, detail="Invalid privacy level")
        current_user.privacy_level = profile_data.privacy_level
    
    session.add(current_user)
    session.commit()
    session.refresh(current_user)
    
    return current_user

@router.put("/me/favorites", response_model=List[FavoriteGameDisplay])
async def update_favorites(
    game_ids: List[int],
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Update favorite games list (Max 12)."""
    if len(game_ids) > 12:
        raise HTTPException(status_code=400, detail="Maximum 12 favorite games allowed")
        
    # Verify unique
    if len(game_ids) != len(set(game_ids)):
        raise HTTPException(status_code=400, detail="Duplicate games in list")
        
    current_user.favorite_game_ids = game_ids
    session.add(current_user)
    session.commit()
    
    return get_enriched_favorites(session, game_ids, current_user.id)

@router.post("/me/images", response_model=ImageInfo)
async def upload_profile_image(
    type: str = Query(..., pattern="^(avatar|background)$"),
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Upload a profile image (avatar or background)."""
    # Check config limits
    max_size_mb_cfg = session.get(SystemConfig, "profile_max_file_size_mb")
    max_size_mb = int(max_size_mb_cfg.value) if max_size_mb_cfg else 5
    
    max_images_cfg = session.get(SystemConfig, "profile_max_images")
    max_count = int(max_images_cfg.value) if max_images_cfg else 10
    
    # Path: /data/profiles/{user_id}/{type}/
    upload_dir = os.path.join(settings.DATA_DIR, "profiles", str(current_user.id), type)
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir, exist_ok=True)

    # Check count (files in dir)
    existing = [f for f in os.listdir(upload_dir) if os.path.isfile(os.path.join(upload_dir, f))]
    if len(existing) >= max_count:
        raise HTTPException(400, f"Maximum {max_count} images allowed for {type}. Delete some images first.")
    
    # Validate extension
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".jpg", ".jpeg", ".png", ".gif", ".webp"]:
        raise HTTPException(400, "Invalid image format.")
        
    filename = f"{uuid.uuid4().hex[:8]}{ext}"
    file_path = os.path.join(upload_dir, filename)
    
    # Save file
    try:
        content = await file.read()
        if len(content) > max_size_mb * 1024 * 1024:
            raise HTTPException(400, f"File too large. Maximum size is {max_size_mb}MB.")
            
        with open(file_path, "wb") as buffer:
            buffer.write(content)
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise e
        
    # URL: /profiles/{user_id}/{type}/{filename}
    url = f"/profiles/{current_user.id}/{type}/{filename}"
    return ImageInfo(
        url=url,
        filename=filename,
        type=type,
        created_at=datetime.now(timezone.utc),
        is_server=False
    )

@router.get("/me/images", response_model=List[ImageInfo])
async def list_profile_images(
    type: Optional[str] = Query(None, pattern="^(avatar|background)$"),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """List uploaded profile images."""
    results = []
    types = [type] if type else ["avatar", "background"]
    
    for t in types:
         upload_dir = os.path.join(settings.DATA_DIR, "profiles", str(current_user.id), t)
         if os.path.exists(upload_dir):
             for f in os.listdir(upload_dir):
                 if os.path.isfile(os.path.join(upload_dir, f)):
                     path = os.path.join(upload_dir, f)
                     results.append(ImageInfo(
                         url=f"/profiles/{current_user.id}/{t}/{f}",
                         filename=f,
                         type=t,
                         created_at=datetime.fromtimestamp(os.path.getmtime(path)),
                         is_server=False
                     ))
    return sorted(results, key=lambda x: x.created_at, reverse=True)

@router.get("/server/images", response_model=List[str])
async def list_server_images(
    type: str = Query(..., pattern="^(avatar|background)$"),
    current_user: User = Depends(get_current_user)
):
    """List server preset images."""
    folder_name = f"{type}s"
    server_dir = os.path.join(settings.DATA_DIR, "server", folder_name)
    
    if not os.path.exists(server_dir):
        os.makedirs(server_dir, exist_ok=True)
        return []
        
    results = []
    for f in os.listdir(server_dir):
        if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp", ".gif")):
             results.append(f"/server/{folder_name}/{f}")
    return sorted(results)

@router.delete("/me/images")
async def delete_profile_image(
    filename: str,
    type: str = Query(..., pattern="^(avatar|background)$"),
    current_user: User = Depends(get_current_user)
):
    """Delete an uploaded profile image."""
    upload_dir = os.path.join(settings.DATA_DIR, "profiles", str(current_user.id), type)
    
    # Prevent directory traversal
    safe_filename = os.path.basename(filename)
    file_path = os.path.join(upload_dir, safe_filename)
    
    if os.path.exists(file_path):
        os.remove(file_path)
        return {"status": "success"}
    
    raise HTTPException(404, "Image not found")

@router.get("/{user_id}", response_model=PublicProfile)
async def get_user_profile(
    user_id: int,
    session: Session = Depends(get_session),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Get a user's public profile."""
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    can_view = check_privacy(user, current_user, session)
    
    stats = get_user_stats(session, user_id)
    friend_status = get_friend_status(session, current_user.id, user_id) if current_user else None
    
    if not can_view:
        # Return limited profile for private users
        return PublicProfile(
            id=user.id,
            username=user.username,
            display_name=user.display_name,
            avatar_url=user.avatar_url,
            bio=None,  # Hidden
            background_url=None,  # Hidden
            privacy_level=user.privacy_level,
            favorite_games=[],
            stats=ProfileStats(
                games_count=0,
                total_playtime_minutes=0,
                reviews_count=0,
                joined_date=user.created_at
            ),
            is_friend=friend_status == "accepted",
            friend_status=friend_status
        )
    
    favorites = get_enriched_favorites(session, user.favorite_game_ids or [], user.id)

    return PublicProfile(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        avatar_url=user.avatar_url,
        bio=user.bio,
        background_url=user.background_url,
        privacy_level=user.privacy_level,
        favorite_games=favorites,
        stats=stats,
        is_friend=friend_status == "accepted",
        friend_status=friend_status
    )

@router.get("/{user_id}/games", response_model=List[GameWithPlaytime])
async def get_user_games(
    user_id: int,
    limit: int = 20,
    offset: int = 0,
    session: Session = Depends(get_session),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Get a user's games with playtime."""
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not check_privacy(user, current_user, session):
        raise HTTPException(status_code=403, detail="Profile is private")
    
    statement = (
        select(UserPlaytime, Game)
        .join(Game, Game.id == UserPlaytime.game_id)
        .where(UserPlaytime.user_id == user_id)
        .order_by(UserPlaytime.last_played.desc().nullslast())
        .offset(offset)
        .limit(limit)
    )
    
    results = session.exec(statement).all()
    
    return [
        GameWithPlaytime(
            id=game.id,
            title=game.title,
            cover_url=game.cover_url,
            total_minutes=playtime.total_minutes,
            last_played=playtime.last_played,
            sessions_count=playtime.sessions_count
        )
        for playtime, game in results
    ]

@router.get("/{user_id}/reviews", response_model=List[ReviewSummary])
async def get_user_reviews(
    user_id: int,
    limit: int = 20,
    offset: int = 0,
    session: Session = Depends(get_session),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Get a user's reviews."""
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not check_privacy(user, current_user, session):
        raise HTTPException(status_code=403, detail="Profile is private")
    
    statement = (
        select(Review, Game)
        .join(Game, Game.id == Review.game_id)
        .where(Review.user_id == user_id, Review.is_hidden == False)
        .order_by(Review.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    
    results = session.exec(statement).all()
    
    return [
        ReviewSummary(
            id=review.id,
            game_id=review.game_id,
            game_title=game.title,
            game_cover=game.cover_url,
            rating=review.rating,
            is_recommended=review.is_recommended,
            content=review.content[:300] + "..." if len(review.content) > 300 else review.content,
            created_at=review.created_at
        )
        for review, game in results
    ]

@router.get("/{user_id}/recent-activity", response_model=List[GameWithPlaytime])
async def get_user_recent_activity(
    user_id: int,
    limit: int = 5,
    session: Session = Depends(get_session),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Get user's recently played games."""
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not check_privacy(user, current_user, session):
        raise HTTPException(status_code=403, detail="Profile is private")
    
    statement = (
        select(UserPlaytime, Game)
        .join(Game, Game.id == UserPlaytime.game_id)
        .where(UserPlaytime.user_id == user_id, UserPlaytime.last_played.isnot(None))
        .order_by(UserPlaytime.last_played.desc())
        .limit(limit)
    )
    
    results = session.exec(statement).all()
    
    return [
        GameWithPlaytime(
            id=game.id,
            title=game.title,
            cover_url=game.cover_url,
            total_minutes=playtime.total_minutes,
            last_played=playtime.last_played,
            sessions_count=playtime.sessions_count
        )
        for playtime, game in results
    ]
