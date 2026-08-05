"""ntfy push notifications — the primary phone channel.

No Android build required: install the ntfy app from the Play Store, subscribe
to the topic configured here, and every POST lands on the phone. Priority 5
(`max`) rings through the lock screen, and the topic can be set to override
Do Not Disturb from inside the ntfy app.
"""

import logging

import httpx

from app.services.notifiers.base import BaseNotifier, Alert, DeliveryResult
from app.services import settings_service

logger = logging.getLogger("alertbot.notifiers.ntfy")

TIMEOUT = 10.0

# HTTP headers are latin-1 at best, so anything fancy in a title (em dashes,
# curly quotes, emoji) raises UnicodeEncodeError before the request is even
# sent. The body is UTF-8 and keeps the original text.
_TRANSLITERATE = {
    "—": "-", "–": "-", "‘": "'", "’": "'",
    "“": '"', "”": '"', "…": "...", " ": " ",
}


def ascii_header(value: str) -> str:
    text = str(value or "")
    for source, target in _TRANSLITERATE.items():
        text = text.replace(source, target)
    return text.encode("ascii", "ignore").decode("ascii").strip()


class NtfyNotifier(BaseNotifier):
    name = "ntfy"
    label = "ntfy"

    @classmethod
    def is_enabled(cls) -> bool:
        return bool(
            settings_service.get("ntfy.enabled")
            and settings_service.get("ntfy.topic")
        )

    @classmethod
    def topic_url(cls) -> str:
        server = str(settings_service.get("ntfy.server") or "https://ntfy.sh").rstrip("/")
        topic = str(settings_service.get("ntfy.topic") or "").strip("/")
        return f"{server}/{topic}"

    @classmethod
    def config_summary(cls) -> str:
        topic = settings_service.get("ntfy.topic")
        return cls.topic_url() if topic else "no topic configured"

    @classmethod
    def _priority(cls, alert: Alert) -> str:
        if alert.event == "RESOLVED":
            return "3"
        if alert.level >= 1:
            return str(settings_service.get("ntfy.escalated_priority") or 5)
        return str(settings_service.get("ntfy.priority") or 5)

    @classmethod
    def _tags(cls, alert: Alert) -> str:
        if alert.event == "RESOLVED":
            return "white_check_mark"
        if alert.event == "ESCALATED":
            return "rotating_light,bangbang"
        if alert.event == "REPEAT":
            return "rotating_light,repeat"
        if alert.event == "TEST":
            return "test_tube"
        return "rotating_light"

    @classmethod
    def send(cls, alert: Alert) -> DeliveryResult:
        if not cls.is_enabled():
            return DeliveryResult(cls.name, False, "ntfy is not enabled/configured")

        headers = {
            "Title": ascii_header(alert.title) or "AlertBot incident",
            "Priority": cls._priority(alert),
            "Tags": cls._tags(alert),
            "Markdown": "no",
        }

        token = str(settings_service.get("ntfy.token") or "").strip()
        if token:
            headers["Authorization"] = f"Bearer {token}"

        if alert.url:
            # Tapping the notification opens the dashboard.
            headers["Click"] = ascii_header(alert.url)
            if alert.incident_id and alert.is_alarm:
                headers["Actions"] = ascii_header(
                    f"http, Acknowledge, {alert.url}/api/incidents/"
                    f"{alert.incident_id}/ack, method=POST, clear=true"
                )

        try:
            response = httpx.post(
                cls.topic_url(),
                content=alert.message.encode("utf-8"),
                headers=headers,
                timeout=TIMEOUT,
            )
            if response.status_code >= 400:
                return DeliveryResult(
                    cls.name, False, f"HTTP {response.status_code}: {response.text[:200]}"
                )
            return DeliveryResult(cls.name, True, f"HTTP {response.status_code}")
        except Exception as exc:  # network down, DNS, timeout...
            logger.warning("ntfy delivery failed: %s", exc)
            return DeliveryResult(cls.name, False, f"{type(exc).__name__}: {exc}")
