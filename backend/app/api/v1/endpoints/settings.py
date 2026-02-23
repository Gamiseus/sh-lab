from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from app.core.db import get_session
from app.models.system_config import SystemConfig, SystemConfigRead, SystemConfigUpdate

router = APIRouter()

@router.get("/", response_model=SystemConfigRead)
def get_settings(session: Session = Depends(get_session)):
    config = session.exec(select(SystemConfig).where(SystemConfig.id == 1)).first()
    if not config:
        # Create default if not exists
        config = SystemConfig(id=1)
        session.add(config)
        session.commit()
        session.refresh(config)
    return config

@router.put("/", response_model=SystemConfigRead)
def update_settings(
    settings_in: SystemConfigUpdate,
    session: Session = Depends(get_session)
):
    config = session.exec(select(SystemConfig).where(SystemConfig.id == 1)).first()
    if not config:
        config = SystemConfig(id=1)
        session.add(config)
    
    if settings_in.igdb_client_id is not None:
        config.igdb_client_id = settings_in.igdb_client_id
    if settings_in.igdb_client_secret is not None:
        config.igdb_client_secret = settings_in.igdb_client_secret
        
    session.add(config)
    session.commit()
    session.refresh(config)
    return config
