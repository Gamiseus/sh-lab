from typing import Optional, List
from sqlmodel import Field, SQLModel, Column
from sqlalchemy import ARRAY, Text, Integer
from datetime import datetime

class UserBase(SQLModel):
    username: str = Field(unique=True, index=True, max_length=50)
    display_name: Optional[str] = Field(default=None, max_length=100)
    email: Optional[str] = Field(default=None, unique=True, max_length=255)
    is_admin: bool = Field(default=False)
    is_active: bool = Field(default=True)
    
    # Profile
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    background_url: Optional[str] = None
    privacy_level: str = Field(default="public")  # 'public', 'friends', 'private'
    favorite_game_ids: List[int] = Field(default=[], sa_column=Column(ARRAY(Integer)))

class User(UserBase, table=True):
    __tablename__ = "users"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    password_hash: str = Field(max_length=255)
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None

class UserCreate(SQLModel):
    """Schema for creating a new user"""
    username: str
    password: str  # Plain text, will be hashed
    email: Optional[str] = None
    display_name: Optional[str] = None

class UserUpdate(SQLModel):
    """Schema for updating user profile"""
    display_name: Optional[str] = None
    email: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    background_url: Optional[str] = None
    privacy_level: Optional[str] = None
    favorite_game_ids: Optional[List[int]] = None

class UserPasswordUpdate(SQLModel):
    """Schema for changing password"""
    current_password: str
    new_password: str

class UserRead(SQLModel):
    """Public user data (excludes password_hash)"""
    id: int
    username: str
    display_name: Optional[str]
    is_admin: bool
    avatar_url: Optional[str]
    bio: Optional[str]
    background_url: Optional[str]
    privacy_level: str
    created_at: Optional[datetime]

class UserReadPrivate(UserRead):
    """Private user data (includes email, for own profile)"""
    email: Optional[str]
    is_active: bool
    last_login: Optional[datetime]

# Session model
class UserSession(SQLModel, table=True):
    __tablename__ = "user_sessions"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    token: str = Field(unique=True, max_length=255, index=True)
    expires_at: datetime
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    ip_address: Optional[str] = Field(default=None, max_length=45)
    user_agent: Optional[str] = None

# User Settings model
class UserSettings(SQLModel, table=True):
    __tablename__ = "user_settings"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", unique=True)
    library_paths: Optional[List[str]] = Field(default=None, sa_column=Column(ARRAY(Text)))
    download_path: Optional[str] = None
    auto_update_games: bool = Field(default=True)
    notifications_enabled: bool = Field(default=True)
    # settings_json handled separately if needed
