from datetime import datetime

from sqlalchemy import Column, Integer, String, Boolean, DateTime

from app.database import Base


class Device(Base):
    """A Firebase Cloud Messaging registration token.

    The Android app registers itself here on first launch (POST /api/devices),
    so notifications work even before any User record exists.
    """

    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, unique=True, nullable=False)
    label = Column(String, default="")
    platform = Column(String, default="android")   # android | web | ios
    user_id = Column(Integer, nullable=True, index=True)
    enabled = Column(Boolean, default=True)
    last_success_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
