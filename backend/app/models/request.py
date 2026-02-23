from typing import Optional
from sqlmodel import Field, SQLModel
from datetime import datetime

class GameRequestBase(SQLModel):
    game_name: str = Field(max_length=255)
    platform: Optional[str] = Field(default=None, max_length=50)  # 'steam', 'gog', 'itch', 'epic', 'other'
    steam_app_id: Optional[int] = None
    external_url: Optional[str] = None
    notes: Optional[str] = None

class GameRequest(GameRequestBase, table=True):
    __tablename__ = "game_requests"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    requester_id: int = Field(foreign_key="users.id")
    status: str = Field(default="pending")  # 'pending', 'approved', 'rejected', 'completed', 'duplicate'
    priority: int = Field(default=0)
    admin_notes: Optional[str] = None
    assigned_game_id: Optional[int] = Field(default=None, foreign_key="game.id")
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[int] = Field(default=None, foreign_key="users.id")

class GameRequestCreate(SQLModel):
    """Schema for creating a game request"""
    game_name: str
    platform: Optional[str] = None
    steam_app_id: Optional[int] = None
    external_url: Optional[str] = None
    notes: Optional[str] = None

class GameRequestUpdate(SQLModel):
    """Schema for admin updating a request"""
    status: Optional[str] = None
    priority: Optional[int] = None
    admin_notes: Optional[str] = None
    assigned_game_id: Optional[int] = None

class GameRequestRead(GameRequestBase):
    """Schema for reading a request"""
    id: int
    requester_id: int
    status: str
    priority: int
    created_at: Optional[datetime]
    resolved_at: Optional[datetime]

class GameRequestReadAdmin(GameRequestRead):
    """Admin view with extra fields"""
    admin_notes: Optional[str]
    assigned_game_id: Optional[int]
    resolved_by: Optional[int]
