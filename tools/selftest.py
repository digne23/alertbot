"""AlertBot self-test — proves the whole pipeline works, offline.

    python tools/selftest.py

Runs the real code paths (routes, rule engine, IncidentService, escalation,
WhatsApp ingest) but points the notification channels at a throwaway HTTP
server on localhost. Nothing is sent to ntfy.sh, MacroDroid, Firebase or your
mailbox, and no test data is left behind.

Exit code 0 = everything passed.
"""

import sys
import threading
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.path.insert(0, ".")

RECEIVED: list[dict] = []
SERVICE = "selftest.esicia.rw"
CHAT = "SELFTEST CHAT"


class MockPhone(BaseHTTPRequestHandler):
    """Stands in for the phone: records what would have been delivered."""

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        RECEIVED.append({
            "method": "POST",
            "path": self.path,
            "headers": dict(self.headers),
            "body": self.rfile.read(length).decode("utf-8", "ignore"),
        })
        self._ok()

    def do_GET(self):
        RECEIVED.append({"method": "GET", "path": self.path, "headers": dict(self.headers)})
        self._ok()

    def _ok(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *args):
        pass


results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, bool(ok), detail))
    mark = "PASS" if ok else "FAIL"
    print(f"  {mark}  {name}" + (f"   [{detail}]" if detail else ""))


def section(title: str) -> None:
    print(f"\n{title}")
    print("-" * len(title))


