"""Decides whether an email is an incident.

Rules live in the database (`critical_senders` / `critical_keywords`) and are
editable from the Settings page. The values in config.py are only used to seed
the tables the first time the app runs.
"""

import re
import threading

from app.config import settings as env
from app.database import SessionLocal
from app.models.rule import CriticalSender, CriticalKeyword

_lock = threading.Lock()
_cache: dict | None = None


def _keyword_pattern(keyword: str) -> re.Pattern:
    # Word-boundary match so short keywords like "up"/"down" don't match
    # substrings such as "support" or "download".
    return re.compile(r"\b" + re.escape(keyword) + r"\b", re.IGNORECASE)


def seed_rules() -> None:
    """Populate the rule tables from config defaults if they are empty."""
    db = SessionLocal()
    try:
        if db.query(CriticalSender).count() == 0:
            for value in env.CRITICAL_SENDERS:
                db.add(CriticalSender(value=value.lower(), label=""))
        if db.query(CriticalKeyword).count() == 0:
            for value in env.CRITICAL_KEYWORDS:
                db.add(CriticalKeyword(value=value.lower(), intent="ANY"))
        db.commit()
    finally:
        db.close()
    invalidate()


def invalidate() -> None:
    global _cache
    with _lock:
        _cache = None


def _load() -> dict:
    db = SessionLocal()
    try:
        senders = [
            row.value.lower()
            for row in db.query(CriticalSender).filter(CriticalSender.enabled.is_(True)).all()
        ]
        keywords = [
            row.value.lower()
            for row in db.query(CriticalKeyword).filter(CriticalKeyword.enabled.is_(True)).all()
        ]
    finally:
        db.close()

    if not senders:
        senders = list(env.CRITICAL_SENDERS)
    if not keywords:
        keywords = list(env.CRITICAL_KEYWORDS)

    return {
        "senders": senders,
        "keywords": keywords,
        "patterns": [_keyword_pattern(k) for k in keywords],
    }


def rules() -> dict:
    global _cache
    with _lock:
        if _cache is not None:
            return _cache
    loaded = _load()
    with _lock:
        _cache = loaded
    return loaded


def is_critical(sender: str, subject: str, body: str) -> bool:
    active = rules()
    sender = (sender or "").lower()
    text = f"{subject or ''}\n{body or ''}"

    sender_match = any(known in sender for known in active["senders"])
    if not sender_match:
        return False

    return any(pattern.search(text) for pattern in active["patterns"])


def explain(sender: str, subject: str, body: str) -> dict:
    """Same decision as is_critical, but reports which rules matched.
    Used by the rule tester on the Settings page."""
    active = rules()
    sender_l = (sender or "").lower()
    text = f"{subject or ''}\n{body or ''}"

    matched_senders = [s for s in active["senders"] if s in sender_l]
    matched_keywords = [
        keyword
        for keyword, pattern in zip(active["keywords"], active["patterns"])
        if pattern.search(text)
    ]

    return {
        "critical": bool(matched_senders and matched_keywords),
        "matched_senders": matched_senders,
        "matched_keywords": matched_keywords,
    }
