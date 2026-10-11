from typing import Optional
from sqlmodel import Field, SQLModel
from datetime import datetime, timezone

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class SystemConfig(SQLModel, table=True):
    __tablename__ = "system_config"
    
    key: str = Field(primary_key=True, max_length=100)
    value: Optional[str] = None
    value_type: str = Field(default="string")  # 'string', 'number', 'boolean', 'json'
    description: Optional[str] = None
    is_secret: bool = Field(default=False)
    updated_at: Optional[datetime] = Field(default_factory=utc_now)
    updated_by: Optional[int] = Field(default=None, foreign_key="users.id")

class SystemConfigRead(SQLModel):
    """Public config (excludes secret values)"""
    key: str
    value: Optional[str]
    value_type: str
    description: Optional[str]
    is_secret: bool

class SystemConfigUpdate(SQLModel):
    """Schema for updating a config value"""
    value: str

# Helper functions for typed access
def get_config_bool(value: Optional[str]) -> bool:
    """Convert config string to boolean"""
    if value is None:
        return False
    return value.lower() in ('true', '1', 'yes', 'on')

def get_config_int(value: Optional[str], default: int = 0) -> int:
    """Convert config string to integer"""
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default
