"""Sign-in for the Android app.

Staff never see a server address, a username, or the registration key. They type
the name this phone should be known by and a shared PIN. This endpoint checks
the PIN and hands back the device registration key, which the app then presents
on every other call (see `auth.require_app_or_auth`).

Deliberately outside `require_auth` — it is the one thing a phone can reach
before it holds any credential at all.

Shared PIN, not per-user: there is no individual identity here, so `name` is a
device label rather than an account. Revoking one person means changing
`APP_PIN` for everyone. That trade was made knowingly; the `users` table is
already shaped for per-user PINs when that becomes worth building.
"""

import logging
import secrets
import time

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.config import settings as env
from app.services import notification_service

logger = logging.getLogger("alertbot.app_auth")

router = APIRouter(prefix="/api/app", tags=["app"])

# --- Brute-force throttle -------------------------------------------------
# A single shared PIN on a public URL has no per-user lockout to fall back on,
# so slow down guessing per client address. In-memory and per-process: this is
# a speed bump, not a security boundary. The real defence is a PIN long enough
# not to be guessed in a handful of tries.
_MAX_FAILURES = 5
_LOCKOUT_SECONDS = 15 * 60
_failures: dict[str, list[float]] = {}


def _client_key(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _seconds_locked_out(key: str) -> int:
    recent = [t for t in _failures.get(key, []) if time.time() - t < _LOCKOUT_SECONDS]
    _failures[key] = recent
    if len(recent) < _MAX_FAILURES:
        return 0
    return int(_LOCKOUT_SECONDS - (time.time() - recent[0])) + 1


def _record_failure(key: str) -> None:
    _failures.setdefault(key, []).append(time.time())


def _push_enabled() -> bool:
    """Whether anything can actually ring a phone.

    Signing in successfully and never being woken is the worst outcome this app
    has, so the answer travels back with the sign-in rather than being
    discovered at 3am.
    """
    try:
        return any(
            channel.get("name") == "firebase" and channel.get("enabled")
            for channel in notification_service.channel_status()
        )
    except Exception:  # pragma: no cover - status must never break sign-in
        logger.warning("Could not read channel status during sign-in", exc_info=True)
        return False


class SignInRequest(BaseModel):
    name: str = ""
    pin: str = ""


@router.post("/signin")
def app_signin(payload: SignInRequest, request: Request):
    if not env.APP_PIN:
        raise HTTPException(
            status_code=503,
            detail="App sign-in is not set up yet. Ask your administrator to set APP_PIN.",
        )

    client = _client_key(request)
    locked_for = _seconds_locked_out(client)
    if locked_for:
        raise HTTPException(
            status_code=429,
            detail=f"Too many wrong PINs. Try again in {locked_for // 60 + 1} minutes.",
        )

    if not secrets.compare_digest(payload.pin.strip(), env.APP_PIN):
        _record_failure(client)
        logger.info("Rejected app sign-in from %s", client)
        raise HTTPException(status_code=401, detail="That PIN isn't right.")

    _failures.pop(client, None)

    name = payload.name.strip() or "Android phone"
    logger.info("App sign-in accepted for %r from %s", name, client)

    return {
        "ok": True,
        "name": name,
        # The app stores this and sends it as X-Registration-Key from here on.
        "key": env.DEVICE_REGISTRATION_KEY,
        "push_enabled": _push_enabled(),
    }
