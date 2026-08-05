import email
from email.header import decode_header
from email.utils import parsedate_to_datetime

from imapclient import IMAPClient
from bs4 import BeautifulSoup

from app.config import settings


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


def _extract_body(msg: email.message.Message) -> str:
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


def fetch_unseen_emails() -> list[dict]:
    """Connect via IMAP, fetch unseen emails, mark them seen, return parsed dicts."""
    if not settings.GMAIL_EMAIL or not settings.GMAIL_APP_PASSWORD:
        return []

    results = []

    with IMAPClient(settings.IMAP_HOST, port=settings.IMAP_PORT, use_uid=True, ssl=True) as client:
        client.login(settings.GMAIL_EMAIL, settings.GMAIL_APP_PASSWORD)
        client.select_folder(settings.IMAP_FOLDER)

        uids = client.search(["UNSEEN"])
        if not uids:
            return []

        response = client.fetch(uids, ["RFC822", "INTERNALDATE"])

        for uid, data in response.items():
            raw = data.get(b"RFC822")
            if not raw:
                continue
            msg = email.message_from_bytes(raw)

            sender = _decode(msg.get("From", ""))
            subject = _decode(msg.get("Subject", ""))
            body = _extract_body(msg)

            received_at = None
            try:
                received_at = parsedate_to_datetime(msg.get("Date"))
            except Exception:
                received_at = data.get(b"INTERNALDATE")

            results.append({
                "uid": uid,
                "sender": sender,
                "subject": subject,
                "body": body,
                "received_at": received_at,
            })

            client.add_flags(uid, [b"\\Seen"])

    return results
