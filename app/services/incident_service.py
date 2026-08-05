"""IncidentService — the single source of truth for incidents.

Nothing else in the codebase may create, open, close or acknowledge an
incident. Every path (email poller, test alert, manual entry) goes through
`IncidentService.create_incident()`, which is also the only place that asks
NotificationService to wake somebody up.
"""

import logging
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.incident import Incident
from app.services import notification_service

logger = logging.getLogger("alertbot.incidents")


class IncidentService:

    # ------------------------------------------------------------------
    # Creation / lifecycle
    # ------------------------------------------------------------------
    @classmethod
    def create_incident(cls, db: Session, parsed: dict, source: str = "email") -> Incident:
        """Open, update or resolve an incident from a parsed alert.

        `parsed` is whatever a provider parser returned:
            {provider, service, state, severity, reason}
        """
        provider = parsed.get("provider") or "Unknown"
        service = parsed.get("service") or "unknown-service"
        state = (parsed.get("state") or "OPEN").upper()

        existing = cls.find_open(db, provider, service)

        if state == "OPEN":
            if existing:
                return cls._register_repeat_event(db, existing, parsed)
            return cls._open_new(db, provider, service, parsed, source)

        return cls._resolve(db, existing, provider, service, parsed, source)

    @classmethod
    def find_open(cls, db: Session, provider: str, service: str) -> Incident | None:
        return (
            db.query(Incident)
            .filter(
                Incident.provider == provider,
                Incident.service == service,
                Incident.state == "OPEN",
            )
            .order_by(Incident.created_at.desc())
            .first()
        )

    @classmethod
    def _open_new(cls, db: Session, provider: str, service: str,
                  parsed: dict, source: str) -> Incident:
        incident = Incident(
            provider=provider,
            service=service,
            state="OPEN",
            severity=parsed.get("severity") or "Critical",
            reason=parsed.get("reason") or "",
            source=source,
            event_count=1,
        )
        db.add(incident)
        db.commit()
        db.refresh(incident)

        logger.info("Incident #%s OPENED — %s / %s", incident.id, provider, service)
        notification_service.notify(incident, event="OPENED", db=db)
        return incident

    @classmethod
    def _register_repeat_event(cls, db: Session, incident: Incident, parsed: dict) -> Incident:
        """Another DOWN email for an incident that is already open.

        Deliberately does NOT notify: the escalation job owns the repeat alarm,
        so a flapping monitor cannot machine-gun the phone.
        """
        incident.event_count = (incident.event_count or 0) + 1
        incident.reason = parsed.get("reason") or incident.reason
        incident.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(incident)
        logger.info("Incident #%s repeat event (%s total)", incident.id, incident.event_count)
        return incident

    @classmethod
    def _resolve(cls, db: Session, existing: Incident | None, provider: str,
                 service: str, parsed: dict, source: str) -> Incident:
        now = datetime.utcnow()

        if existing:
            existing.state = "RESOLVED"
            existing.resolved = True
            existing.resolved_at = now
            existing.updated_at = now
            if parsed.get("reason"):
                existing.reason = parsed["reason"]
            db.commit()
            db.refresh(existing)
            logger.info("Incident #%s RESOLVED — %s / %s", existing.id, provider, service)
            notification_service.notify(existing, event="RESOLVED", db=db)
            return existing

        # A recovery mail with no matching open incident — keep it for history,
        # but there is nothing to wake anyone about.
        incident = Incident(
            provider=provider,
            service=service,
            state="RESOLVED",
            severity=parsed.get("severity") or "Critical",
            reason=parsed.get("reason") or "",
            source=source,
            resolved=True,
            resolved_at=now,
        )
        db.add(incident)
        db.commit()
        db.refresh(incident)
        return incident

    # ------------------------------------------------------------------
    # Engineer actions
    # ------------------------------------------------------------------
    @classmethod
    def acknowledge(cls, db: Session, incident_id: int) -> Incident | None:
        incident = db.query(Incident).filter(Incident.id == incident_id).first()
        if not incident:
            return None
        incident.acknowledged = True
        incident.acknowledged_at = datetime.utcnow()
        incident.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(incident)
        logger.info("Incident #%s acknowledged — alarm stopped", incident.id)
        return incident

    @classmethod
    def silence(cls, db: Session, incident_id: int, silenced: bool = True) -> Incident | None:
        """Stop the repeat alarm without marking the incident as handled."""
        incident = db.query(Incident).filter(Incident.id == incident_id).first()
        if not incident:
            return None
        incident.silenced = silenced
        incident.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(incident)
        return incident

    @classmethod
    def resolve_manually(cls, db: Session, incident_id: int) -> Incident | None:
        incident = db.query(Incident).filter(Incident.id == incident_id).first()
        if not incident:
            return None
        now = datetime.utcnow()
        incident.state = "RESOLVED"
        incident.resolved = True
        incident.resolved_at = now
        incident.updated_at = now
        db.commit()
        db.refresh(incident)
        logger.info("Incident #%s manually resolved", incident.id)
        return incident

    # ------------------------------------------------------------------
    # Queries used by the dashboard
    # ------------------------------------------------------------------
    @classmethod
    def open_unacknowledged(cls, db: Session) -> list[Incident]:
        return (
            db.query(Incident)
            .filter(
                Incident.state == "OPEN",
                Incident.acknowledged.is_(False),
                Incident.silenced.is_(False),
            )
            .all()
        )


# Backwards-compatible module-level helpers.
def handle_incident(db: Session, parsed: dict, source: str = "email") -> Incident:
    return IncidentService.create_incident(db, parsed, source=source)


def acknowledge(db: Session, incident_id: int) -> Incident | None:
    return IncidentService.acknowledge(db, incident_id)
