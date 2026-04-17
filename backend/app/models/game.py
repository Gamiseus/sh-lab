from typing import Optional, List, Dict, Any
from sqlmodel import Field, SQLModel, Column
from sqlalchemy import Text
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from datetime import datetime

class GameBase(SQLModel):
    title: str = Field(index=True)
    description: Optional[str] = None
    
    # Short descriptions
    short_description: Optional[str] = None
    about_the_game: Optional[str] = None
    
    # Metadata
    developer: Optional[str] = None
    publisher: Optional[str] = None
    release_date: Optional[str] = None  # Changed to string for flexibility
    
    # Stats (legacy - now tracked per-user in user_playtime)
    playtime_minutes: int = Field(default=0)
    last_played: Optional[datetime] = None
    
    # External IDs
    igdb_id: Optional[int] = None
    steam_app_id: Optional[int] = None
    
    # Content
    summary: Optional[str] = None
    rating: Optional[float] = None
    cover_url: Optional[str] = None
    background_url: Optional[str] = None
    trailer_url: Optional[str] = None
    
    # Image URLs
    header_image: Optional[str] = None
    capsule_image: Optional[str] = None
    
    # Categorization (stored as PostgreSQL arrays)
    genres: Optional[List[str]] = Field(default=None, sa_column=Column(ARRAY(Text)))
    tags: Optional[List[str]] = Field(default=None, sa_column=Column(ARRAY(Text)))
    
    # Categories (Steam categories like "Co-op", "Steam Workshop")
    categories: Optional[List[Dict[str, Any]]] = Field(default=None, sa_column=Column(JSONB))
    
    # Platforms
    platforms: Optional[Dict[str, bool]] = Field(default=None, sa_column=Column(JSONB))
    
    # Media (JSONB arrays)
    screenshots: Optional[List[Dict[str, Any]]] = Field(default=None, sa_column=Column(JSONB))
    movies: Optional[List[Dict[str, Any]]] = Field(default=None, sa_column=Column(JSONB))
    
    # Metacritic
    metacritic_score: Optional[int] = None
    metacritic_url: Optional[str] = None
    
    # Achievements
    achievements_total: Optional[int] = None
    achievements_highlighted: Optional[List[Dict[str, Any]]] = Field(default=None, sa_column=Column(JSONB))
    
    # System Requirements (HTML strings)
    pc_requirements: Optional[str] = None
    mac_requirements: Optional[str] = None
    linux_requirements: Optional[str] = None
    
    # Steam Reviews
    steam_review_count: Optional[int] = None
    steam_review_percent: Optional[int] = None
    
    # Price
    price_cents: Optional[int] = None
    discount_percent: Optional[int] = Field(default=0)
    
    # Source & Version
    source: Optional[str] = Field(default="manual")  # 'manual', 'steam', 'torrent'
    version: Optional[str] = None
    
    # Launch Configuration
    executable_path: Optional[str] = None
    launch_args: Optional[str] = None
    
    # Size
    size_bytes: Optional[int] = None
    
    # Timestamps
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)

class Game(GameBase, table=True):
    __tablename__ = "game"
    id: Optional[int] = Field(default=None, primary_key=True)

class GameCreate(SQLModel):
    """Schema for creating a new game (minimal required fields)"""
    title: str
    description: Optional[str] = None
    source: Optional[str] = "manual"
    steam_app_id: Optional[int] = None

class GameUpdate(SQLModel):
    """Schema for updating a game (all fields optional)"""
    title: Optional[str] = None
    description: Optional[str] = None
    short_description: Optional[str] = None
    about_the_game: Optional[str] = None
    developer: Optional[str] = None
    publisher: Optional[str] = None
    release_date: Optional[str] = None
    igdb_id: Optional[int] = None
    steam_app_id: Optional[int] = None
    summary: Optional[str] = None
    rating: Optional[float] = None
    cover_url: Optional[str] = None
    background_url: Optional[str] = None
    trailer_url: Optional[str] = None
    header_image: Optional[str] = None
    capsule_image: Optional[str] = None
    genres: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    categories: Optional[List[Dict[str, Any]]] = None
    platforms: Optional[Dict[str, bool]] = None
    screenshots: Optional[List[Dict[str, Any]]] = None
    movies: Optional[List[Dict[str, Any]]] = None
    metacritic_score: Optional[int] = None
    metacritic_url: Optional[str] = None
    achievements_total: Optional[int] = None
    achievements_highlighted: Optional[List[Dict[str, Any]]] = None
    pc_requirements: Optional[str] = None
    mac_requirements: Optional[str] = None
    linux_requirements: Optional[str] = None
    steam_review_count: Optional[int] = None
    steam_review_percent: Optional[int] = None
    price_cents: Optional[int] = None
    discount_percent: Optional[int] = None
    source: Optional[str] = None
    version: Optional[str] = None
    executable_path: Optional[str] = None
    launch_args: Optional[str] = None
    size_bytes: Optional[int] = None

class GameRead(GameBase):
    """Schema for reading a game (includes ID)"""
    id: int
