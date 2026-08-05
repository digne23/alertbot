from datetime import datetime

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text

from app.database import Base


class EmailLog(Base):
    __tablename__ = "email_logs"

    id = Column(Integer, primary_key=True, index=True)

    sender = Column(String, index=True)
    subject = Column(String)
    body = Column(Text)
    received_at = Column(DateTime, nullable=True)

    is_critical = Column(Boolean, default=False)
    provider = Column(String, nullable=True)
    incident_id = Column(Integer, nullable=True)

    processed_at = Column(DateTime, default=datetime.utcnow)
