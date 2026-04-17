from typing import Optional
from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from pydantic import BaseModel
from app.core.db import get_session
from app.core.auth import require_admin
from app.models.user import User
from app.models.config import SystemConfig

router = APIRouter()


class SettingsRead(BaseModel):
    igdb_client_id: Optional[str] = None
    igdb_client_secret: Optional[str] = None
    library_path: Optional[str] = None


class SettingsUpdate(BaseModel):
    igdb_client_id: Optional[str] = None
    igdb_client_secret: Optional[str] = None


def _get_config_value(session: Session, key: str) -> Optional[str]:
    """Get a config value by key from the key-value SystemConfig table."""
    cfg = session.get(SystemConfig, key)
    return cfg.value if cfg else None


def _set_config_value(
    session: Session, key: str, value: str, description: str,
    is_secret: bool = False, admin_id: Optional[int] = None
):
    """Set a config value, creating the row if it doesn't exist."""
    cfg = session.get(SystemConfig, key)
    if cfg:
        cfg.value = value
        cfg.updated_by = admin_id
        session.add(cfg)
    else:
        session.add(SystemConfig(
            key=key,
            value=value,
            value_type="string",
            description=description,
            is_secret=is_secret,
            updated_by=admin_id,
        ))


@router.get("/", response_model=SettingsRead)
def get_settings(
    session: Session = Depends(get_session),
    admin: User = Depends(require_admin),
):
    """Get system settings (admin only)."""
    return SettingsRead(
        igdb_client_id=_get_config_value(session, "igdb_client_id"),
        igdb_client_secret=_get_config_value(session, "igdb_client_secret"),
        library_path=_get_config_value(session, "library_path") or "/data/games",
    )


@router.put("/", response_model=SettingsRead)
def update_settings(
    settings_in: SettingsUpdate,
    session: Session = Depends(get_session),
    admin: User = Depends(require_admin),
):
    """Update system settings (admin only)."""
    if settings_in.igdb_client_id is not None:
        _set_config_value(
            session, "igdb_client_id", settings_in.igdb_client_id,
            "IGDB Client ID", is_secret=False, admin_id=admin.id,
        )
    if settings_in.igdb_client_secret is not None:
        _set_config_value(
            session, "igdb_client_secret", settings_in.igdb_client_secret,
            "IGDB Client Secret", is_secret=True, admin_id=admin.id,
        )

    session.commit()

    return SettingsRead(
        igdb_client_id=_get_config_value(session, "igdb_client_id"),
        igdb_client_secret=_get_config_value(session, "igdb_client_secret"),
        library_path=_get_config_value(session, "library_path") or "/data/games",
    )
