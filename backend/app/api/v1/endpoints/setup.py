"""
Setup API endpoints for first-run configuration.
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from pydantic import BaseModel

from app.core.db import get_session
from app.core.security import hash_password, create_access_token
from app.core.config import settings
from app.models.user import User
from app.models.config import SystemConfig

router = APIRouter()

class SetupCheckResponse(BaseModel):
    setup_complete: bool
    has_admin: bool
    # Let frontend know which fields are already configured via env vars
    steam_username_configured: bool = False
    steam_password_configured: bool = False
    steam_api_key_configured: bool = False

class SetupRequest(BaseModel):
    # Admin account
    username: str
    password: str
    email: Optional[str] = None
    
    # Steam credentials (optional - may already be set via env vars)
    steam_api_key: Optional[str] = None
    steam_username: Optional[str] = None
    steam_password: Optional[str] = None

class SetupResponse(BaseModel):
    success: bool
    message: str
    access_token: Optional[str] = None

@router.get("/check", response_model=SetupCheckResponse)
async def check_setup_status(session: Session = Depends(get_session)):
    """
    Check if initial setup has been completed.
    Returns setup status so frontend can show setup wizard if needed.
    Also indicates which fields are pre-configured via environment variables.
    """
    # Check setup_complete flag
    config = session.get(SystemConfig, "setup_complete")
    setup_complete = config.value.lower() == "true" if config else False
    
    # Check if any admin user exists
    admin_count = session.exec(
        select(User).where(User.is_admin == True)
    ).first()
    has_admin = admin_count is not None
    
    # Check what's already configured via env vars
    steam_username_configured = bool(settings.STEAM_USERNAME)
    steam_password_configured = bool(settings.STEAM_PASSWORD)
    steam_api_key_configured = bool(settings.STEAM_WEB_API_KEY)
    
    return SetupCheckResponse(
        setup_complete=setup_complete,
        has_admin=has_admin,
        steam_username_configured=steam_username_configured,
        steam_password_configured=steam_password_configured,
        steam_api_key_configured=steam_api_key_configured
    )

@router.post("/complete", response_model=SetupResponse)
async def complete_setup(
    data: SetupRequest,
    session: Session = Depends(get_session)
):
    """
    Complete the initial setup.
    Creates admin account and stores Steam credentials (if not already in env).
    """
    # Check if setup already complete
    config = session.get(SystemConfig, "setup_complete")
    if config and config.value.lower() == "true":
        raise HTTPException(
            status_code=400,
            detail="Setup has already been completed"
        )
    
    # Check if username already exists
    existing_user = session.exec(
        select(User).where(User.username == data.username)
    ).first()
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Username already exists"
        )
    
    # Create admin user
    admin_user = User(
        username=data.username,
        password_hash=hash_password(data.password),
        email=data.email,
        is_admin=True,
        is_active=True
    )
    session.add(admin_user)
    
    # Store Steam API key if provided AND not already in env
    if data.steam_api_key and not settings.STEAM_WEB_API_KEY:
        api_key_config = session.get(SystemConfig, "steam_api_key")
        if api_key_config:
            api_key_config.value = data.steam_api_key
            session.add(api_key_config)
        else:
            session.add(SystemConfig(
                key="steam_api_key",
                value=data.steam_api_key,
                value_type="string",
                description="Steam Web API Key",
                is_secret=True
            ))
    
    # Store Steam credentials if provided AND not already in env
    if data.steam_username and not settings.STEAM_USERNAME:
        steam_user_config = session.get(SystemConfig, "steam_username")
        if steam_user_config:
            steam_user_config.value = data.steam_username
            session.add(steam_user_config)
        else:
            session.add(SystemConfig(
                key="steam_username",
                value=data.steam_username,
                value_type="string",
                description="Steam account username",
                is_secret=False
            ))
    
    if data.steam_password and not settings.STEAM_PASSWORD:
        steam_pass_config = session.get(SystemConfig, "steam_password")
        if steam_pass_config:
            steam_pass_config.value = data.steam_password
            session.add(steam_pass_config)
        else:
            session.add(SystemConfig(
                key="steam_password",
                value=data.steam_password,
                value_type="string",
                description="Steam account password",
                is_secret=True
            ))
    
    # Mark setup as complete
    setup_config = session.get(SystemConfig, "setup_complete")
    if setup_config:
        setup_config.value = "true"
        session.add(setup_config)
    else:
        session.add(SystemConfig(
            key="setup_complete",
            value="true",
            value_type="bool",
            description="First-run setup completed"
        ))
    
    session.commit()
    session.refresh(admin_user)
    
    # Generate access token for auto-login
    access_token = create_access_token(data={"sub": str(admin_user.id)})
    
    return SetupResponse(
        success=True,
        message=f"Setup complete! Admin user '{data.username}' created.",
        access_token=access_token
    )

@router.post("/reset")
async def reset_setup(session: Session = Depends(get_session)):
    """
    Reset setup status (for development/testing only).
    In production, this should be removed or protected.
    """
    config = session.get(SystemConfig, "setup_complete")
    if config:
        config.value = "false"
        session.add(config)
        session.commit()
    
    return {"status": "reset", "message": "Setup status reset to false"}
