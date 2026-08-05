"""Optional dashboard protection.

Leave DASHBOARD_PASSWORD empty and AlertBot behaves exactly as before (no
login) — right for a laptop on your desk. Set it in .env before putting the
dashboard on the internet, and every page and API call needs the password.
"""

import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from app.config import settings

_basic = HTTPBasic(auto_error=False)


def auth_enabled() -> bool:
    return bool(settings.DASHBOARD_PASSWORD)


def require_auth(credentials: HTTPBasicCredentials | None = Depends(_basic)):
    if not auth_enabled():
        return None

    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authorised",
        headers={"WWW-Authenticate": 'Basic realm="AlertBot"'},
    )

    if credentials is None:
        raise unauthorized

    user_ok = secrets.compare_digest(credentials.username, settings.DASHBOARD_USER)
    password_ok = secrets.compare_digest(credentials.password, settings.DASHBOARD_PASSWORD)
    if not (user_ok and password_ok):
        raise unauthorized

    return credentials.username
