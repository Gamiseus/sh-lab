"""
Security utilities for password hashing and JWT token management.
"""
from datetime import datetime, timedelta
from typing import Optional, Any
import bcrypt
from jose import JWTError, jwt
import secrets

# JWT Configuration
# In production, load from environment/config
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours
REFRESH_TOKEN_EXPIRE_DAYS = 7

def get_jwt_secret() -> str:
    """
    Get or generate JWT secret.
    In production, this should be loaded from environment/database.
    """
    # TODO: Load from system_config table or environment
    # For now, use a static secret (CHANGE IN PRODUCTION)
    import os
    secret = os.environ.get("JWT_SECRET")
    if not secret:
        # Fallback - in production this should fail or auto-generate and persist
        secret = "sh-lab-dev-secret-change-in-production-abc123"
    return secret

# ============================================================
# Password Hashing (using bcrypt directly)
# ============================================================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    try:
        return bcrypt.checkpw(
            plain_password.encode('utf-8'), 
            hashed_password.encode('utf-8')
        )
    except Exception:
        return False

def hash_password(password: str) -> str:
    """Hash a password for storage."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

# ============================================================
# JWT Token Management
# ============================================================

def create_access_token(
    data: dict, 
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: Payload data (should include 'sub' for user identifier)
        expires_delta: Optional custom expiration time
    
    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    })
    
    encoded_jwt = jwt.encode(to_encode, get_jwt_secret(), algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict) -> str:
    """
    Create a longer-lived refresh token.
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh"
    })
    
    encoded_jwt = jwt.encode(to_encode, get_jwt_secret(), algorithm=ALGORITHM)
    return encoded_jwt

def decode_token(token: str) -> Optional[dict]:
    """
    Decode and verify a JWT token.
    
    Returns:
        Decoded payload if valid, None if invalid/expired
    """
    try:
        payload = jwt.decode(token, get_jwt_secret(), algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

def generate_session_token() -> str:
    """Generate a secure random session token."""
    return secrets.token_urlsafe(32)

# ============================================================
# Token Payload Helpers
# ============================================================

def create_token_payload(user_id: int, username: str, is_admin: bool = False) -> dict:
    """Create the standard payload for user tokens."""
    return {
        "sub": str(user_id),
        "username": username,
        "is_admin": is_admin
    }

def get_user_id_from_token(token: str) -> Optional[int]:
    """Extract user ID from a valid token."""
    payload = decode_token(token)
    if payload:
        try:
            return int(payload.get("sub"))
        except (ValueError, TypeError):
            return None
    return None
