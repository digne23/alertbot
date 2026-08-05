from dotenv import load_dotenv
import os

load_dotenv()


def _split_list(value: str) -> list[str]:
    return [item.strip().lower() for item in value.split(",") if item.strip()]


def _bool(value: str, default: bool = False) -> bool:
    if value is None or value == "":
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


DEFAULT_CRITICAL_SENDERS = [
    "alert@pingdom.com",
    "monitor@esicia.site",
    "noc@esicia.rw",
    "support@esicia.com",
    "innocent.ishimwe@aos.rw",
]

DEFAULT_CRITICAL_KEYWORDS = [
    "down",
    "up",
    "503",
    "unreachable",
    "timeout",
    "incident opened",
    "incident closed",
    "critical",
    "server unreachable",
    "http response code",
]


class Settings:
    APP_NAME = os.getenv("APP_NAME", "AlertBot")
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///alerts.db")

    # --- Mailbox ---------------------------------------------------------
    # Any IMAP mailbox: cPanel, Gmail, Outlook, whatever. GMAIL_* are the
    # original names and still work, so existing .env files keep running.
    MAILBOX_EMAIL = os.getenv("MAILBOX_EMAIL") or os.getenv("GMAIL_EMAIL", "")
    MAILBOX_PASSWORD = os.getenv("MAILBOX_PASSWORD") or os.getenv("GMAIL_APP_PASSWORD", "")

    # Deprecated aliases, kept so nothing that reads them breaks.
    GMAIL_EMAIL = MAILBOX_EMAIL
    GMAIL_APP_PASSWORD = MAILBOX_PASSWORD

    IMAP_HOST = os.getenv("IMAP_HOST", "imap.gmail.com")
    IMAP_PORT = int(os.getenv("IMAP_PORT", 993))
    IMAP_FOLDER = os.getenv("IMAP_FOLDER", "INBOX")

    CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", 30))

    # Seed values only. Once the database is initialised these live in the
    # `critical_senders` / `critical_keywords` tables and are edited from
    # the Settings page.
    _senders_env = os.getenv("CRITICAL_SENDERS", "")
    CRITICAL_SENDERS = _split_list(_senders_env) if _senders_env else DEFAULT_CRITICAL_SENDERS

    _keywords_env = os.getenv("CRITICAL_KEYWORDS", "")
    CRITICAL_KEYWORDS = _split_list(_keywords_env) if _keywords_env else DEFAULT_CRITICAL_KEYWORDS

    # --- Notifications ---------------------------------------------------
    # Seed values for the notification providers. Editable from Settings.
    NTFY_SERVER = os.getenv("NTFY_SERVER", "https://ntfy.sh")
    NTFY_TOPIC = os.getenv("NTFY_TOPIC", "")
    NTFY_TOKEN = os.getenv("NTFY_TOKEN", "")

    MACRODROID_WEBHOOK_URL = os.getenv("MACRODROID_WEBHOOK_URL", "")

    FIREBASE_CREDENTIALS = os.getenv("FIREBASE_CREDENTIALS", "credentials/firebase.json")
    # Hosts like Render have no writable secrets file — paste the whole
    # service-account JSON into this variable instead.
    FIREBASE_CREDENTIALS_JSON = os.getenv("FIREBASE_CREDENTIALS_JSON", "")

    # --- Escalation ------------------------------------------------------
    ESCALATION_REPEAT_MINUTES = int(os.getenv("ESCALATION_REPEAT_MINUTES", 2))
    ESCALATION_AFTER_MINUTES = int(os.getenv("ESCALATION_AFTER_MINUTES", 10))
    ESCALATION_TICK_SECONDS = int(os.getenv("ESCALATION_TICK_SECONDS", 20))

    # --- Dashboard access ------------------------------------------------
    # Leave DASHBOARD_PASSWORD empty to run without a login (local use).
    # Set it before deploying anywhere public.
    DASHBOARD_USER = os.getenv("DASHBOARD_USER", "admin")
    DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "")

    # Shared key the Android app sends when registering its FCM token.
    # Empty = open registration (fine locally, set it once deployed).
    DEVICE_REGISTRATION_KEY = os.getenv("DEVICE_REGISTRATION_KEY", "")

    PUBLIC_URL = os.getenv("PUBLIC_URL", "http://127.0.0.1:8000")


settings = Settings()
