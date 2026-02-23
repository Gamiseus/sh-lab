"""
Authentication dependencies for FastAPI routes.
"""
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel import Session, select

from app.core.db import get_session
from app.core.security import decode_token
from app.models.user import User

# Security scheme for Bearer token auth
security = HTTPBearer(auto_error=False)

# ============================================================
# User Retrieval
# ============================================================

async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    session: Session = Depends(get_session)
) -> Optional[User]:
    """
    Get the current user if a valid token is provided.
    Returns None if no token or invalid token (doesn't raise error).
    Use this for routes that work with or without auth.
    """
    if not credentials:
        return None
    
    token = credentials.credentials
    payload = decode_token(token)
    
    if not payload:
        return None
    
    user_id = payload.get("sub")
    if not user_id:
        return None
    
    try:
        user_id = int(user_id)
    except ValueError:
        return None
    
    user = session.get(User, user_id)
    
    if not user or not user.is_active:
        return None
    
    return user

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: Session = Depends(get_session)
) -> User:
    """
    Get the current authenticated user.
    Raises 401 if not authenticated or token invalid.
    Use this for routes that require authentication.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if not credentials:
        raise credentials_exception
    
    token = credentials.credentials
    payload = decode_token(token)
    
    if not payload:
        raise credentials_exception
    
    user_id = payload.get("sub")
    if not user_id:
        raise credentials_exception
    
    try:
        user_id = int(user_id)
    except ValueError:
        raise credentials_exception
    
    user = session.get(User, user_id)
    
    if not user:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    
    return user

async def require_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Require the current user to be an admin.
    Raises 403 if user is not an admin.
    Use this for admin-only routes.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user

# ============================================================
# Convenience Type Aliases
# ============================================================

# For route signatures
CurrentUser = User
CurrentAdmin = User

# Example usage in routes:
# @router.get("/protected")
# async def protected_route(user: User = Depends(get_current_user)):
#     return {"user_id": user.id}
#
# @router.get("/admin-only")
# async def admin_route(admin: User = Depends(require_admin)):
#     return {"admin_id": admin.id}
