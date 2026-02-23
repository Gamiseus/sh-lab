from typing import Optional, List, Dict, Any
from sqlmodel import Field, SQLModel, Column
from sqlalchemy import ARRAY, Text
from datetime import datetime

class DedicatedServerBase(SQLModel):
    name: str = Field(max_length=100)
    description: Optional[str] = None
    folder_path: str
    executable_path: str
    launch_command: Optional[str] = None
    working_directory: Optional[str] = None
    config_files: Optional[List[str]] = Field(default=None, sa_column=Column(ARRAY(Text)))
    allow_user_start: bool = Field(default=False)
    auto_restart: bool = Field(default=False)
    max_players: Optional[int] = None

class DedicatedServer(DedicatedServerBase, table=True):
    __tablename__ = "dedicated_servers"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    game_id: Optional[int] = Field(default=None, foreign_key="game.id")
    is_running: bool = Field(default=False)
    current_players: int = Field(default=0)
    last_started: Optional[datetime] = None
    last_stopped: Optional[datetime] = None
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    # environment_vars stored as JSONB, handle separately if needed

class DedicatedServerCreate(SQLModel):
    """Schema for creating a server"""
    name: str
    game_id: Optional[int] = None
    folder_path: str
    executable_path: str
    launch_command: Optional[str] = None
    working_directory: Optional[str] = None
    config_files: Optional[List[str]] = None
    allow_user_start: bool = False
    auto_restart: bool = False
    max_players: Optional[int] = None

class DedicatedServerUpdate(SQLModel):
    """Schema for updating a server"""
    name: Optional[str] = None
    description: Optional[str] = None
    game_id: Optional[int] = None
    folder_path: Optional[str] = None
    executable_path: Optional[str] = None
    launch_command: Optional[str] = None
    working_directory: Optional[str] = None
    config_files: Optional[List[str]] = None
    allow_user_start: Optional[bool] = None
    auto_restart: Optional[bool] = None
    max_players: Optional[int] = None

class DedicatedServerRead(DedicatedServerBase):
    """Schema for reading a server"""
    id: int
    game_id: Optional[int]
    is_running: bool
    current_players: int
    last_started: Optional[datetime]
    created_at: Optional[datetime]

class DedicatedServerStatus(SQLModel):
    """Runtime status info"""
    id: int
    name: str
    is_running: bool
    current_players: int
    max_players: Optional[int]
    uptime_seconds: Optional[int] = None
