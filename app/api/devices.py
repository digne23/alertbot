"""Device registration — called by the Android app, not by a human.

Deliberately outside the dashboard's Basic-auth dependency so the phone can
register with a shared registration key instead of dashboard credentials.
Set DEVICE_REGISTRATION_KEY in .env to require one.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings as env
from app.database import get_db
from app.models.device import Device

router = APIRouter(prefix="/api", tags=["devices"])


class DeviceIn(BaseModel):
    token: str
    label: str | None = ""
    platform: str | None = "android"
    user_id: int | None = None


def _check_key(key: str | None) -> None:
    expected = env.DEVICE_REGISTRATION_KEY
    if not expected:
        return
    if key != expected:
        raise HTTPException(status_code=401, detail="Invalid registration key")


@router.post("/devices")
def register_device(
    payload: DeviceIn,
    db: Session = Depends(get_db),
    x_registration_key: str | None = Header(default=None),
):
    _check_key(x_registration_key)

    token = payload.token.strip()
    if not token:
        raise HTTPException(status_code=400, detail="token is required")

    device = db.query(Device).filter(Device.token == token).first()
    if device:
        device.label = payload.label or device.label
        device.platform = payload.platform or device.platform
        device.user_id = payload.user_id or device.user_id
        device.enabled = True
        device.updated_at = datetime.utcnow()
    else:
        device = Device(
            token=token,
            label=payload.label or "",
            platform=payload.platform or "android",
            user_id=payload.user_id,
            enabled=True,
        )
        db.add(device)

    db.commit()
    db.refresh(device)
    return {"ok": True, "id": device.id, "label": device.label}


@router.delete("/devices")
def unregister_device(
    payload: DeviceIn,
    db: Session = Depends(get_db),
    x_registration_key: str | None = Header(default=None),
):
    _check_key(x_registration_key)

    device = db.query(Device).filter(Device.token == payload.token.strip()).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not registered")
    db.delete(device)
    db.commit()
    return {"ok": True}
