import csv
import io
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import or_, func
from sqlalchemy.orm import Session

from app.auth import require_app_or_auth
from app.database import get_db
from app.models.incident import Incident
from app.models.notification_log import NotificationLog
from app.models.email_log import EmailLog
from app.services.incident_service import IncidentService
from app.services.poller import poll_once
from app.services import notification_service

router = APIRouter(
    prefix="/api",
    tags=["incidents"],
    # Dashboard login or the phone's registration key — the Android app has no
    # dashboard password to offer. See app/auth.py.
    dependencies=[Depends(require_app_or_auth)],
)


def _iso(value: datetime | None) -> str | None:
    # Timestamps are stored as naive UTC — tag them so the browser converts
    # to local time instead of assuming the local zone.
    return value.isoformat() + "Z" if value else None


def serialize(incident: Incident) -> dict:
    return {
        "id": incident.id,
        "provider": incident.provider,
        "service": incident.service,
        "state": incident.state,
        "severity": incident.severity,
        "reason": incident.reason,
        "event_count": incident.event_count,
        "source": incident.source,
        "acknowledged": bool(incident.acknowledged),
        "acknowledged_at": _iso(incident.acknowledged_at),
        "resolved": bool(incident.resolved),
        "resolved_at": _iso(incident.resolved_at),
        "silenced": bool(incident.silenced),
        "notify_count": incident.notify_count or 0,
        "last_notified_at": _iso(incident.last_notified_at),
        "escalation_level": incident.escalation_level or 0,
        "escalated_at": _iso(incident.escalated_at),
        "created_at": _iso(incident.created_at),
        "updated_at": _iso(incident.updated_at),
    }


def _filtered_query(
    db: Session,
    state: str | None,
    provider: str | None,
    acknowledged: str | None,
    q: str | None,
    since: str | None,
    until: str | None,
):
    query = db.query(Incident)

    if state and state.upper() != "ALL":
        query = query.filter(Incident.state == state.upper())

    if provider and provider.upper() != "ALL":
        query = query.filter(Incident.provider == provider)

    if acknowledged in ("true", "false"):
        query = query.filter(Incident.acknowledged.is_(acknowledged == "true"))

    if q:
        pattern = f"%{q.strip()}%"
        query = query.filter(
            or_(
                Incident.service.ilike(pattern),
                Incident.provider.ilike(pattern),
                Incident.reason.ilike(pattern),
                Incident.severity.ilike(pattern),
            )
        )

    for value, comparator in ((since, "since"), (until, "until")):
        if not value:
            continue
        try:
            parsed = datetime.fromisoformat(value.replace("Z", ""))
        except ValueError:
            continue
        if comparator == "since":
            query = query.filter(Incident.created_at >= parsed)
        else:
            query = query.filter(Incident.created_at <= parsed + timedelta(days=1))

    return query


