"""
Database models for user library tracking and server depot cache management.
"""
from typing import Optional
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class UserLibrary(SQLModel, table=True):
    __tablename__ = "user_library"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    game_id: int = Field(index=True)
    status: str = Field(default="uninstalled")  # 'uninstalled', 'installing', 'installed'
    added_at: datetime = Field(default_factory=utc_now)
    installed_at: Optional[datetime] = None
    last_updated: datetime = Field(default_factory=utc_now)

UserLibraryEntry = UserLibrary

class ServerGameCache(SQLModel, table=True):
    __tablename__ = "server_game_cache"
    id: Optional[int] = Field(default=None, primary_key=True)
    game_id: int = Field(index=True, unique=True)
    title: str = Field(index=True)
    steam_app_id: Optional[int] = Field(default=None, index=True)
    cached_size_bytes: int = Field(default=0)
    is_cached: bool = Field(default=False)
    build_id: Optional[str] = None
    latest_build_id: Optional[str] = None
    last_check: Optional[datetime] = None
    orphaned_at: Optional[datetime] = None
    cached_at: Optional[datetime] = None
    purged_at: Optional[datetime] = None
    updated_at: datetime = Field(default_factory=utc_now)
