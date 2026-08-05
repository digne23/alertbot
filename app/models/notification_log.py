from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean

from app.database import Base


class NotificationLog(Base):
    """One row per delivery attempt, per provider. The audit trail for
    'did the phone actually get woken up?'."""

    __tablename__ = "notification_logs"

    id = Column(Integer, primary_key=True, index=True)

    incident_id = Column(Integer, nullable=True, index=True)
    provider = Column(String, index=True)      # ntfy | macrodroid | firebase
    event = Column(String, default="OPENED")   # OPENED | REPEAT | ESCALATED | RESOLVED | TEST
    level = Column(Integer, default=0)         # escalation level at send time

    success = Column(Boolean, default=False)
    detail = Column(Text, default="")

    created_at = Column(DateTime, default=datetime.utcnow, index=True)
