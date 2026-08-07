"""Test / simulation endpoints.

These go through IncidentService.create_incident() exactly like a real email
would, so a test alert exercises the full path including the phone alarm.
"""

import random

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import require_app_or_auth
from app.database import get_db
from app.services.incident_service import IncidentService
from app.services.rule_engine import explain
from app.services.parsers import get_parser
from app.api.incidents import serialize

router = APIRouter(
    prefix="/api",
    tags=["Testing"],
    # The app's "Send a test alert" needs this, and it holds the registration
    # key rather than a dashboard password. See app/auth.py.
    dependencies=[Depends(require_app_or_auth)],
)


SAMPLES = [
    {
        "provider": "Pingdom",
        "service": "portal.esicia.rw",
        "severity": "Critical",
        "reason": "HTTP Server Error 503 Service Unavailable",
    },
    {
        "provider": "ESICIA Monitor",
        "service": "api.esicia.site",
        "severity": "Critical",
        "reason": "Incident OPENED: Search String Missing",
    },
    {
        "provider": "AOS",
        "service": "aos-gateway",
        "severity": "Critical",
        "reason": "Server Unreachable",
    },
]


class TestAlertRequest(BaseModel):
    provider: str | None = None
    service: str | None = None
    severity: str | None = None
    reason: str | None = None
    state: str | None = "OPEN"


class SimulateEmailRequest(BaseModel):
    sender: str
    subject: str
    body: str = ""
    create_incident: bool = False


@router.post("/test-alert")
def generate_test_alert(payload: TestAlertRequest | None = None, db: Session = Depends(get_db)):
    sample = random.choice(SAMPLES)
    payload = payload or TestAlertRequest()

    parsed = {
        "provider": payload.provider or sample["provider"],
        "service": payload.service or sample["service"],
        "state": (payload.state or "OPEN").upper(),
        "severity": payload.severity or sample["severity"],
        "reason": payload.reason or sample["reason"],
    }

    incident = IncidentService.create_incident(db, parsed, source="test")

    return {
        "success": True,
        "message": "Test alert created through IncidentService.",
        "incident_id": incident.id,
        "incident": serialize(incident),
    }


@router.post("/simulate-email")
def simulate_email(payload: SimulateEmailRequest, db: Session = Depends(get_db)):
    """Paste a real alert email and see exactly what AlertBot would do with it."""
    verdict = explain(payload.sender, payload.subject, payload.body)
    parser = get_parser(payload.sender)
    parsed = parser.parse(payload.sender, payload.subject, payload.body)

    result = {
        "critical": verdict["critical"],
        "matched_senders": verdict["matched_senders"],
        "matched_keywords": verdict["matched_keywords"],
        "parser": parser.provider_name,
        "parsed": parsed,
        "incident": None,
    }

    if verdict["critical"] and payload.create_incident:
        incident = IncidentService.create_incident(db, parsed, source="manual")
        result["incident"] = serialize(incident)

    return result