def main() -> int:
    server = HTTPServer(("127.0.0.1", 0), MockPhone)
    port = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()
    mock = f"http://127.0.0.1:{port}"

    from fastapi.testclient import TestClient

    from app.api import app_auth
    from app.config import settings as env
    from app.database import SessionLocal, init_db
    from app.main import app
    from app.models.email_log import EmailLog
    from app.models.incident import Incident
    from app.models.notification_log import NotificationLog
    from app.models.watched_chat import WatchedChat
    from app.services import settings_service
    from app.services.escalation_service import run_escalation_cycle

    init_db()

    def purge():
        db = SessionLocal()
        for incident in db.query(Incident).filter(Incident.service.in_([SERVICE, CHAT])).all():
            db.query(NotificationLog).filter(
                NotificationLog.incident_id == incident.id).delete()
            db.delete(incident)
        db.query(EmailLog).filter(EmailLog.sender.like(f"%{CHAT}%")).delete(
            synchronize_session=False)
        db.query(WatchedChat).filter(WatchedChat.name == CHAT).delete(
            synchronize_session=False)
        db.commit()
        db.close()

    keys = ("notifications.enabled", "notifications.notify_on_resolve",
            "ntfy.enabled", "ntfy.server", "ntfy.topic", "ntfy.token",
            "macrodroid.enabled", "macrodroid.webhook_url", "firebase.enabled",
            "escalation.enabled", "escalation.repeat_minutes")
    saved = {key: settings_service.get(key) for key in keys}

    print(f"AlertBot self-test — mock phone listening on {mock}")
    print("No message leaves this machine.\n")

    try:
        purge()
        settings_service.set_many({
            "notifications.enabled": True,
            "notifications.notify_on_resolve": True,
            "ntfy.enabled": True,
            "ntfy.server": mock,
            "ntfy.topic": "selftest",
            "ntfy.token": "",
            "macrodroid.enabled": True,
            "macrodroid.webhook_url": f"{mock}/macro",
            "escalation.enabled": True,
            "escalation.repeat_minutes": 1,
        })

        with TestClient(app) as client:
            if env.DASHBOARD_PASSWORD:
                client.auth = (env.DASHBOARD_USER, env.DASHBOARD_PASSWORD)

            def ours(method: str) -> list[dict]:
                """Deliveries for this test only — real incidents may also be
                escalating in the background."""
                return [hit for hit in RECEIVED
                        if hit["method"] == method and (SERVICE in str(hit) or CHAT in str(hit))]

            # ---------------------------------------------------------------
            section("1. Every page loads")
            for path in ("/", "/history", "/settings", "/setup", "/healthz",
                         "/manifest.webmanifest", "/sw.js", "/static/style.css",
                         "/static/icons/icon-192.png"):
                response = client.get(path)
                check(f"GET {path}", response.status_code == 200, f"HTTP {response.status_code}")

            # ---------------------------------------------------------------
            section("2. Login protects the dashboard")
            if env.DASHBOARD_PASSWORD:
                bare = TestClient(app)
                check("dashboard requires a password", bare.get("/").status_code == 401)
                check("API requires a password", bare.get("/api/incidents").status_code == 401)
                check("health probe stays open", bare.get("/healthz").status_code == 200)
            else:
                check("dashboard is unprotected (DASHBOARD_PASSWORD empty)", True,
                      "set it before deploying")

            # ---------------------------------------------------------------
            section("2b. The phone signs in with a name and a PIN")
            # Staff have no dashboard password. They type a name and a PIN; the
            # server hands back the registration key, which then stands in for
            # the password on the endpoints the app needs — and on nothing else.
            bare = TestClient(app)
            real_pin, real_key = env.APP_PIN, env.DEVICE_REGISTRATION_KEY
            try:
                env.APP_PIN = "selftest-pin-9174"
                env.DEVICE_REGISTRATION_KEY = "selftest-key-3382"
                app_auth._failures.clear()

                good = bare.post("/api/app/signin",
                                 json={"name": "Selftest phone", "pin": env.APP_PIN})
                check("correct PIN signs in", good.status_code == 200,
                      f"HTTP {good.status_code}")
                issued = good.json().get("key", "") if good.status_code == 200 else ""
                check("sign-in hands back the registration key",
                      issued == env.DEVICE_REGISTRATION_KEY)

                check("wrong PIN is refused",
                      bare.post("/api/app/signin",
                                json={"name": "x", "pin": "wrong"}).status_code == 401)

                key_header = {"X-Registration-Key": issued}
                check("the key opens the alert list",
                      bare.get("/api/incidents", headers=key_header).status_code == 200)
                # Only meaningful when the dashboard actually has a password —
                # without one every endpoint is open and this proves nothing.
                if env.DASHBOARD_PASSWORD:
                    check("the key does not open settings",
                          bare.get("/api/settings/users", headers=key_header).status_code == 401)

                app_auth._failures.clear()
                env.APP_PIN = ""
                check("no PIN configured means no sign-in",
                      bare.post("/api/app/signin",
                                json={"name": "x", "pin": "y"}).status_code == 503)
            finally:
                env.APP_PIN, env.DEVICE_REGISTRATION_KEY = real_pin, real_key
                app_auth._failures.clear()

            # ---------------------------------------------------------------
            section("3. An alert reaches the phone")
            RECEIVED.clear()
            response = client.post("/api/test-alert", json={
                "provider": "Pingdom", "service": SERVICE,
                "reason": "HTTP Server Error 503 Service Unavailable", "state": "OPEN",
            })
            check("test alert accepted", response.status_code == 200, f"HTTP {response.status_code}")
            incident_id = response.json().get("incident_id")

            pushes, webhooks = ours("POST"), ours("GET")
            check("ntfy push delivered", len(pushes) == 1, f"{len(pushes)} received")
            check("push priority is max (rings a silent phone)",
                  bool(pushes) and pushes[0]["headers"].get("Priority") == "5")
            check("push offers Acknowledge",
                  bool(pushes) and "Acknowledge" in pushes[0]["headers"].get("Actions", ""))
            check("MacroDroid alarm fired", len(webhooks) == 1, f"{len(webhooks)} received")
            check("MacroDroid told to alarm", bool(webhooks) and "alarm=1" in webhooks[0]["path"])

            # ---------------------------------------------------------------
            section("4. Repeated alerts do not machine-gun the phone")
            client.post("/api/test-alert", json={
                "provider": "Pingdom", "service": SERVICE,
                "reason": "HTTP Server Error 503", "state": "OPEN",
            })
            check("duplicate reuses one incident", len(ours("POST")) == 1,
                  f"{len(ours('POST'))} pushes total")
            detail = client.get(f"/api/incidents/{incident_id}").json()
            check("but the event is counted", detail["event_count"] == 2,
                  str(detail["event_count"]))

            # ---------------------------------------------------------------
            section("5. It keeps ringing until acknowledged")
            db = SessionLocal()
            incident = db.query(Incident).filter(Incident.id == incident_id).first()
            incident.last_notified_at = datetime.utcnow() - timedelta(minutes=5)
            incident.created_at = datetime.utcnow() - timedelta(minutes=3)
            db.commit()
            db.close()

            RECEIVED.clear()
            run_escalation_cycle()
            check("unacknowledged incident re-alerts", len(ours("POST")) >= 1,
                  f"{len(ours('POST'))} pushes")
            check("repeat is labelled STILL DOWN",
                  bool(ours("POST")) and "STILL DOWN" in ours("POST")[0]["headers"].get("Title", ""),
                  ours("POST")[0]["headers"].get("Title", "") if ours("POST") else "-")

            db = SessionLocal()
            incident = db.query(Incident).filter(Incident.id == incident_id).first()
            incident.last_notified_at = datetime.utcnow() - timedelta(minutes=5)
            incident.created_at = datetime.utcnow() - timedelta(minutes=45)
            db.commit()
            db.close()

            RECEIVED.clear()
            run_escalation_cycle()
            check("escalates when ignored too long",
                  bool(ours("POST")) and "ESCALATED" in ours("POST")[0]["headers"].get("Title", ""),
                  ours("POST")[0]["headers"].get("Title", "") if ours("POST") else "-")

            # ---------------------------------------------------------------
            section("6. Acknowledging silences it")
            check("acknowledge accepted",
                  client.post(f"/api/incidents/{incident_id}/ack").status_code == 200)

            db = SessionLocal()
            incident = db.query(Incident).filter(Incident.id == incident_id).first()
            incident.last_notified_at = datetime.utcnow() - timedelta(minutes=30)
            db.commit()
            db.close()

            RECEIVED.clear()
            run_escalation_cycle()
            check("alarm stops after acknowledgement", not ours("POST"),
                  f"{len(ours('POST'))} pushes")

            # ---------------------------------------------------------------
            section("7. Recovery closes the incident")
            RECEIVED.clear()
            response = client.post("/api/test-alert", json={
                "provider": "Pingdom", "service": SERVICE, "state": "RESOLVED",
                "reason": "UP again",
            })
            check("recovery resolves it", response.json()["incident"]["state"] == "RESOLVED")
            check("phone told to stop the alarm",
                  bool(ours("GET")) and "alarm=0" in ours("GET")[0]["path"])

            # ---------------------------------------------------------------
            section("8. The rules match the right mail")
            response = client.post("/api/simulate-email", json={
                "sender": "alert@pingdom.com",
                "subject": f"DOWN alert: {SERVICE} is DOWN",
                "body": "HTTP Server Error 503 Service Unavailable",
            })
            check("a Pingdom DOWN raises an alert", response.json()["critical"])
            check("the Pingdom parser is chosen", response.json()["parser"] == "Pingdom",
                  response.json()["parser"])

            response = client.post("/api/simulate-email", json={
                "sender": "customer@example.com",
                "subject": "Question about support",
                "body": "Nothing is broken, just asking.",
            })
            check("normal mail is ignored", not response.json()["critical"])

            # ---------------------------------------------------------------
            section("9. WhatsApp chats raise incidents")
            client.post("/api/settings/chats", json={"name": CHAT, "label": CHAT})

            RECEIVED.clear()
            response = client.get("/api/ingest/whatsapp", params={
                "chat": f"{CHAT} (2 messages)", "message": "Server room UPS is beeping",
                "key": env.DEVICE_REGISTRATION_KEY,
            })
            check("watched chat raises an incident",
                  response.json().get("action") == "incident_created", str(response.json()))
            check("WhatsApp message reaches the phone", len(ours("POST")) == 1,
                  f"{len(ours('POST'))} pushes")

            response = client.get("/api/ingest/whatsapp", params={
                "chat": "Some other chat", "message": "hello",
                "key": env.DEVICE_REGISTRATION_KEY,
            })
            check("unwatched chat is ignored",
                  response.json().get("action") == "not_watched", str(response.json()))

            if env.DEVICE_REGISTRATION_KEY:
                check("ingest rejects a wrong key",
                      client.get("/api/ingest/whatsapp",
                                 params={"chat": CHAT, "message": "x", "key": "wrong"}
                                 ).status_code == 401)

            # ---------------------------------------------------------------
            section("10. Dashboard data")
            stats = client.get("/api/stats").json()
            check("stats load", "open" in stats and "per_day" in stats)
            check("CSV export works",
                  client.get("/api/incidents.csv?state=ALL").status_code == 200)
            check("history filters by provider",
                  client.get("/api/incidents?provider=WhatsApp&state=ALL").status_code == 200)

            # ---------------------------------------------------------------
            section("11. Live configuration")
            health = client.get("/api/health").json()
            check("mailbox credentials present", health["mailbox_configured"],
                  "" if health["mailbox_configured"]
                  else "set MAILBOX_EMAIL / MAILBOX_PASSWORD in .env")

            # Deliberately reads the SAVED settings, not the live ones: the
            # live ones are this test's mock, and checking those would only
            # prove the test configured itself.
            real_channels = []
            if saved.get("ntfy.enabled") and saved.get("ntfy.topic"):
                real_channels.append("ntfy")
            if saved.get("macrodroid.enabled") and saved.get("macrodroid.webhook_url"):
                real_channels.append("macrodroid")
            if settings_service.defaults().get("firebase.enabled") is not None:
                if saved.get("firebase.enabled"):
                    real_channels.append("firebase")

            check("a real notification channel is configured", bool(real_channels),
                  ", ".join(real_channels) if real_channels
                  else "no phone channel yet — set an ntfy topic on /setup")

    finally:
        purge()
        settings_service.set_many(saved)
        server.shutdown()

    failed = [name for name, ok, _ in results if not ok]
    total = len(results)
    print("\n" + "=" * 60)
    print(f"{total - len(failed)}/{total} checks passed")
    if failed:
        print("\nFailed:")
        for name in failed:
            print(f"  - {name}")
        print("\nA failure in section 11 usually just means configuration is "
              "still missing, not that the code is broken.")
    else:
        print("Everything works. Real settings and data were restored.")
    print("=" * 60)

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