@router.get("/incidents")
def list_incidents(
    db: Session = Depends(get_db),
    state: str | None = Query(None),
    provider: str | None = Query(None),
    acknowledged: str | None = Query(None),
    q: str | None = Query(None),
    since: str | None = Query(None),
    until: str | None = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    query = _filtered_query(db, state, provider, acknowledged, q, since, until)
    total = query.count()
    incidents = (
        query.order_by(Incident.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [serialize(incident) for incident in incidents],
    }


@router.get("/incidents/{incident_id}")
def get_incident(incident_id: int, db: Session = Depends(get_db)):
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    notifications = (
        db.query(NotificationLog)
        .filter(NotificationLog.incident_id == incident_id)
        .order_by(NotificationLog.created_at.desc())
        .limit(50)
        .all()
    )
    emails = (
        db.query(EmailLog)
        .filter(EmailLog.incident_id == incident_id)
        .order_by(EmailLog.processed_at.desc())
        .limit(20)
        .all()
    )

    data = serialize(incident)
    data["notifications"] = [
        {
            "id": n.id,
            "provider": n.provider,
            "event": n.event,
            "level": n.level,
            "success": bool(n.success),
            "detail": n.detail,
            "created_at": _iso(n.created_at),
        }
        for n in notifications
    ]
    data["emails"] = [
        {
            "id": e.id,
            "sender": e.sender,
            "subject": e.subject,
            "received_at": _iso(e.received_at),
        }
        for e in emails
    ]
    return data


@router.post("/incidents/{incident_id}/ack")
def acknowledge_incident(incident_id: int, db: Session = Depends(get_db)):
    incident = IncidentService.acknowledge(db, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return {"ok": True, "incident": serialize(incident)}


@router.post("/incidents/{incident_id}/silence")
def silence_incident(incident_id: int, silenced: bool = True, db: Session = Depends(get_db)):
    incident = IncidentService.silence(db, incident_id, silenced=silenced)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return {"ok": True, "incident": serialize(incident)}


@router.post("/incidents/{incident_id}/resolve")
def resolve_incident(incident_id: int, db: Session = Depends(get_db)):
    incident = IncidentService.resolve_manually(db, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return {"ok": True, "incident": serialize(incident)}


@router.get("/stats")
def stats(db: Session = Depends(get_db)):
    now = datetime.utcnow()
    day_ago = now - timedelta(days=1)
    week_ago = now - timedelta(days=7)

    open_count = db.query(Incident).filter(Incident.state == "OPEN").count()
    unacked = (
        db.query(Incident)
        .filter(Incident.state == "OPEN", Incident.acknowledged.is_(False))
        .count()
    )
    resolved_24h = (
        db.query(Incident)
        .filter(Incident.state == "RESOLVED", Incident.resolved_at >= day_ago)
        .count()
    )
    total = db.query(Incident).count()
    notifications_24h = (
        db.query(NotificationLog).filter(NotificationLog.created_at >= day_ago).count()
    )
    failed_24h = (
        db.query(NotificationLog)
        .filter(NotificationLog.created_at >= day_ago, NotificationLog.success.is_(False))
        .count()
    )

    by_provider = (
        db.query(Incident.provider, func.count(Incident.id))
        .filter(Incident.created_at >= week_ago)
        .group_by(Incident.provider)
        .all()
    )

    # Grouped in Python rather than SQL: date_trunc/strftime/CAST all differ
    # between SQLite and PostgreSQL, and a week of incidents is a tiny set.
    recent_dates = (
        db.query(Incident.created_at)
        .filter(Incident.created_at >= week_ago)
        .all()
    )
    counts: dict[str, int] = {}
    for (created,) in recent_dates:
        if created:
            counts[created.date().isoformat()] = counts.get(created.date().isoformat(), 0) + 1
    per_day = sorted(counts.items())

    # Mean time to acknowledge, in minutes, over the last 7 days.
    acked = (
        db.query(Incident)
        .filter(
            Incident.acknowledged.is_(True),
            Incident.acknowledged_at.isnot(None),
            Incident.created_at >= week_ago,
        )
        .all()
    )
    mtta = None
    if acked:
        deltas = [
            (incident.acknowledged_at - incident.created_at).total_seconds()
            for incident in acked
            if incident.acknowledged_at and incident.created_at
        ]
        if deltas:
            mtta = round(sum(deltas) / len(deltas) / 60, 1)

    return {
        "open": open_count,
        "unacknowledged": unacked,
        "resolved_24h": resolved_24h,
        "total": total,
        "notifications_24h": notifications_24h,
        "notification_failures_24h": failed_24h,
        "mtta_minutes": mtta,
        "by_provider": [{"provider": p, "count": c} for p, c in by_provider],
        "per_day": [{"day": day, "count": count} for day, count in per_day],
        "channels": notification_service.channel_status(),
    }


@router.get("/providers")
def providers(db: Session = Depends(get_db)):
    rows = db.query(Incident.provider).distinct().all()
    return sorted({row[0] for row in rows if row[0]})


@router.get("/notifications")
def recent_notifications(db: Session = Depends(get_db), limit: int = Query(50, ge=1, le=500)):
    rows = (
        db.query(NotificationLog)
        .order_by(NotificationLog.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": row.id,
            "incident_id": row.incident_id,
            "provider": row.provider,
            "event": row.event,
            "level": row.level,
            "success": bool(row.success),
            "detail": row.detail,
            "created_at": _iso(row.created_at),
        }
        for row in rows
    ]


@router.get("/emails")
def recent_emails(db: Session = Depends(get_db), limit: int = Query(50, ge=1, le=500)):
    rows = (
        db.query(EmailLog)
        .order_by(EmailLog.processed_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": row.id,
            "sender": row.sender,
            "subject": row.subject,
            "is_critical": bool(row.is_critical),
            "provider": row.provider,
            "incident_id": row.incident_id,
            "received_at": _iso(row.received_at),
            "processed_at": _iso(row.processed_at),
        }
        for row in rows
    ]


@router.get("/incidents.csv")
def export_csv(
    db: Session = Depends(get_db),
    state: str | None = Query(None),
    provider: str | None = Query(None),
    acknowledged: str | None = Query(None),
    q: str | None = Query(None),
    since: str | None = Query(None),
    until: str | None = Query(None),
):
    query = _filtered_query(db, state, provider, acknowledged, q, since, until)
    incidents = query.order_by(Incident.created_at.desc()).all()

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([
        "id", "created_at", "provider", "service", "state", "severity", "reason",
        "events", "acknowledged", "acknowledged_at", "resolved_at",
        "notifications_sent", "escalation_level", "source",
    ])
    for incident in incidents:
        writer.writerow([
            incident.id,
            _iso(incident.created_at),
            incident.provider,
            incident.service,
            incident.state,
            incident.severity,
            incident.reason,
            incident.event_count,
            incident.acknowledged,
            _iso(incident.acknowledged_at),
            _iso(incident.resolved_at),
            incident.notify_count or 0,
            incident.escalation_level or 0,
            incident.source,
        ])

    buffer.seek(0)
    stamp = datetime.utcnow().strftime("%Y%m%d-%H%M")
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="alertbot-incidents-{stamp}.csv"'},
    )


@router.post("/poll")
def trigger_poll():
    return poll_once()
