import re

from app.services.parsers.base import BaseParser


class AOSParser(BaseParser):
    provider_name = "AOS Monitoring"
    sender_domains = ["aos.rw"]

    @classmethod
    def parse(cls, sender: str, subject: str, body: str) -> dict:
        text = f"{subject}\n{body}"

        if re.search(r"\b(up|resolved|restored)\b", subject, re.IGNORECASE):
            state = "RESOLVED"
        else:
            state = "OPEN"

        ip_match = re.search(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", text)
        service = ip_match.group(0) if ip_match else "unknown-server"

        severity_match = re.search(r"Severity:\s*(\w+)", text, re.IGNORECASE)
        severity = severity_match.group(1).strip() if severity_match else "Critical"

        return {
            "provider": cls.provider_name,
            "service": service,
            "state": state,
            "severity": severity,
            "reason": "Server Unreachable",
        }
