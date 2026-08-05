"""Firebase Cloud Messaging channel.

FCM can only deliver to a registration token produced by an installed Android
app (package `com.alertbot.mobile`). Until that app exists this provider stays
disabled — register tokens via POST /api/devices and flip `firebase.enabled`
on the Settings page once you have one.

The alarm behaviour lives in the message payload: an `alarm` data field the app
reads, plus an Android channel id so the phone uses the loud alarm channel.
"""

import logging
import os
import threading

from app.config import settings as env
from app.database import SessionLocal
from app.models.device import Device
from app.models.user import User
from app.services import settings_service
from app.services.notifiers.base import BaseNotifier, Alert, DeliveryResult

logger = logging.getLogger("alertbot.notifiers.firebase")

_init_lock = threading.Lock()
_app = None
_init_error = ""


def _get_app():
    """Initialise firebase-admin once, lazily. Returns None if unavailable."""
    global _app, _init_error

    with _init_lock:
        if _app is not None:
            return _app
        try:
            import firebase_admin
            from firebase_admin import credentials

            if firebase_admin._apps:
                _app = firebase_admin.get_app()
                return _app

            # On Render (and any host without a writable secrets file) the
            # whole service-account JSON is passed in an env var instead.
            raw = (env.FIREBASE_CREDENTIALS_JSON or "").strip()
            if raw:
                import json
                cert = credentials.Certificate(json.loads(raw))
            else:
                path = env.FIREBASE_CREDENTIALS
                if not path or not os.path.exists(path):
                    _init_error = f"service account file not found: {path}"
                    return None
                cert = credentials.Certificate(path)

            _app = firebase_admin.initialize_app(cert)
            _init_error = ""
            return _app
        except Exception as exc:
            _init_error = f"{type(exc).__name__}: {exc}"
            logger.warning("Firebase init failed: %s", _init_error)
            return None


def active_tokens() -> list[tuple[str, str]]:
    """Every FCM token we should push to, as (token, label) pairs.

    Tokens come from registered devices and from users who have a token saved
    and push enabled. Duplicates are collapsed.
    """
    db = SessionLocal()
    try:
        tokens: dict[str, str] = {}

        for device in db.query(Device).filter(Device.enabled.is_(True)).all():
            if device.token:
                tokens.setdefault(device.token, device.label or device.platform or "device")

        for user in db.query(User).filter(
            User.active.is_(True), User.notify_push.is_(True)
        ).all():
            if user.fcm_token:
                tokens.setdefault(user.fcm_token, user.name or user.email)

        return list(tokens.items())
    finally:
        db.close()


class FirebaseNotifier(BaseNotifier):
    name = "firebase"
    label = "Firebase (FCM)"

    @classmethod
    def is_enabled(cls) -> bool:
        return bool(settings_service.get("firebase.enabled"))

    @classmethod
    def config_summary(cls) -> str:
        count = len(active_tokens())
        if _init_error:
            return f"{count} device(s) — {_init_error}"
        return f"{count} registered device token(s)"

    @classmethod
    def send(cls, alert: Alert) -> DeliveryResult:
        if not cls.is_enabled():
            return DeliveryResult(cls.name, False, "Firebase is not enabled")

        app = _get_app()
        if app is None:
            return DeliveryResult(cls.name, False, _init_error or "firebase-admin unavailable")

        targets = active_tokens()
        if not targets:
            return DeliveryResult(cls.name, False, "no registered device tokens")

        try:
            from firebase_admin import messaging
        except Exception as exc:
            return DeliveryResult(cls.name, False, f"firebase-admin import failed: {exc}")

        data = {
            "incident_id": str(alert.incident_id or 0),
            "title": alert.title,
            "message": alert.message,
            "service": alert.service,
            "provider": alert.provider,
            "severity": alert.severity,
            "state": alert.state,
            "event": alert.event,
            "level": str(alert.level),
            "alarm": "1" if alert.is_alarm else "0",
        }

        android = messaging.AndroidConfig(
            priority="high",
            ttl=300,
            notification=messaging.AndroidNotification(
                title=alert.title,
                body=alert.message,
                channel_id="alertbot_alarm" if alert.is_alarm else "alertbot_info",
                sound="alarm" if alert.is_alarm else "default",
                priority="max",
            ),
        )

        sent, failures = 0, []
        for token, label in targets:
            message = messaging.Message(
                token=token,
                data=data,
                android=android,
                notification=messaging.Notification(title=alert.title, body=alert.message),
            )
            try:
                messaging.send(message)
                sent += 1
            except Exception as exc:
                failures.append(f"{label or token[:12]}: {exc}")

        if sent == 0:
            return DeliveryResult(cls.name, False, "; ".join(failures)[:400])
        detail = f"sent to {sent}/{len(targets)} device(s)"
        if failures:
            detail += " — " + "; ".join(failures)[:300]
        return DeliveryResult(cls.name, True, detail)
