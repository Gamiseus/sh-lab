from typing import Optional
from sqlmodel import Field, SQLModel
from datetime import datetime

# ============================================================
# User Playtime - Tracks per-user, per-game play statistics
# ============================================================

class UserPlaytime(SQLModel, table=True):
    __tablename__ = "user_playtime"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    game_id: int = Field(foreign_key="game.id")
    total_minutes: int = Field(default=0)
    last_played: Optional[datetime] = None
    last_session_minutes: int = Field(default=0)
    sessions_count: int = Field(default=0)
    first_played: Optional[datetime] = Field(default_factory=datetime.utcnow)

class UserPlaytimeRead(SQLModel):
    """Schema for reading playtime data"""
    user_id: int
    game_id: int
    total_minutes: int
    last_played: Optional[datetime]
    sessions_count: int

class UserPlaytimeUpdate(SQLModel):
    """Schema for syncing playtime from client"""
    game_id: int
    session_minutes: int
    session_end: datetime

# ============================================================
# Friendship - Tracks friend relationships between users
# ============================================================

class Friendship(SQLModel, table=True):
    __tablename__ = "friendships"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    friend_id: int = Field(foreign_key="users.id")
    status: str = Field(default="pending")  # 'pending', 'accepted', 'blocked'
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

class FriendshipCreate(SQLModel):
    """Schema for sending a friend request"""
    friend_id: int

class FriendshipUpdate(SQLModel):
    """Schema for updating friendship status"""
    status: str  # 'accepted', 'blocked'

class FriendshipRead(SQLModel):
    """Schema for reading a friendship"""
    id: int
    user_id: int
    friend_id: int
    status: str
    created_at: Optional[datetime]

class FriendRead(SQLModel):
    """Friend info for display"""
    id: int
    username: str
    display_name: Optional[str]
    avatar_url: Optional[str]
    status: str  # friendship status
    is_online: bool = False
    last_played_game: Optional[str] = None
