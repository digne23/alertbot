import email
import logging
from datetime import datetime, timedelta, timezone
from email.header import decode_header
from email.message import Message
from email.utils import parsedate_to_datetime

from imapclient import IMAPClient
from bs4 import BeautifulSoup

from app.config import settings

logger = logging.getLogger("alertbot.email")


def _decode(value) -> str:
    if not value:
        return ""
    parts = decode_header(value)
    decoded = ""
    for text, charset in parts:
        if isinstance(text, bytes):
            decoded += text.decode(charset or "utf-8", errors="ignore")
        else:
            decoded += text
    return decoded


def _extract_body(msg: Message) -> str:
    if msg.is_multipart():
        text_part = None
        html_part = None
        for part in msg.walk():
            content_type = part.get_content_type()
            disposition = str(part.get("Content-Disposition") or "")
            if "attachment" in disposition:
                continue
            if content_type == "text/plain" and text_part is None:
                text_part = part
            elif content_type == "text/html" and html_part is None:
                html_part = part

        chosen = text_part or html_part
        if chosen is None:
            return ""
        payload = chosen.get_payload(decode=True) or b""
        charset = chosen.get_content_charset() or "utf-8"
        content = payload.decode(charset, errors="ignore")
        if chosen is html_part:
            content = BeautifulSoup(content, "html.parser").get_text(separator="\n")
        return content

    payload = msg.get_payload(decode=True) or b""
    charset = msg.get_content_charset() or "utf-8"
    content = payload.decode(charset, errors="ignore")
    if msg.get_content_type() == "text/html":
        content = BeautifulSoup(content, "html.parser").get_text(separator="\n")
    return content


def test_connection() -> dict:
    """Log in and report what is there. Used by the Test button in Settings.

    Never raises: the point is to explain why a login failed, not to crash.
    """
    result = {
        "ok": False,
        "host": settings.IMAP_HOST,
        "port": settings.IMAP_PORT,
        "email": settings.MAILBOX_EMAIL,
        "folder": settings.IMAP_FOLDER,
        "folders": [],
        "unseen": None,
        "total": None,
        "error": None,
    }

    if not settings.MAILBOX_EMAIL or not settings.MAILBOX_PASSWORD:
        result["error"] = "No mailbox credentials configured in .env"
        return result

    try:
        with IMAPClient(settings.IMAP_HOST, port=settings.IMAP_PORT,
                        use_uid=True, ssl=True) as client:
            client.login(settings.MAILBOX_EMAIL, settings.MAILBOX_PASSWORD)

            result["folders"] = sorted(
                name for _flags, _sep, name in client.list_folders()
            )

            try:
                status = client.select_folder(settings.IMAP_FOLDER)
                result["total"] = status.get(b"EXISTS")
                result["unseen"] = len(client.search(["UNSEEN"]))
            except Exception as exc:
                result["error"] = (
                    f"Connected, but folder {settings.IMAP_FOLDER!r} could not be "
                    f"opened: {exc}"
                )
                return result

            result["ok"] = True
            return result
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        return result


def _as_utc(value) -> datetime | None:
    """IMAP INTERNALDATE comes back naive on some servers, aware on others."""
    if not isinstance(value, datetime):
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _watermark_key(folder: str) -> str:
    return f"mail.uid_watermark.{folder}"


def _uidvalidity_key(folder: str) -> str:
    return f"mail.uidvalidity.{folder}"


def _parse_message(uid: int, data: dict) -> dict | None:
    raw = data.get(b"RFC822")
    if not raw:
        return None

    msg = email.message_from_bytes(raw)

    received_at = None
    try:
        received_at = parsedate_to_datetime(msg.get("Date"))
    except Exception:
        received_at = data.get(b"INTERNALDATE")

    return {
        "uid": uid,
        "message_id": (msg.get("Message-ID") or "").strip()[:250],
        "sender": _decode(msg.get("From", "")),
        "subject": _decode(msg.get("Subject", "")),
        "body": _extract_body(msg),
        "received_at": received_at,
    }


