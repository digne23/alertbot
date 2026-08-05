import re

from app.services.parsers.base import BaseParser


class GenericParser(BaseParser):
    provider_name = "Generic"
    sender_domains = []

    @classmethod
    def parse(cls, sender: str, subject: str, body: str) -> dict:
        text = f"{subject}\n{body}"

        if re.search(r"\b(up|resolved|closed|restored)\b", subject, re.IGNORECASE):
            state = "RESOLVED"
        else:
            state = "OPEN"

        domain = sender.split("@")[-1] if "@" in sender else sender

        return {
            "provider": cls.provider_name,
            "service": domain or "unknown-service",
            "state": state,
            "severity": "Critical",
            "reason": subject or "Alert",
        }
