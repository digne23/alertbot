"""Check the IMAP mailbox from the command line.

    python tools/check_mailbox.py

Prints whether the login works, which folders exist and how much unread mail is
waiting. Run it before starting the server — it answers "are the credentials
right?" without any of the rest of AlertBot getting involved.
"""

import sys

sys.path.insert(0, ".")

from app.config import settings          # noqa: E402
from app.services.email_client import test_connection   # noqa: E402


def main() -> int:
    print(f"Host    : {settings.IMAP_HOST}:{settings.IMAP_PORT}")
    print(f"Mailbox : {settings.MAILBOX_EMAIL or '(not configured)'}")
    print(f"Folder  : {settings.IMAP_FOLDER}")
    print("Connecting...\n")

    result = test_connection()

    if not result["ok"]:
        print(f"FAILED: {result['error']}")
        if result["folders"]:
            print("\nFolders on the server:")
            for name in result["folders"]:
                print(f"  - {name}")
            print("\nIf the alerts live in one of those, set IMAP_FOLDER in .env.")
        return 1

    print(f"OK — connected as {result['email']}")
    print(f"{result['folder']}: {result['total']} message(s), {result['unseen']} unread")
    print("\nFolders on the server:")
    for name in result["folders"]:
        print(f"  - {name}")

    if not result["unseen"]:
        print(
            "\nNothing unread. AlertBot only processes UNREAD mail, so if the "
            "alerts have already been opened it will not see them."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