def fetch_new_emails() -> list[dict]:
    """Return messages that have arrived since the last poll.

    AlertBot keeps its own place in the mailbox using IMAP UIDs instead of the
    unread flag, because this mailbox is also read by a human. Relying on
    \\Seen would mean any alert opened on a phone first becomes invisible to
    AlertBot — precisely the mail that must not be missed.

    Consequences of the UID approach:
      * reading mail yourself changes nothing
      * AlertBot does not mark anything read (unless mail.mark_seen is on)
      * on first run it starts from the newest message rather than replaying
        the entire mailbox history
    """
    from app.services import settings_service

    if not settings.MAILBOX_EMAIL or not settings.MAILBOX_PASSWORD:
        return []

    folder = settings.IMAP_FOLDER
    results: list[dict] = []

    with IMAPClient(settings.IMAP_HOST, port=settings.IMAP_PORT, use_uid=True, ssl=True) as client:
        client.login(settings.MAILBOX_EMAIL, settings.MAILBOX_PASSWORD)
        status = client.select_folder(folder)

        uid_validity = status.get(b"UIDVALIDITY")
        stored_validity = settings_service.get(_uidvalidity_key(folder))
        watermark = settings_service.get(_watermark_key(folder)) or 0

        try:
            watermark = int(watermark)
        except (TypeError, ValueError):
            watermark = 0

        # UIDVALIDITY changing means the server renumbered the folder; every
        # stored UID is meaningless and we have to start over.
        if stored_validity is not None and uid_validity != stored_validity:
            logger.warning(
                "UIDVALIDITY for %s changed (%s -> %s) — restarting from the newest message",
                folder, stored_validity, uid_validity,
            )
            watermark = 0

        if watermark <= 0:
            # First run. A real mailbox can hold thousands of unread messages,
            # so processing "everything unread" would replay months of old
            # alerts and alarm for outages that ended long ago. Start from now,
            # and only look back if explicitly asked to.
            all_uids = client.search(["ALL"])
            highest = max(all_uids) if all_uids else 0

            try:
                lookback = int(settings_service.get("mail.first_poll_lookback_minutes") or 0)
            except (TypeError, ValueError):
                lookback = 0

            uids = []
            if lookback > 0:
                cutoff = datetime.now(timezone.utc) - timedelta(minutes=lookback)
                # IMAP SINCE only has date granularity, so narrow by date and
                # then filter precisely on the server's INTERNALDATE.
                candidates = client.search(["SINCE", cutoff.date()])
                if candidates:
                    dates = client.fetch(candidates, ["INTERNALDATE"])
                    uids = [
                        uid for uid, data in dates.items()
                        if _as_utc(data.get(b"INTERNALDATE")) and _as_utc(data[b"INTERNALDATE"]) >= cutoff
                    ]

            logger.info(
                "First poll of %s: %s existing message(s) left alone, starting at UID %s"
                " (lookback %s min, %s message(s) to process)",
                folder, len(all_uids), highest, lookback, len(uids),
            )
        else:
            # '<n>:*' can return the last message even when its UID is lower,
            # so filter client-side rather than trusting the range.
            uids = [u for u in client.search(["UID", f"{watermark + 1}:*"]) if u > watermark]
            highest = max(uids) if uids else watermark

        if uids:
            response = client.fetch(uids, ["RFC822", "INTERNALDATE"])
            for uid, data in sorted(response.items()):
                parsed = _parse_message(uid, data)
                if parsed:
                    results.append(parsed)

            if settings_service.get("mail.mark_seen"):
                client.add_flags(uids, [b"\\Seen"])

        settings_service.set_many({
            _watermark_key(folder): int(max(highest, watermark)),
            _uidvalidity_key(folder): uid_validity,
        })

    return results


# Older name, kept so anything still calling it keeps working.
fetch_unseen_emails = fetch_new_emails
