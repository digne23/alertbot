from datetime import datetime

from sqlalchemy import Column, Integer, String, Boolean, DateTime

from app.database import Base


class User(Base):
    """An on-call engineer.

    Multi-user routing is not switched on yet — every enabled channel still
    notifies everyone — but the model is here so escalation policies and
    per-user preferences can be added without a migration headache.
    """

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    phone = Column(String, default="")
    role = Column(String, default="engineer")  # engineer | manager | admin

    # Per-user notification preferences.
    notify_push = Column(Boolean, default=True)
    notify_email = Column(Boolean, default=False)
    notify_sms = Column(Boolean, default=False)
    notify_whatsapp = Column(Boolean, default=False)

    # Firebase registration token from the Android app.
    fcm_token = Column(String, default="")

    active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
