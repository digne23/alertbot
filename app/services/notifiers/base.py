"""Provider-independent notification interface.

Every channel (ntfy, MacroDroid, Firebase, ...) implements this same contract so
NotificationService never has to know which one it is talking to.
"""

from dataclasses import dataclass, field


@dataclass
class Alert:
    """What the engineer needs to see on the lock screen at 4am."""

    incident_id: int | None
    title: str
    message: str
    provider: str = ""          # Pingdom / ESICIA Monitor / AOS ...
    service: str = ""
    severity: str = "Critical"
    reason: str = ""
    state: str = "OPEN"
    event: str = "OPENED"       # OPENED | REPEAT | ESCALATED | RESOLVED | TEST
    level: int = 0              # escalation level
    event_count: int = 1
    url: str = ""
    extra: dict = field(default_factory=dict)

    @property
    def is_alarm(self) -> bool:
        """True when this should physically wake someone up."""
        return self.event in ("OPENED", "REPEAT", "ESCALATED", "TEST")


@dataclass
class DeliveryResult:
    provider: str
    success: bool
    detail: str = ""


class BaseNotifier:
    name = "base"
    label = "Base"

    @classmethod
    def is_enabled(cls) -> bool:
        raise NotImplementedError

    @classmethod
    def config_summary(cls) -> str:
        """Short human-readable description of where this sends to."""
        return ""

    @classmethod
    def send(cls, alert: Alert) -> DeliveryResult:
        raise NotImplementedError
