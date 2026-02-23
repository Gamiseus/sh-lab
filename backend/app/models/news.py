from typing import Optional, List
from sqlmodel import Field, SQLModel, Column
from sqlalchemy import Text
from sqlalchemy.dialects.postgresql import ARRAY
from datetime import datetime

class NewsPostBase(SQLModel):
    title: str = Field(max_length=255)
    slug: Optional[str] = Field(default=None, unique=True, max_length=255)
    content: str  # Markdown
    excerpt: Optional[str] = None
    cover_image_url: Optional[str] = None
    is_pinned: bool = Field(default=False)
    tags: Optional[List[str]] = Field(default=None, sa_column=Column(ARRAY(Text)))

class NewsPost(NewsPostBase, table=True):
    __tablename__ = "news_posts"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    author_id: Optional[int] = Field(default=None, foreign_key="users.id")
    is_published: bool = Field(default=False)
    published_at: Optional[datetime] = None
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

class NewsPostCreate(SQLModel):
    """Schema for creating a news post"""
    title: str
    content: str
    excerpt: Optional[str] = None
    cover_image_url: Optional[str] = None
    is_pinned: bool = False
    tags: Optional[List[str]] = None

class NewsPostUpdate(SQLModel):
    """Schema for updating a news post"""
    title: Optional[str] = None
    content: Optional[str] = None
    excerpt: Optional[str] = None
    cover_image_url: Optional[str] = None
    is_pinned: Optional[bool] = None
    tags: Optional[List[str]] = None

class NewsPostRead(NewsPostBase):
    """Schema for reading a news post"""
    id: int
    author_id: Optional[int]
    is_published: bool
    published_at: Optional[datetime]
    created_at: Optional[datetime]

class NewsPostReadWithAuthor(NewsPostRead):
    """News post with author info"""
    author_username: Optional[str]
    author_display_name: Optional[str]
