"""Optional dashboard protection.

Leave DASHBOARD_PASSWORD empty and AlertBot behaves exactly as before (no
login) — right for a laptop on your desk. Set it in .env before putting the
dashboard on the internet, and every page and API call needs the password.
"""

import secrets

from fastapi import Depends, Header, HTTPException, status
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


def app_key_ok(key: str | None) -> bool:
    """True when `key` is the device registration key.

    An unset key never matches. Otherwise a deployment that forgot to set one
    would accept `X-Registration-Key:` from anybody, which is the opposite of
    what leaving it blank is supposed to mean here.
    """
    expected = settings.DEVICE_REGISTRATION_KEY
    if not expected or not key:
        return False
    return secrets.compare_digest(key, expected)


def require_app_or_auth(
    credentials: HTTPBasicCredentials | None = Depends(_basic),
    x_registration_key: str | None = Header(default=None),
):
    """Dashboard login *or* the phone's registration key.

    Staff using the Android app have no dashboard password — they typed a PIN,
    and `/api/app/signin` handed their phone the registration key in exchange.
    This lets that key stand in for the password on the handful of endpoints the
    app actually needs (incidents, ack, stats, test alert).

    Deliberately *not* applied to the dashboard pages or the settings API: the
    key is baked into every APK, so it should not unlock configuration.
    """
    if app_key_ok(x_registration_key):
        return "app"
    return require_auth(credentials)
