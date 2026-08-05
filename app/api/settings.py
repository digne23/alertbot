"""Settings API — rules, notification providers, escalation timing, users, devices."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import require_auth
from app.database import get_db
from app.models.rule import CriticalSender, CriticalKeyword
from app.models.user import User
from app.models.device import Device
from app.services import settings_service, rule_engine, notification_service
from app import scheduler as scheduler_module

router = APIRouter(prefix="/api/settings", tags=["settings"], dependencies=[Depends(require_auth)])


# ----------------------------------------------------------------------
# Key/value settings
# ----------------------------------------------------------------------
class SettingsUpdate(BaseModel):
    values: dict


@router.get("")
def read_settings():
    values = settings_service.all_settings()
    # Never hand the ntfy token back to the browser in full.
    token = str(values.get("ntfy.token") or "")
    values["ntfy.token_set"] = bool(token)
    values["ntfy.token"] = ("•" * 8 + token[-4:]) if token else ""
    return {
        "values": values,
        "channels": notification_service.channel_status(),
        "jobs": scheduler_module.job_status(),
    }


@router.put("")
def update_settings(payload: SettingsUpdate):
    updates = dict(payload.values)

    # An untouched masked token must not overwrite the stored one.
    if "ntfy.token" in updates and str(updates["ntfy.token"]).startswith("•"):
        updates.pop("ntfy.token")
    updates.pop("ntfy.token_set", None)

    for key in ("escalation.repeat_minutes", "escalation.escalate_after_minutes",
                "escalation.max_repeats", "poll.interval_seconds",
                "ntfy.priority", "ntfy.escalated_priority"):
        if key in updates:
            try:
                updates[key] = int(updates[key])
            except (TypeError, ValueError):
                raise HTTPException(status_code=400, detail=f"{key} must be a number")

    values = settings_service.set_many(updates)

    if "poll.interval_seconds" in updates:
        scheduler_module.reschedule_poll(values.get("poll.interval_seconds"))

    return {"ok": True, "values": values, "channels": notification_service.channel_status()}


# ----------------------------------------------------------------------
# Critical senders
# ----------------------------------------------------------------------
class SenderIn(BaseModel):
    value: str
    label: str | None = ""
    enabled: bool | None = True


@router.get("/senders")
def list_senders(db: Session = Depends(get_db)):
    rows = db.query(CriticalSender).order_by(CriticalSender.value).all()
    return [
        {"id": r.id, "value": r.value, "label": r.label, "enabled": bool(r.enabled)}
        for r in rows
    ]


@router.post("/senders")
def add_sender(payload: SenderIn, db: Session = Depends(get_db)):
    value = payload.value.strip().lower()
    if not value:
        raise HTTPException(status_code=400, detail="Sender cannot be empty")
    if db.query(CriticalSender).filter(CriticalSender.value == value).first():
        raise HTTPException(status_code=409, detail="Sender already exists")

    row = CriticalSender(value=value, label=payload.label or "", enabled=bool(payload.enabled))
    db.add(row)
    db.commit()
    db.refresh(row)
    rule_engine.invalidate()
    return {"id": row.id, "value": row.value, "label": row.label, "enabled": bool(row.enabled)}


@router.put("/senders/{sender_id}")
def update_sender(sender_id: int, payload: SenderIn, db: Session = Depends(get_db)):
    row = db.query(CriticalSender).filter(CriticalSender.id == sender_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Sender not found")
    row.value = payload.value.strip().lower() or row.value
    row.label = payload.label or ""
    row.enabled = bool(payload.enabled)
    db.commit()
    rule_engine.invalidate()
    return {"id": row.id, "value": row.value, "label": row.label, "enabled": bool(row.enabled)}


@router.delete("/senders/{sender_id}")
def delete_sender(sender_id: int, db: Session = Depends(get_db)):
    row = db.query(CriticalSender).filter(CriticalSender.id == sender_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Sender not found")
    db.delete(row)
    db.commit()
    rule_engine.invalidate()
    return {"ok": True}


# ----------------------------------------------------------------------
# Critical keywords
# ----------------------------------------------------------------------
class KeywordIn(BaseModel):
    value: str
    intent: str | None = "ANY"
    enabled: bool | None = True


@router.get("/keywords")
def list_keywords(db: Session = Depends(get_db)):
    rows = db.query(CriticalKeyword).order_by(CriticalKeyword.value).all()
    return [
        {"id": r.id, "value": r.value, "intent": r.intent, "enabled": bool(r.enabled)}
        for r in rows
    ]


@router.post("/keywords")
def add_keyword(payload: KeywordIn, db: Session = Depends(get_db)):
    value = payload.value.strip().lower()
    if not value:
        raise HTTPException(status_code=400, detail="Keyword cannot be empty")
    if db.query(CriticalKeyword).filter(CriticalKeyword.value == value).first():
        raise HTTPException(status_code=409, detail="Keyword already exists")

    row = CriticalKeyword(
        value=value, intent=(payload.intent or "ANY").upper(), enabled=bool(payload.enabled)
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    rule_engine.invalidate()
    return {"id": row.id, "value": row.value, "intent": row.intent, "enabled": bool(row.enabled)}


@router.put("/keywords/{keyword_id}")
def update_keyword(keyword_id: int, payload: KeywordIn, db: Session = Depends(get_db)):
    row = db.query(CriticalKeyword).filter(CriticalKeyword.id == keyword_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Keyword not found")
    row.value = payload.value.strip().lower() or row.value
    row.intent = (payload.intent or "ANY").upper()
    row.enabled = bool(payload.enabled)
    db.commit()
    rule_engine.invalidate()
    return {"id": row.id, "value": row.value, "intent": row.intent, "enabled": bool(row.enabled)}


@router.delete("/keywords/{keyword_id}")
def delete_keyword(keyword_id: int, db: Session = Depends(get_db)):
    row = db.query(CriticalKeyword).filter(CriticalKeyword.id == keyword_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Keyword not found")
    db.delete(row)
    db.commit()
    rule_engine.invalidate()
    return {"ok": True}


# ----------------------------------------------------------------------
# Users
# ----------------------------------------------------------------------
class UserIn(BaseModel):
    name: str
    email: str
    phone: str | None = ""
    role: str | None = "engineer"
    notify_push: bool | None = True
    notify_email: bool | None = False
    notify_sms: bool | None = False
    notify_whatsapp: bool | None = False
    fcm_token: str | None = ""
    active: bool | None = True


def _serialize_user(user: User) -> dict:
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "phone": user.phone,
        "role": user.role,
        "notify_push": bool(user.notify_push),
        "notify_email": bool(user.notify_email),
        "notify_sms": bool(user.notify_sms),
        "notify_whatsapp": bool(user.notify_whatsapp),
        "has_token": bool(user.fcm_token),
        "active": bool(user.active),
    }


@router.get("/users")
def list_users(db: Session = Depends(get_db)):
    return [_serialize_user(u) for u in db.query(User).order_by(User.name).all()]


@router.post("/users")
def add_user(payload: UserIn, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=409, detail="A user with that email already exists")

    user = User(
        name=payload.name.strip(),
        email=email,
        phone=payload.phone or "",
        role=payload.role or "engineer",
        notify_push=bool(payload.notify_push),
        notify_email=bool(payload.notify_email),
        notify_sms=bool(payload.notify_sms),
        notify_whatsapp=bool(payload.notify_whatsapp),
        fcm_token=payload.fcm_token or "",
        active=bool(payload.active),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _serialize_user(user)


@router.put("/users/{user_id}")
def update_user(user_id: int, payload: UserIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.name = payload.name.strip() or user.name
    user.email = payload.email.strip().lower() or user.email
    user.phone = payload.phone or ""
    user.role = payload.role or "engineer"
    user.notify_push = bool(payload.notify_push)
    user.notify_email = bool(payload.notify_email)
    user.notify_sms = bool(payload.notify_sms)
    user.notify_whatsapp = bool(payload.notify_whatsapp)
    if payload.fcm_token:
        user.fcm_token = payload.fcm_token
    user.active = bool(payload.active)
    db.commit()
    db.refresh(user)
    return _serialize_user(user)


@router.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
    return {"ok": True}


# ----------------------------------------------------------------------
# Devices (FCM tokens)
# ----------------------------------------------------------------------
@router.get("/devices")
def list_devices(db: Session = Depends(get_db)):
    rows = db.query(Device).order_by(Device.created_at.desc()).all()
    return [
        {
            "id": r.id,
            "label": r.label,
            "platform": r.platform,
            "token_preview": (r.token[:14] + "…") if r.token else "",
            "enabled": bool(r.enabled),
            "user_id": r.user_id,
        }
        for r in rows
    ]


@router.delete("/devices/{device_id}")
def delete_device(device_id: int, db: Session = Depends(get_db)):
    row = db.query(Device).filter(Device.id == device_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Device not found")
    db.delete(row)
    db.commit()
    return {"ok": True}


# ----------------------------------------------------------------------
# Test the notification path
# ----------------------------------------------------------------------
@router.post("/test-notification")
def test_notification(provider: str | None = None):
    results = notification_service.send_test(provider)
    return {
        "results": [
            {"provider": r.provider, "success": r.success, "detail": r.detail} for r in results
        ]
    }
