from app.services.notifiers.base import BaseNotifier, Alert, DeliveryResult
from app.services.notifiers.ntfy import NtfyNotifier
from app.services.notifiers.macrodroid import MacroDroidNotifier
from app.services.notifiers.firebase import FirebaseNotifier

# Order matters: the fastest, most reliable channel first.
NOTIFIERS: list[type[BaseNotifier]] = [
    NtfyNotifier,
    MacroDroidNotifier,
    FirebaseNotifier,
]

REGISTRY = {notifier.name: notifier for notifier in NOTIFIERS}


def get_notifier(name: str) -> type[BaseNotifier] | None:
    return REGISTRY.get(name)


def enabled_notifiers() -> list[type[BaseNotifier]]:
    return [notifier for notifier in NOTIFIERS if notifier.is_enabled()]


__all__ = [
    "Alert",
    "DeliveryResult",
    "BaseNotifier",
    "NOTIFIERS",
    "REGISTRY",
    "get_notifier",
    "enabled_notifiers",
]
