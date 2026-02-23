from typing import Optional
from sqlmodel import Field, SQLModel

class SystemConfig(SQLModel, table=True):
    id: int = Field(default=1, primary_key=True)
    igdb_client_id: Optional[str] = None
    igdb_client_secret: Optional[str] = None
    library_path: Optional[str] = "/data/games"

class SystemConfigRead(SQLModel):
    igdb_client_id: Optional[str]
    igdb_client_secret: Optional[str]
    library_path: Optional[str]

class SystemConfigUpdate(SQLModel):
    igdb_client_id: Optional[str] = None
    igdb_client_secret: Optional[str] = None
