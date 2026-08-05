"""Repeat-until-acknowledged.

One incident that nobody acknowledges must keep making noise. This job runs on
a short tick and re-notifies every `escalation.repeat_minutes`, switching to
escalation level 1 once the incident has been open for
`escalation.escalate_after_minutes`.

The loop stops the moment the incident is acknowledged, silenced or resolved.
"""

import logging
from datetime import datetime, timedelta

from app.database import SessionLocal
from app.models.incident import Incident
from app.services import notification_service, settings_service

logger = logging.getLogger("alertbot.escalation")


def _minutes(key: str, fallback: int) -> int:
    try:
        return max(1, int(settings_service.get(key) or fallback))
    except (TypeError, ValueError):
        return fallback


def run_escalation_cycle() -> dict:
    """Returns a summary of what it did — handy for the dashboard and tests."""
    summary = {"checked": 0, "repeated": 0, "escalated": 0}

    if not settings_service.get("escalation.enabled"):
        return summary
    if not settings_service.get("notifications.enabled"):
        return summary

    repeat_minutes = _minutes("escalation.repeat_minutes", 2)
    escalate_after = _minutes("escalation.escalate_after_minutes", 10)
    try:
        max_repeats = int(settings_service.get("escalation.max_repeats") or 0)
    except (TypeError, ValueError):
        max_repeats = 0

    now = datetime.utcnow()

    db = SessionLocal()
    try:
        incidents = (
            db.query(Incident)
            .filter(
                Incident.state == "OPEN",
                Incident.acknowledged.is_(False),
                Incident.silenced.is_(False),
            )
            .all()
        )
        summary["checked"] = len(incidents)

        for incident in incidents:
            reference = incident.last_notified_at or incident.created_at or now
            if now - reference < timedelta(minutes=repeat_minutes):
                continue

            if max_repeats and (incident.notify_count or 0) >= max_repeats:
                continue

            opened_at = incident.created_at or now
            should_escalate = (
                now - opened_at >= timedelta(minutes=escalate_after)
                and (incident.escalation_level or 0) < 1
            )

            if should_escalate:
                incident.escalation_level = 1
                incident.escalated_at = now
                event = "ESCALATED"
                summary["escalated"] += 1
            else:
                event = "ESCALATED" if (incident.escalation_level or 0) >= 1 else "REPEAT"
                summary["repeated"] += 1

            logger.info(
                "Re-alerting incident #%s (%s, level %s, %s notifications so far)",
                incident.id, event, incident.escalation_level or 0, incident.notify_count or 0,
            )
            notification_service.notify(incident, event=event, db=db)

        db.commit()
    except Exception:
        logger.exception("Escalation cycle failed")
        db.rollback()
    finally:
        db.close()

    return summary
