from datetime import datetime

from sqlalchemy import Column, Integer, String, Boolean, DateTime

from app.database import Base


class WatchedChat(Base):
    """A WhatsApp conversation whose messages should raise an incident.

    `name` is matched against the chat title exactly as WhatsApp shows it in
    the notification — case-insensitive, and a contains-match so a group title
    that gets truncated on the phone still matches.
    """

    __tablename__ = "watched_chats"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String, unique=True, nullable=False, index=True)
    label = Column(String, default="")

    # Empty = alarm on every message from this chat.
    # Otherwise a comma-separated list; only matching messages raise an incident.
    keywords = Column(String, default="")

    # False = record the message but never make noise.
    alarm = Column(Boolean, default=True)
    enabled = Column(Boolean, default=True)

    last_message_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def keyword_list(self) -> list[str]:
        return [word.strip().lower() for word in (self.keywords or "").split(",") if word.strip()]
