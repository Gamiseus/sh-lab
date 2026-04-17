"""
Reviews API endpoints.
"""
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select, func
from pydantic import BaseModel

from app.core.db import get_session
from app.core.auth import get_current_user, get_current_user_optional, require_admin
from app.models.user import User
from app.models.game import Game
from app.models.review import Review, ReviewCreate, ReviewUpdate
from app.models.social import UserPlaytime

router = APIRouter()

# ============================================================
# Response Schemas
# ============================================================

class ReviewWithUser(BaseModel):
    id: int
    user_id: int
    game_id: int
    content: str
    rating: int
    is_recommended: Optional[bool]
    playtime_at_review: Optional[int]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    is_hidden: bool = False
    # User info
    username: str
    display_name: Optional[str]
    avatar_url: Optional[str]

class ReviewStats(BaseModel):
    total_reviews: int
    average_rating: float
    recommend_percent: Optional[float]
    rating_distribution: dict  # {1: count, 2: count, ...}

# ============================================================
# Public Endpoints
# ============================================================

@router.get("/games/{game_id}/reviews", response_model=List[ReviewWithUser])
async def get_game_reviews(
    game_id: int,
    sort_by: str = Query("recent", pattern="^(recent|rating|playtime)$"),
    limit: int = 50,
    offset: int = 0,
    session: Session = Depends(get_session)
):
    """
    Get all reviews for a game (public, excludes hidden reviews).
    """
    # Verify game exists
    game = session.get(Game, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    # Build query with user join
    statement = (
        select(Review, User)
        .join(User, User.id == Review.user_id)
        .where(Review.game_id == game_id)
        .where(Review.is_hidden == False)
    )
    
    # Sort
    if sort_by == "recent":
        statement = statement.order_by(Review.created_at.desc())
    elif sort_by == "rating":
        statement = statement.order_by(Review.rating.desc())
    elif sort_by == "playtime":
        statement = statement.order_by(Review.playtime_at_review.desc().nullslast())
    
    statement = statement.offset(offset).limit(limit)
    results = session.exec(statement).all()
    
    return [
        ReviewWithUser(
            id=review.id,
            user_id=review.user_id,
            game_id=review.game_id,
            content=review.content,
            rating=review.rating,
            is_recommended=review.is_recommended,
            playtime_at_review=review.playtime_at_review,
            created_at=review.created_at,
            updated_at=review.updated_at,
            username=user.username,
            display_name=user.display_name,
            avatar_url=user.avatar_url
        )
        for review, user in results
    ]

@router.get("/games/{game_id}/review-stats", response_model=ReviewStats)
async def get_game_review_stats(
    game_id: int,
    session: Session = Depends(get_session)
):
    """
    Get aggregate review statistics for a game.
    """
    # Verify game exists
    game = session.get(Game, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    # Get all visible reviews
    statement = select(Review).where(
        Review.game_id == game_id,
        Review.is_hidden == False
    )
    reviews = session.exec(statement).all()
    
    if not reviews:
        return ReviewStats(
            total_reviews=0,
            average_rating=0.0,
            recommend_percent=None,
            rating_distribution={1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        )
    
    # Calculate stats
    total = len(reviews)
    avg_rating = sum(r.rating for r in reviews) / total
    
    # Recommendation percentage
    recommended_count = sum(1 for r in reviews if r.is_recommended is True)
    not_recommended_count = sum(1 for r in reviews if r.is_recommended is False)
    if recommended_count + not_recommended_count > 0:
        recommend_percent = (recommended_count / (recommended_count + not_recommended_count)) * 100
    else:
        recommend_percent = None
    
    # Rating distribution
    distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for r in reviews:
        distribution[r.rating] = distribution.get(r.rating, 0) + 1
    
    return ReviewStats(
        total_reviews=total,
        average_rating=round(avg_rating, 2),
        recommend_percent=round(recommend_percent, 1) if recommend_percent else None,
        rating_distribution=distribution
    )

# ============================================================
# Authenticated Endpoints
# ============================================================

@router.post("/reviews", response_model=ReviewWithUser)
async def create_review(
    review_data: ReviewCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Create a review for a game. One review per user per game.
    """
    # Verify game exists
    game = session.get(Game, review_data.game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    # Check if user already reviewed this game
    existing = session.exec(
        select(Review).where(
            Review.user_id == current_user.id,
            Review.game_id == review_data.game_id
        )
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=400,
            detail="You have already reviewed this game. Edit your existing review instead."
        )
    
    # Get user's playtime for this game
    playtime_record = session.exec(
        select(UserPlaytime).where(
            UserPlaytime.user_id == current_user.id,
            UserPlaytime.game_id == review_data.game_id
        )
    ).first()
    
    playtime_at_review = playtime_record.total_minutes if playtime_record else 0
    
    # Create review
    review = Review(
        user_id=current_user.id,
        game_id=review_data.game_id,
        content=review_data.content,
        rating=review_data.rating,
        is_recommended=review_data.is_recommended,
        playtime_at_review=playtime_at_review,
        created_at=datetime.now(timezone.utc)
    )
    
    session.add(review)
    session.commit()
    session.refresh(review)
    
    return ReviewWithUser(
        id=review.id,
        user_id=review.user_id,
        game_id=review.game_id,
        content=review.content,
        rating=review.rating,
        is_recommended=review.is_recommended,
        playtime_at_review=review.playtime_at_review,
        created_at=review.created_at,
        updated_at=review.updated_at,
        username=current_user.username,
        display_name=current_user.display_name,
        avatar_url=current_user.avatar_url
    )

@router.get("/reviews/me", response_model=List[ReviewWithUser])
async def get_my_reviews(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Get all reviews written by the current user.
    """
    statement = (
        select(Review)
        .where(Review.user_id == current_user.id)
        .order_by(Review.created_at.desc())
    )
    reviews = session.exec(statement).all()
    
    return [
        ReviewWithUser(
            id=r.id,
            user_id=r.user_id,
            game_id=r.game_id,
            content=r.content,
            rating=r.rating,
            is_recommended=r.is_recommended,
            playtime_at_review=r.playtime_at_review,
            created_at=r.created_at,
            updated_at=r.updated_at,
            username=current_user.username,
            display_name=current_user.display_name,
            avatar_url=current_user.avatar_url
        )
        for r in reviews
    ]

@router.get("/games/{game_id}/my-review", response_model=Optional[ReviewWithUser])
async def get_my_review_for_game(
    game_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Get the current user's review for a specific game (if exists).
    """
    review = session.exec(
        select(Review).where(
            Review.user_id == current_user.id,
            Review.game_id == game_id
        )
    ).first()
    
    if not review:
        return None
    
    return ReviewWithUser(
        id=review.id,
        user_id=review.user_id,
        game_id=review.game_id,
        content=review.content,
        rating=review.rating,
        is_recommended=review.is_recommended,
        playtime_at_review=review.playtime_at_review,
        created_at=review.created_at,
        updated_at=review.updated_at,
        username=current_user.username,
        display_name=current_user.display_name,
        avatar_url=current_user.avatar_url
    )

@router.put("/reviews/{review_id}", response_model=ReviewWithUser)
async def update_review(
    review_id: int,
    review_data: ReviewUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Update your own review.
    """
    review = session.get(Review, review_id)
    
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    
    if review.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only edit your own reviews")
    
    # Update fields
    if review_data.content is not None:
        review.content = review_data.content
    if review_data.rating is not None:
        review.rating = review_data.rating
    if review_data.is_recommended is not None:
        review.is_recommended = review_data.is_recommended
    
    review.updated_at = datetime.now(timezone.utc)
    
    session.add(review)
    session.commit()
    session.refresh(review)
    
    return ReviewWithUser(
        id=review.id,
        user_id=review.user_id,
        game_id=review.game_id,
        content=review.content,
        rating=review.rating,
        is_recommended=review.is_recommended,
        playtime_at_review=review.playtime_at_review,
        created_at=review.created_at,
        updated_at=review.updated_at,
        username=current_user.username,
        display_name=current_user.display_name,
        avatar_url=current_user.avatar_url
    )

@router.delete("/reviews/{review_id}")
async def delete_review(
    review_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a review.
    Users can delete their own. Admins can delete any.
    """
    review = session.get(Review, review_id)
    
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    
    if review.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="You can only delete your own reviews")
    
    session.delete(review)
    session.commit()
    
    return {"message": "Review deleted successfully"}

# ============================================================
# Admin Endpoints
# ============================================================

@router.get("/admin/all", response_model=List[ReviewWithUser])
async def get_all_reviews_admin(
    page: int = 1,
    limit: int = 50,
    session: Session = Depends(get_session),
    admin: User = Depends(require_admin)
):
    """
    Admin: List all reviews (paginated).
    """
    offset = (page - 1) * limit
    
    statement = (
        select(Review, User)
        .join(User, User.id == Review.user_id)
        .order_by(Review.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    
    results = session.exec(statement).all()
    
    return [
        ReviewWithUser(
            id=review.id,
            user_id=review.user_id,
            game_id=review.game_id,
            content=review.content,
            rating=review.rating,
            is_recommended=review.is_recommended,
            playtime_at_review=review.playtime_at_review,
            created_at=review.created_at,
            updated_at=review.updated_at,
            username=user.username,
            display_name=user.display_name,
            avatar_url=user.avatar_url,
            is_hidden=review.is_hidden
        )
        for review, user in results
    ]

@router.put("/{review_id}/visibility")
async def toggle_review_visibility(
    review_id: int,
    is_hidden: bool,
    session: Session = Depends(get_session),
    admin: User = Depends(require_admin)
):
    """
    Admin: Hide or show a review.
    """
    review = session.get(Review, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
        
    review.is_hidden = is_hidden
    session.add(review)
    session.commit()
    session.refresh(review)
    
    return {"message": "Visibility updated", "is_hidden": review.is_hidden}

