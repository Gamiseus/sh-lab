from typing import Optional
from sqlmodel import Field, SQLModel
from datetime import datetime, timezone

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class ReviewBase(SQLModel):
    content: str
    rating: int = Field(ge=1, le=5)  # 1-5 stars
    is_recommended: Optional[bool] = None
    game_version: Optional[str] = None

class Review(ReviewBase, table=True):
    __tablename__ = "reviews"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    game_id: int = Field(foreign_key="game.id")
    playtime_at_review: Optional[int] = None  # minutes
    is_hidden: bool = Field(default=False)
    created_at: Optional[datetime] = Field(default_factory=utc_now)
    updated_at: Optional[datetime] = None

class ReviewCreate(SQLModel):
    """Schema for creating a review"""
    game_id: int
    content: str
    rating: int = Field(ge=1, le=5)
    is_recommended: Optional[bool] = None

class ReviewUpdate(SQLModel):
    """Schema for updating a review"""
    content: Optional[str] = None
    rating: Optional[int] = Field(default=None, ge=1, le=5)
    is_recommended: Optional[bool] = None

class ReviewRead(ReviewBase):
    """Schema for reading a review"""
    id: int
    user_id: int
    game_id: int
    playtime_at_review: Optional[int]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

class ReviewReadWithUser(ReviewRead):
    """Review with user info for display"""
    username: str
    display_name: Optional[str]
    avatar_url: Optional[str]
