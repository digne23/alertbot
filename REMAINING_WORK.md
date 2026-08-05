# AlertBot — What's Left

Everything in `system.md` Sprints 1–7, 9 and 10 is built. This file tracks only
what is still open, and what only you can do.

## 1. Two things block "it wakes me tonight"

Both are credentials, not code.

1. **Mailbox** — `.env` still has empty `GMAIL_EMAIL` / `GMAIL_APP_PASSWORD`.
   Without them the poller connects to nothing and silently returns 0 emails.
   Needs a Gmail App Password with IMAP enabled (or the real mailbox login for
   info@esicia.rw / domain@esicia.com).
2. **A phone channel** — open `/setup`, generate an ntfy topic, subscribe to it
   in the ntfy app, save it. That is the whole setup. Everything downstream is
   already wired and tested.

## 2. Deployment

Nothing is deployed yet. `render.yaml` is ready — create a Blueprint from the
repo and set the secrets listed in the README.

Two things to get right:

- Do not use a free instance that sleeps; a sleeping AlertBot notices nothing.
- `DASHBOARD_PASSWORD` must be set before the URL is public. Without it the
  dashboard and API are open to anyone.

## 3. Android app

The Kotlin source is complete in `android/`, but no APK has been built or
installed. Push to GitHub, run the **Build Android APK** action, install the
artifact, register the device, enable the Firebase channel.

Until then Firebase stays disabled — it has no device token to push to.

## 4. Sprint 8 — not started

- WhatsApp, Slack, SMS and email notifiers. The interface is ready: add one file
  under `app/services/notifiers/`, register it in `__init__.py`.
- Per-user routing / on-call rotation. The `users` table and its Settings UI
  exist, but every enabled channel currently notifies everyone.

## 5. Parsers

- Zabbix and UptimeRobot parsers are not written.
- `GenericParser` is a fallback, not tuned to any real provider.

## 6. Hardening

- No automated test suite. The pipeline was verified end to end against a local
  mock push endpoint, but that check is not committed as a test.
- No retry/backoff if IMAP times out mid-poll — the poll is skipped and retried
  on the next tick, which is acceptable but not ideal.
- `EmailLog.body` is truncated to 5000 characters; there is no raw archive.
- SQLite has no migration tool. Column additions are handled by the ALTER
  helper in `database.py`; anything more complex needs Alembic or a move to
  PostgreSQL.

## Order of attack

1. Mailbox credentials → confirm the poller pulls a real alert.
2. ntfy topic on `/setup` → confirm the phone rings.
3. Deploy to Render, set `PUBLIC_URL` and `DASHBOARD_PASSWORD`.
4. Build and install the Android app for the loud full-screen alarm.
5. Then Sprint 8 (WhatsApp, per-user routing) and the extra parsers.
