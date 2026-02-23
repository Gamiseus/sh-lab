import os
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "sh_lab Backend"
    API_V1_STR: str = "/api/v1"
    
    # Database
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "admin")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "admin")
    POSTGRES_SERVER: str = os.getenv("POSTGRES_SERVER", "db")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "sh-lab")
    
    # IGDB
    IGDB_CLIENT_ID: str = os.getenv("IGDB_CLIENT_ID", "")
    IGDB_CLIENT_SECRET: str = os.getenv("IGDB_CLIENT_SECRET", "")
    
    # Steam Credentials (optional - falls back to DB config if not set)
    STEAM_USERNAME: Optional[str] = os.getenv("STEAM_USERNAME")
    STEAM_PASSWORD: Optional[str] = os.getenv("STEAM_PASSWORD")
    STEAM_WEB_API_KEY: Optional[str] = os.getenv("STEAM_WEB_API_KEY")
    
    # Data paths
    GAMES_REPO_PATH: str = os.getenv("GAMES_REPO_PATH", "/data/repo")
    DATA_DIR: str = os.getenv("DATA_DIR", "/data")
    
    # SteamCMD path - defaults to ./steamcmd (auto-installed by backend)
    # Not exposed in .env since it auto-installs to known location
    STEAMCMD_PATH: str = os.getenv("STEAMCMD_PATH", "./steamcmd")
    
    # JWT/Auth
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
    
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        
    class Config:
        case_sensitive = True

settings = Settings()
