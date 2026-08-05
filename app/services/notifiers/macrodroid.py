"""MacroDroid cloud-webhook channel — this is what makes the phone scream.

MacroDroid gives every macro a public trigger URL of the shape
    https://trigger.macrodroid.com/<device-id>/<trigger-name>
Hitting it fires a macro on the phone, which can set the alarm stream to max
volume, override Do Not Disturb and play a siren on loop — things a normal
push notification is not allowed to do.

Variables are passed as query parameters so the macro can speak the service
name and show it on screen.
"""

import logging
from urllib.parse import urlencode

import httpx

from app.services.notifiers.base import BaseNotifier, Alert, DeliveryResult
from app.services import settings_service

logger = logging.getLogger("alertbot.notifiers.macrodroid")

TIMEOUT = 10.0


class MacroDroidNotifier(BaseNotifier):
    name = "macrodroid"
    label = "MacroDroid"

    @classmethod
    def is_enabled(cls) -> bool:
        return bool(
            settings_service.get("macrodroid.enabled")
            and settings_service.get("macrodroid.webhook_url")
        )

    @classmethod
    def config_summary(cls) -> str:
        url = str(settings_service.get("macrodroid.webhook_url") or "")
        return url or "no webhook URL configured"

    @classmethod
    def send(cls, alert: Alert) -> DeliveryResult:
        if not cls.is_enabled():
            return DeliveryResult(cls.name, False, "MacroDroid is not enabled/configured")

        base = str(settings_service.get("macrodroid.webhook_url")).strip()

        params = {
            "incident": alert.incident_id or 0,
            "title": alert.title,
            "message": alert.message,
            "service": alert.service,
            "provider": alert.provider,
            "severity": alert.severity,
            "state": alert.state,
            "event": alert.event,
            "level": alert.level,
            "alarm": "1" if alert.is_alarm else "0",
        }

        separator = "&" if "?" in base else "?"
        url = f"{base}{separator}{urlencode(params)}"

        try:
            response = httpx.get(url, timeout=TIMEOUT, follow_redirects=True)
            if response.status_code >= 400:
                return DeliveryResult(
                    cls.name, False, f"HTTP {response.status_code}: {response.text[:200]}"
                )
            return DeliveryResult(cls.name, True, f"HTTP {response.status_code}")
        except Exception as exc:
            logger.warning("MacroDroid delivery failed: %s", exc)
            return DeliveryResult(cls.name, False, f"{type(exc).__name__}: {exc}")
