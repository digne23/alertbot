"""Read-only look at recent mail: what would AlertBot have done?

    python tools/scan_recent.py [count]

Fetches the newest messages, runs the rule engine and parsers over them, and
prints the verdict. Creates no incidents, sends no notifications and changes no
flags — it is purely a way to check the rules against real mail before trusting
them.
"""

import sys

sys.path.insert(0, ".")

from imapclient import IMAPClient          # noqa: E402

from app.config import settings            # noqa: E402
from app.services.email_client import _decode, _extract_body   # noqa: E402
from app.services.parsers import get_parser                     # noqa: E402
from app.services.rule_engine import explain                    # noqa: E402
import email as email_module               # noqa: E402


def main() -> int:
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 40

    if not settings.MAILBOX_EMAIL or not settings.MAILBOX_PASSWORD:
        print("No mailbox credentials in .env")
        return 1

    print(f"Scanning the newest {count} message(s) in {settings.IMAP_FOLDER} "
          f"as {settings.MAILBOX_EMAIL}")
    print("Read-only: nothing is created, sent or marked read.\n")

    with IMAPClient(settings.IMAP_HOST, port=settings.IMAP_PORT,
                    use_uid=True, ssl=True) as client:
        client.login(settings.MAILBOX_EMAIL, settings.MAILBOX_PASSWORD)
        client.select_folder(settings.IMAP_FOLDER, readonly=True)

        uids = sorted(client.search(["ALL"]))[-count:]
        if not uids:
            print("Mailbox is empty.")
            return 0

        response = client.fetch(uids, ["RFC822"])

        alerts = 0
        for uid in sorted(response, reverse=True):
            raw = response[uid].get(b"RFC822")
            if not raw:
                continue

            msg = email_module.message_from_bytes(raw)
            sender = _decode(msg.get("From", ""))
            subject = _decode(msg.get("Subject", ""))
            body = _extract_body(msg)

            verdict = explain(sender, subject, body)
            if not verdict["critical"]:
                continue

            alerts += 1
            parser = get_parser(sender)
            parsed = parser.parse(sender, subject, body)

            print(f"ALERT  uid {uid}")
            print(f"       from    {sender[:70]}")
            print(f"       subject {subject[:70]}")
            print(f"       parser  {parser.provider_name}")
            print(f"       service {parsed['service']}   state {parsed['state']}")
            print(f"       reason  {parsed['reason']}")
            print(f"       matched {', '.join(verdict['matched_keywords'])}")
            print()

        print(f"{alerts} of the last {len(uids)} message(s) would have raised an alert.")
        if not alerts:
            print(
                "\nNo alerts in that window. Either nothing broke recently, or the\n"
                "alerts come from a sender not on the critical list. Try a larger\n"
                "count, or check Settings -> critical senders."
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
