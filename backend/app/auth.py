"""
Simple username/password auth layer.
Users are hardcoded in AUTH_USERS dict. Add/remove as needed.
"""

import hashlib
import time
from fastapi import HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

# ─── Hardcoded users ────────────────────────────────────────────────
# Passwords are SHA-256 hashed. To add a new user:
#   python3 -c "import hashlib; print(hashlib.sha256('yourpassword'.encode()).hexdigest())"
# Then add the hex digest below.

AUTH_USERS = {
    "admin": {
        "password_hash": hashlib.sha256("admin123".encode()).hexdigest(),
        "display_name": "Admin",
        "role": "admin",
    },
    "advaid": {
        "password_hash": hashlib.sha256("deep2026".encode()).hexdigest(),
        "display_name": "Advaid",
        "role": "admin",
    },
    "demo": {
        "password_hash": hashlib.sha256("demo123".encode()).hexdigest(),
        "display_name": "Demo User",
        "role": "user",
    },
}

# ─── Simple token store (in-memory, good enough for single instance) ──
ACTIVE_TOKENS: dict[str, dict] = {}  # token -> {username, created_at}


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    username: str
    display_name: str
    role: str


def authenticate(username: str, password: str) -> dict:
    """Validate credentials. Returns user dict or raises."""
    user = AUTH_USERS.get(username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    if password_hash != user["password_hash"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    return user


def create_token(username: str) -> str:
    """Create a simple token (timestamp-based, not JWT — good enough for this use case)."""
    token = hashlib.sha256(f"{username}:{time.time()}:{username}".encode()).hexdigest()
    ACTIVE_TOKENS[token] = {
        "username": username,
        "created_at": time.time(),
    }
    return token


def verify_token(token: str) -> dict:
    """Verify token exists and return user info."""
    entry = ACTIVE_TOKENS.get(token)
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    user = AUTH_USERS.get(entry["username"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return {
        "username": entry["username"],
        "display_name": user["display_name"],
        "role": user["role"],
    }


# FastAPI dependency
security = HTTPBearer(auto_error=False)


async def require_auth(credentials: HTTPAuthorizationCredentials = HTTPBearer()):
    """Dependency: require valid Bearer token."""
    return verify_token(credentials.credentials)
