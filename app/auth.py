"""HTTP Basic Auth dependency for API routes."""

import secrets
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from app.config import settings

_security = HTTPBasic()

try:
    from passlib.context import CryptContext
    _pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
except ImportError:
    _pwd_ctx = None


def require_auth(credentials: HTTPBasicCredentials = Depends(_security)) -> str:
    valid_username = secrets.compare_digest(
        credentials.username.encode(), settings.admin_username.encode()
    )

    if settings.admin_password_hash and _pwd_ctx:
        # Verify against bcrypt hash stored in config
        try:
            valid_password = _pwd_ctx.verify(credentials.password, settings.admin_password_hash)
        except Exception:
            valid_password = False
    else:
        # Legacy: plaintext comparison (constant-time)
        valid_password = secrets.compare_digest(
            credentials.password.encode(), settings.admin_password.encode()
        )

    if not (valid_username and valid_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username
