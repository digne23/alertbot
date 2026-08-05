from datetime import datetime

from sqlalchemy import Column, Integer, String, Boolean, DateTime

from app.database import Base


class CriticalSender(Base):
    """An email address or domain fragment whose mail is treated as an alert."""

    __tablename__ = "critical_senders"

    id = Column(Integer, primary_key=True, index=True)
    value = Column(String, unique=True, nullable=False, index=True)
    label = Column(String, default="")
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class CriticalKeyword(Base):
    """A word/phrase that marks a message from a critical sender as an incident."""

    __tablename__ = "critical_keywords"

    id = Column(Integer, primary_key=True, index=True)
    value = Column(String, unique=True, nullable=False, index=True)
    # OPEN keywords raise an incident, RESOLVED keywords close one,
    # ANY simply flags the mail as critical and lets the parser decide.
    intent = Column(String, default="ANY")
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
