import re

from app.services.parsers.base import BaseParser


class ESICIAMonitorParser(BaseParser):
    provider_name = "ESICIA Monitor"
    sender_domains = ["esicia.site", "noc@esicia.rw"]

    @classmethod
    def parse(cls, sender: str, subject: str, body: str) -> dict:
        text = f"{subject}\n{body}"

        if re.search(r"incident\s+(closed|resolved)", text, re.IGNORECASE):
            state = "RESOLVED"
        else:
            state = "OPEN"

        service_match = re.search(r"Website\s+([^\n(]+)", text, re.IGNORECASE)
        service = service_match.group(1).strip() if service_match else "unknown-website"

        reason_match = re.search(r"\(([^)]+)\)", text)
        reason = reason_match.group(1).strip() if reason_match else "Incident reported"

        return {
            "provider": cls.provider_name,
            "service": service,
            "state": state,
            "severity": "Critical",
            "reason": reason,
        }
