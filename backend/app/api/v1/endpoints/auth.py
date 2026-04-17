"""
Authentication API endpoints.
"""
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select
from pydantic import BaseModel

from app.core.db import get_session
from app.core.security import (
    verify_password, hash_password, 
    create_access_token, create_refresh_token, decode_token,
    create_token_payload, ACCESS_TOKEN_EXPIRE_MINUTES
)
from app.core.auth import get_current_user, get_current_user_optional
from app.models.user import (
    User, UserCreate, UserRead, UserReadPrivate,
    UserSession
)
from app.models.config import SystemConfig, get_config_bool

router = APIRouter()

# ============================================================
# Request/Response Schemas
# ============================================================

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = ACCESS_TOKEN_EXPIRE_MINUTES * 60  # seconds

class RefreshRequest(BaseModel):
    refresh_token: str

class MessageResponse(BaseModel):
    message: str

# ============================================================
# Auth Endpoints
# ============================================================

@router.post("/login", response_model=TokenResponse)
async def login(
    credentials: LoginRequest,
    request: Request,
    session: Session = Depends(get_session)
):
    """
    Authenticate user and return access/refresh tokens.
    """
    # Find user by username
    statement = select(User).where(User.username == credentials.username)
    user = session.exec(statement).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    # Verify password
    if not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    
    # Update last login
    user.last_login = datetime.now(timezone.utc)
    session.add(user)
    session.commit()
    
    # Create tokens
    token_data = create_token_payload(user.id, user.username, user.is_admin)
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    
    # Optionally store session in database for tracking
    # (enables logout and session management)
    user_session = UserSession(
        user_id=user.id,
        token=access_token[:64],  # Store truncated token as identifier
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent", "")[:500]
    )
    session.add(user_session)
    session.commit()
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token
    )

@router.post("/logout", response_model=MessageResponse)
async def logout(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Logout current user (invalidate current session).
    In a stateless JWT system, this mainly clears server-side session records.
    Client should also discard the token.
    """
    # Delete user's sessions from database
    statement = select(UserSession).where(UserSession.user_id == current_user.id)
    sessions = session.exec(statement).all()
    for s in sessions:
        session.delete(s)
    session.commit()
    
    return MessageResponse(message="Successfully logged out")

@router.get("/me", response_model=UserReadPrivate)
async def get_me(
    current_user: User = Depends(get_current_user)
):
    """
    Get current user's profile (private view with email).
    """
    return current_user

@router.post("/register", response_model=UserRead)
async def register(
    user_data: UserCreate,
    session: Session = Depends(get_session)
):
    """
    Register a new user account.
    Only works if registration is enabled in system config.
    """
    # Check if registration is enabled
    config = session.get(SystemConfig, "allow_registration")
    if config and not get_config_bool(config.value):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User registration is currently disabled"
        )
    
    # Check if username already exists
    existing = session.exec(
        select(User).where(User.username == user_data.username)
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )
    
    # Check if email already exists (if provided)
    if user_data.email:
        existing_email = session.exec(
            select(User).where(User.email == user_data.email)
        ).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
    
    # Create new user
    new_user = User(
        username=user_data.username,
        display_name=user_data.display_name or user_data.username,
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        is_admin=False,
        is_active=True
    )
    
    session.add(new_user)
    session.commit()
    session.refresh(new_user)
    
    return new_user

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_data: RefreshRequest,
    session: Session = Depends(get_session)
):
    """
    Refresh access token using a valid refresh token.
    """
    payload = decode_token(refresh_data.refresh_token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )
    
    # Verify it's a refresh token
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type"
        )
    
    # Get user
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    try:
        user_id = int(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID in token"
        )
    
    user = session.get(User, user_id)
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    # Create new tokens
    token_data = create_token_payload(user.id, user.username, user.is_admin)
    new_access_token = create_access_token(token_data)
    new_refresh_token = create_refresh_token(token_data)
    
    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token
    )

# ============================================================
# Password Management
# ============================================================

class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str

@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    password_data: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Change current user's password.
    """
    # Verify current password
    if not verify_password(password_data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Update password
    current_user.password_hash = hash_password(password_data.new_password)
    session.add(current_user)
    session.commit()
    
    return MessageResponse(message="Password updated successfully")
