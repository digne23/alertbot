"""Database-backed runtime configuration.

Everything the Settings page can change lives here. `.env` still provides the
initial value for each key the first time the database is created; after that
the database wins, so the app can be reconfigured without a restart.
"""

import json
import logging
import threading

from sqlalchemy.orm import Session

from app.config import settings as env
from app.database import SessionLocal
from app.models.app_setting import AppSetting

logger = logging.getLogger("alertbot.settings")

_lock = threading.Lock()
_cache: dict | None = None


def defaults() -> dict:
    return {
        # Master switch — turn every notification off in one click.
        "notifications.enabled": True,
        "notifications.notify_on_resolve": True,

        # ntfy (https://ntfy.sh) — the primary phone channel.
        "ntfy.enabled": bool(env.NTFY_TOPIC),
        "ntfy.server": env.NTFY_SERVER,
        "ntfy.topic": env.NTFY_TOPIC,
        "ntfy.token": env.NTFY_TOKEN,
        "ntfy.priority": 5,            # 5 = max, bypasses most silencing
        "ntfy.escalated_priority": 5,

        # MacroDroid cloud webhook — drives the loud alarm on the phone.
        "macrodroid.enabled": bool(env.MACRODROID_WEBHOOK_URL),
        "macrodroid.webhook_url": env.MACRODROID_WEBHOOK_URL,

        # Firebase Cloud Messaging — dormant until an Android build exists.
        "firebase.enabled": False,

        # Repeat-until-acknowledged.
        "escalation.enabled": True,
        "escalation.repeat_minutes": env.ESCALATION_REPEAT_MINUTES,
        "escalation.escalate_after_minutes": env.ESCALATION_AFTER_MINUTES,
        "escalation.max_repeats": 0,   # 0 = keep going until acknowledged

        # Mailbox polling.
        "poll.interval_seconds": env.CHECK_INTERVAL,
        "poll.enabled": True,

        # This mailbox is read by a human too, so AlertBot tracks its own
        # position by IMAP UID and leaves the unread flag alone. Turn this on
        # only for a dedicated mailbox nobody else opens.
        "mail.mark_seen": False,
    }


def _load(db: Session) -> dict:
    values = defaults()
    for row in db.query(AppSetting).all():
        try:
            values[row.key] = json.loads(row.value)
        except (json.JSONDecodeError, TypeError):
            values[row.key] = row.value
    return values


def seed_defaults() -> None:
    """Write any missing default into the database. Safe to call on every boot."""
    db = SessionLocal()
    try:
        existing = {row.key for row in db.query(AppSetting.key).all()}
        added = False
        for key, value in defaults().items():
            if key in existing:
                continue
            db.add(AppSetting(key=key, value=json.dumps(value)))
            added = True
        if added:
            db.commit()
    finally:
        db.close()
    invalidate()


def invalidate() -> None:
    global _cache
    with _lock:
        _cache = None


def all_settings() -> dict:
    global _cache
    with _lock:
        if _cache is not None:
            return dict(_cache)

    db = SessionLocal()
    try:
        values = _load(db)
    finally:
        db.close()

    with _lock:
        _cache = values
    return dict(values)


def get(key: str, default=None):
    return all_settings().get(key, defaults().get(key, default))


def set_many(updates: dict) -> dict:
    db = SessionLocal()
    try:
        for key, value in updates.items():
            row = db.query(AppSetting).filter(AppSetting.key == key).first()
            payload = json.dumps(value)
            if row:
                row.value = payload
            else:
                db.add(AppSetting(key=key, value=payload))
        db.commit()
    finally:
        db.close()

    invalidate()
    return all_settings()


def set(key: str, value) -> dict:
    return set_many({key: value})
