from datetime import datetime

from sqlalchemy import Column, Integer, String, Boolean, DateTime

from app.database import Base


class Incident(Base):
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, index=True)

    provider = Column(String, index=True, nullable=False)
    service = Column(String, index=True, nullable=False)
    state = Column(String, default="OPEN", nullable=False)  # OPEN | RESOLVED
    severity = Column(String, default="Critical", nullable=False)
    reason = Column(String, default="")

    event_count = Column(Integer, default=1)

    # Where the incident came from: email | test | manual
    source = Column(String, default="email")

    acknowledged = Column(Boolean, default=False)
    acknowledged_at = Column(DateTime, nullable=True)

    resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime, nullable=True)

    # --- Notification / escalation state --------------------------------
    notify_count = Column(Integer, default=0)
    last_notified_at = Column(DateTime, nullable=True)
    escalation_level = Column(Integer, default=0)  # 0 = normal, 1 = escalated
    escalated_at = Column(DateTime, nullable=True)
    # Stops the repeat alarm without acknowledging the incident.
    silenced = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def is_open(self) -> bool:
        return self.state == "OPEN"

    @property
    def needs_alarm(self) -> bool:
        """An open, unacknowledged, un-silenced incident should keep ringing."""
        return self.is_open and not self.acknowledged and not self.silenced
