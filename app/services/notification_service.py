"""The single way AlertBot reaches a human.

Called only by IncidentService (and the escalation job, which acts on behalf of
IncidentService). Routes must never call a notifier directly.
"""

import logging
from datetime import datetime, timedelta

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

    # Colon, not an em dash: this title is read at arm's length on a lock
    # screen, and ntfy has to transliterate a dash out of its ASCII headers
    # anyway. "CRITICAL: Vubavuba" survives every channel unchanged.
    if event == "RESOLVED":
        title = f"RESOLVED: {incident.service}"
        prefix = "Recovered"
    elif event == "ESCALATED":
        title = f"ESCALATED: {incident.service}"
        prefix = f"STILL DOWN, NOT ACKNOWLEDGED ({incident.event_count} events)"
    elif event == "REPEAT":
        title = f"STILL DOWN: {incident.service}"
        prefix = f"Unacknowledged for {_age_minutes(incident)} min"
    else:
        title = f"{incident.severity.upper()}: {incident.service}"
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


def local_hour() -> int:
    """Server clock in the on-call team's timezone. Storage is naive UTC."""
    offset = float(settings_service.get("notifications.window_utc_offset_hours") or 0)
    return (datetime.utcnow() + timedelta(hours=offset)).hour


def window_state() -> tuple[bool, str]:
    """Is the phone allowed to ring right now? Returns (allowed, reason)."""
    if not settings_service.get("notifications.window_enabled"):
        return True, "window off"

    start = int(settings_service.get("notifications.window_start_hour") or 0)
    end = int(settings_service.get("notifications.window_end_hour") or 0)

    # A zero-width window is almost certainly a mistake, and reading it as
    # "mute everything forever" is the one failure this system must not have.
    if start == end:
        logger.warning(
            "Notification window start and end are both %s — treating as always on", start
        )
        return True, "window misconfigured, treated as always on"

    hour = local_hour()
    inside = start <= hour < end if start < end else (hour >= start or hour < end)
    return inside, f"{hour:02d}:00 local, window {start:02d}:00-{end:02d}:00"


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


def dispatch(alert: Alert, db: Session | None = None, force: bool = False) -> list[DeliveryResult]:
    """Send one alert through every enabled channel. Never raises.

    `force` bypasses the quiet-hours window. Only deliberate human tests use
    it — an admin proving the alarm path at 2pm must not be told it works by
    silence.
    """
    if not settings_service.get("notifications.enabled"):
        logger.info("Notifications disabled — skipping alert for incident %s", alert.incident_id)
        return []

    if alert.event == "RESOLVED" and not settings_service.get("notifications.notify_on_resolve"):
        return []

    if not force:
        allowed, reason = window_state()
        if not allowed:
            logger.info(
                "Outside the notification window (%s) — incident %s recorded but not pushed",
                reason, alert.incident_id,
            )
            _log(db, alert.incident_id, alert.event, alert.level,
                 [DeliveryResult("quiet-hours", False, f"held: {reason}")])
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
    # The dashboard's "Fire a test incident" button exists to prove the alarm
    # path, so its first push rings whatever the clock says. Only the first:
    # the repeat and escalation pushes obey quiet hours like anything else, so
    # a test nobody closed cannot nag through the working day.
    force = incident.source == "test" and event == "OPENED"
    results = dispatch(alert, db=db, force=force)

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

    return dispatch(alert, force=True)


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
