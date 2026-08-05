import logging

from app.database import SessionLocal
from app.services.email_client import fetch_unseen_emails
from app.services.rule_engine import is_critical
from app.services.parsers import get_parser
from app.services.incident_service import IncidentService
from app.services import settings_service
from app.models.email_log import EmailLog

logger = logging.getLogger("alertbot.poller")


def poll_once() -> dict:
    """Fetch unseen emails, classify, parse, and update incidents. Returns a summary."""
    summary = {"fetched": 0, "critical": 0, "incidents_touched": 0, "error": None}

    try:
        emails = fetch_unseen_emails()
    except Exception as exc:
        logger.exception("Failed to fetch emails")
        summary["error"] = f"{type(exc).__name__}: {exc}"
        return summary

    summary["fetched"] = len(emails)
    if not emails:
        return summary

    db = SessionLocal()
    try:
        for item in emails:
            sender = item["sender"]
            subject = item["subject"]
            body = item["body"]

            critical = is_critical(sender, subject, body)

            log_entry = EmailLog(
                sender=sender,
                subject=subject,
                body=body[:5000],
                received_at=item.get("received_at"),
                is_critical=critical,
            )

            if critical:
                summary["critical"] += 1
                parser = get_parser(sender)
                parsed = parser.parse(sender, subject, body)
                # Single source of truth — this is what fires the phone alarm.
                incident = IncidentService.create_incident(db, parsed, source="email")

                log_entry.provider = parsed["provider"]
                log_entry.incident_id = incident.id
                summary["incidents_touched"] += 1

            db.add(log_entry)
            db.commit()
    except Exception as exc:
        logger.exception("Poll failed while processing emails")
        summary["error"] = f"{type(exc).__name__}: {exc}"
        db.rollback()
    finally:
        db.close()

    return summary


def poll_enabled() -> bool:
    return bool(settings_service.get("poll.enabled"))
