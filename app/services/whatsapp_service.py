"""WhatsApp as a second input source, alongside the mailbox.

WhatsApp has no official way to read chats you are already in, so the message
is pushed to AlertBot from the phone: a MacroDroid macro triggers on the
WhatsApp notification for a watched chat and calls
`/api/ingest/whatsapp`.

From there the flow is identical to email:

    message → watched-chat match → IncidentService.create_incident() → alarm
"""

import logging
import re
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.email_log import EmailLog
from app.models.watched_chat import WatchedChat
from app.services.incident_service import IncidentService

logger = logging.getLogger("alertbot.whatsapp")

PROVIDER = "WhatsApp"


def find_watched_chat(db: Session, chat: str) -> WatchedChat | None:
    """Match a chat title against the watched list, case-insensitively.

    Notification titles get truncated and decorated ("Ops Team (3 messages)"),
    so a two-way contains-match is more reliable than equality.
    """
    chat_l = (chat or "").strip().lower()
    if not chat_l:
        return None

    for row in db.query(WatchedChat).filter(WatchedChat.enabled.is_(True)).all():
        name = (row.name or "").strip().lower()
        if not name:
            continue
        if name == chat_l or name in chat_l or chat_l in name:
            return row
    return None


def _keyword_hit(watched: WatchedChat, text: str) -> tuple[bool, list[str]]:
    keywords = watched.keyword_list()
    if not keywords:
        return True, []   # no filter: every message counts

    matched = [
        word for word in keywords
        if re.search(r"\b" + re.escape(word) + r"\b", text or "", re.IGNORECASE)
    ]
    return bool(matched), matched


def handle_message(db: Session, chat: str, message: str, sender: str = "") -> dict:
    """Process one inbound WhatsApp message. Returns what was decided."""
    chat = (chat or "").strip()
    message = (message or "").strip()
    sender = (sender or "").strip()

    result = {
        "chat": chat,
        "watched": False,
        "matched_keywords": [],
        "incident_id": None,
        "action": "ignored",
    }

    watched = find_watched_chat(db, chat)

    log_entry = EmailLog(
        sender=f"whatsapp:{chat}" + (f" ({sender})" if sender and sender != chat else ""),
        subject=message[:200],
        body=message[:5000],
        received_at=datetime.utcnow(),
        is_critical=False,
        provider=PROVIDER,
    )

    if not watched:
        db.add(log_entry)
        db.commit()
        logger.info("WhatsApp message from unwatched chat %r ignored", chat)
        result["action"] = "not_watched"
        return result

    result["watched"] = True
    watched.last_message_at = datetime.utcnow()

    should_alert, matched = _keyword_hit(watched, message)
    result["matched_keywords"] = matched

    if not should_alert:
        db.add(log_entry)
        db.commit()
        logger.info("WhatsApp message in %r ignored: no keyword match", chat)
        result["action"] = "no_keyword_match"
        return result

    log_entry.is_critical = True

    parsed = {
        "provider": PROVIDER,
        "service": watched.label or watched.name,
        "state": "OPEN",
        "severity": "Critical" if watched.alarm else "Message",
        "reason": (f"{sender}: " if sender and sender != chat else "") + (message or "(no text)"),
    }

    # reopen_on_repeat: a new message in a chat whose previous incident was
    # already acknowledged has to ring again — unlike a monitor resending the
    # same DOWN alert, it is genuinely new information.
    incident = IncidentService.create_incident(
        db, parsed, source="whatsapp", reopen_on_repeat=True
    )

    log_entry.incident_id = incident.id
    db.add(log_entry)
    db.commit()

    result["incident_id"] = incident.id
    result["action"] = "incident_created"
    logger.info("WhatsApp message in %r raised incident #%s", chat, incident.id)
    return result
