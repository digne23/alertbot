import re

from app.services.parsers.base import BaseParser

REASONS = [
    r"HTTP Server Error 503",
    r"HTTP\s*\d{3}",
    r"Socket timeout",
    r"Network is unreachable",
    r"Connection timed out",
]


class PingdomParser(BaseParser):
    provider_name = "Pingdom"
    sender_domains = ["pingdom.com"]

    @classmethod
    def parse(cls, sender: str, subject: str, body: str) -> dict:
        text = f"{subject}\n{body}"

        if re.search(r"\bUP\b", subject, re.IGNORECASE):
            state = "RESOLVED"
        else:
            state = "OPEN"

        service_match = re.search(
            r"([a-zA-Z0-9\-]+\.[a-zA-Z0-9\-.]+\.[a-zA-Z]{2,})", text
        )
        service = service_match.group(1) if service_match else "unknown-service"

        reason = cls.find_first(REASONS, text)

        return {
            "provider": cls.provider_name,
            "service": service,
            "state": state,
            "severity": "Critical",
            "reason": reason,
        }
