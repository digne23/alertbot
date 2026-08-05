"""The single way AlertBot reaches a human.

Called only by IncidentService (and the escalation job, which acts on behalf of
IncidentService). Routes must never call a notifier directly.
"""

import logging
from datetime import datetime

from sqlalchemy.orm import Session

from app.config import settings as env
from app.database import SessionLocal
from app.models.incident import Incident
from app.models.notification_log import NotificationLog
from app.services import settings_service
from app.services.notifiers import Alert, DeliveryResult, enabled_notifiers, get_notifier

logger = logging.getLogger("alertbot.notifications")


def _dashboard_url() -> str:
    return str(env.PUBLIC_URL or "").rstrip("/")


def build_alert(incident: Incident, event: str = "OPENED") -> Alert:
    """Turn an incident into the message that shows up on the lock screen."""
    level = incident.escalation_level or 0

    if event == "RESOLVED":
        title = f"RESOLVED — {incident.service}"
        prefix = "Recovered"
    elif event == "ESCALATED":
        title = f"ESCALATED — {incident.service}"
        prefix = f"STILL DOWN, NOT ACKNOWLEDGED ({incident.event_count} events)"
    elif event == "REPEAT":
        title = f"STILL DOWN — {incident.service}"
        prefix = f"Unacknowledged for {_age_minutes(incident)} min"
    else:
        title = f"{incident.severity.upper()} — {incident.service}"
        prefix = "Incident opened"

    message = (
        f"{prefix}\n"
        f"Provider: {incident.provider}\n"
        f"Service: {incident.service}\n"
        f"Reason: {incident.reason or 'N/A'}\n"
        f"Events: {incident.event_count}"
    )

    return Alert(
        incident_id=incident.id,
        title=title,
        message=message,
        provider=incident.provider,
        service=incident.service,
        severity=incident.severity,
        reason=incident.reason or "",
        state=incident.state,
        event=event,
        level=level,
        event_count=incident.event_count or 1,
        url=_dashboard_url(),
    )


def _age_minutes(incident: Incident) -> int:
    if not incident.created_at:
        return 0
    return max(0, int((datetime.utcnow() - incident.created_at).total_seconds() // 60))


def _log(db: Session | None, incident_id: int | None, event: str, level: int,
         results: list[DeliveryResult]) -> None:
    owns_session = db is None
    session = db or SessionLocal()
    try:
        for result in results:
            session.add(
                NotificationLog(
                    incident_id=incident_id,
                    provider=result.provider,
                    event=event,
                    level=level,
                    success=result.success,
                    detail=result.detail[:900],
                )
            )
        session.commit()
    except Exception:
        logger.exception("Failed to write notification log")
        session.rollback()
    finally:
        if owns_session:
            session.close()


def dispatch(alert: Alert, db: Session | None = None) -> list[DeliveryResult]:
    """Send one alert through every enabled channel. Never raises."""
    if not settings_service.get("notifications.enabled"):
        logger.info("Notifications disabled — skipping alert for incident %s", alert.incident_id)
        return []

    if alert.event == "RESOLVED" and not settings_service.get("notifications.notify_on_resolve"):
        return []

    notifiers = enabled_notifiers()
    if not notifiers:
        logger.warning(
            "No notification channel is enabled — incident %s will not reach anyone",
            alert.incident_id,
        )
        _log(db, alert.incident_id, alert.event, alert.level,
             [DeliveryResult("none", False, "no channel enabled")])
        return []

    results: list[DeliveryResult] = []
    for notifier in notifiers:
        try:
            result = notifier.send(alert)
        except Exception as exc:
            logger.exception("Notifier %s crashed", notifier.name)
            result = DeliveryResult(notifier.name, False, f"{type(exc).__name__}: {exc}")
        results.append(result)
        logger.info(
            "Notification %s via %s: %s (%s)",
            alert.event, result.provider, "OK" if result.success else "FAILED", result.detail,
        )

    _log(db, alert.incident_id, alert.event, alert.level, results)
    return results


def notify(incident: Incident, event: str = "OPENED", db: Session | None = None) -> list[DeliveryResult]:
    """Notify about an incident and record that we did."""
    alert = build_alert(incident, event)
    results = dispatch(alert, db=db)

    # Always stamp the attempt, even when every channel is off or failed —
    # otherwise the escalation job would retry on every 20-second tick.
    incident.last_notified_at = datetime.utcnow()
    if results:
        incident.notify_count = (incident.notify_count or 0) + 1
    if db is not None:
        db.commit()

    return results


def send_test(provider: str | None = None) -> list[DeliveryResult]:
    """Fire a test alert. Used by the 'Test notification' button in Settings."""
    alert = Alert(
        incident_id=None,
        title="AlertBot test notification",
        message=(
            "This is a test from AlertBot.\n"
            "If your phone just made a loud noise, the alarm path works."
        ),
        provider="AlertBot",
        service="test",
        severity="Test",
        state="OPEN",
        event="TEST",
        url=_dashboard_url(),
    )

    if provider:
        notifier = get_notifier(provider)
        if notifier is None:
            return [DeliveryResult(provider, False, "unknown provider")]
        try:
            result = notifier.send(alert)
        except Exception as exc:
            result = DeliveryResult(provider, False, f"{type(exc).__name__}: {exc}")
        _log(None, None, "TEST", 0, [result])
        return [result]

    return dispatch(alert)


def channel_status() -> list[dict]:
    from app.services.notifiers import NOTIFIERS

    return [
        {
            "name": notifier.name,
            "label": notifier.label,
            "enabled": notifier.is_enabled(),
            "target": notifier.config_summary(),
        }
        for notifier in NOTIFIERS
    ]
