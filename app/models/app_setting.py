from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, DateTime

from app.database import Base


class AppSetting(Base):
    """Key/value store for runtime configuration edited from the Settings page.

    Values are JSON-encoded so booleans, numbers and strings all round-trip.
    """

    __tablename__ = "app_settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, nullable=False, index=True)
    value = Column(Text, default="null")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
