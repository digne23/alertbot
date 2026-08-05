"""Inbound message ingestion from the phone.

WhatsApp offers no official way to read chats you are already in, so the phone
forwards them: a MacroDroid macro triggers on the WhatsApp notification for a
watched chat and calls this endpoint.

Authenticated with DEVICE_REGISTRATION_KEY rather than the dashboard login,
because MacroDroid's HTTP action sends a plain URL. Both GET (easiest to build
in MacroDroid) and POST (for anything that can send JSON) are accepted.
"""

import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings as env
from app.database import get_db
from app.services import whatsapp_service

logger = logging.getLogger("alertbot.ingest")

router = APIRouter(prefix="/api/ingest", tags=["ingest"])


class WhatsAppMessage(BaseModel):
    chat: str
    message: str = ""
    sender: str = ""
    key: str | None = None


def _check_key(provided: str | None) -> None:
    expected = env.DEVICE_REGISTRATION_KEY
    if not expected:
        return
    if provided != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing key")


@router.get("/whatsapp")
def ingest_whatsapp_get(
    chat: str = Query(..., description="Chat title as WhatsApp shows it"),
    message: str = Query("", description="Message text"),
    sender: str = Query("", description="Who sent it, for group chats"),
    key: str | None = Query(None, description="DEVICE_REGISTRATION_KEY"),
    x_registration_key: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    _check_key(key or x_registration_key)
    return whatsapp_service.handle_message(db, chat=chat, message=message, sender=sender)


@router.post("/whatsapp")
def ingest_whatsapp_post(
    payload: WhatsAppMessage,
    x_registration_key: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    _check_key(payload.key or x_registration_key)
    return whatsapp_service.handle_message(
        db, chat=payload.chat, message=payload.message, sender=payload.sender
    )
