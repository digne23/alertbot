# AlertBot — working notes

On-call incident management for ESICIA. Watches a mailbox and two WhatsApp
chats, raises incidents, and makes a phone scream until an engineer
acknowledges.

**The phone is the product. The dashboard is the receipt.** When a trade-off
appears, favour "the engineer gets woken" over anything else.

Owner: Steve Manzi (`digne@esicia.rw`). Spec and sprint history: `system.md`.
Manual and automated test procedure: `TESTING.md`.

---

## Two rules that must never be broken

1. **Only `IncidentService.create_incident()` creates incidents.** Routes, the
   email poller, WhatsApp ingest and the test-alert endpoint all go through it.
   A route that writes an `Incident` directly is a bug — it silently skips
   notification, which is the entire point of the system. This has already
   happened once (`app/api/test.py`, fixed).
2. **Only IncidentService calls NotificationService.** The escalation job is
   the one exception, and it acts on IncidentService's behalf.

Keep routes thin, business logic in services, one file per notification
provider and per email parser.

---

## Shape of the thing

```
Email (IMAP)  ─┐
               ├→ RuleEngine → Parser → IncidentService → NotificationService
WhatsApp      ─┘                             │                    │
(phone → ingest)                             ↓                    ↓
                                         SQLite            ntfy / MacroDroid / Firebase
                                             │                    │
                                        Dashboard              Phone alarm
                                                                  │
                                              EscalationService repeats every 2 min
                                              until acknowledged, escalates at 10
```

```
app/
  api/         incidents · test · settings · devices · ingest
  models/      incident · email_log · rule · app_setting · notification_log
               device · user · watched_chat
  services/
    notifiers/ base · ntfy · macrodroid · firebase      (one file per channel)
    parsers/   pingdom · esicia_monitor · aos · generic (one file per provider)
    email_client · rule_engine · incident_service · notification_service
    escalation_service · poller · whatsapp_service · settings_service
  templates/   base · dashboard · history · incident · settings · setup · offline
  static/      style.css · app.js · sw.js · manifest.webmanifest · icons/
  auth.py · config.py · database.py · scheduler.py · main.py
android/       Kotlin FCM alarm app, built by GitHub Actions
tools/         selftest · check_mailbox · scan_recent · make_icons
```

The model uses **`state`**, never `status`.

---

## Non-obvious decisions, and why

- **The mailbox is a human's personal inbox** (`digne@esicia.rw`, 3000+
  messages, most unread). So AlertBot tracks its own position by **IMAP UID
  watermark** in `app_settings`, and does not touch the `\Seen` flag. Fetching
  `UNSEEN` and marking read would mean any alert he opened on his phone first
  became invisible to AlertBot — losing exactly the mail that matters.
  `mail.mark_seen` restores the old behaviour for a dedicated mailbox.
- **First poll starts from now** (`mail.first_poll_lookback_minutes`, default
  0). With thousands of unread messages, replaying them would alarm for
  outages that ended months ago.
- **Message-ID is recorded** for every processed mail, so a lost watermark
  cannot raise the same incident twice.
- **A repeat DOWN email does not re-notify.** The escalation job owns the
  repeat alarm, so a flapping monitor cannot machine-gun the phone. WhatsApp is
  the exception: `reopen_on_repeat=True`, because a new message is genuinely
  new information and must ring again even after acknowledgement.
- **ntfy headers are transliterated to ASCII.** An em dash in a title raised
  `UnicodeEncodeError` and killed every push. Bodies stay UTF-8.
- **Stats group per-day in Python**, not SQL — `CAST(... AS DATE)` and
  `strftime` differ between SQLite and PostgreSQL.
- **WhatsApp is an input, not an output.** There is no official way to read
  chats you are already in; Meta's Cloud API only receives mail sent to a
  business number you own. So the phone forwards its own notifications via
  MacroDroid to `/api/ingest/whatsapp`. Sending alerts *out* over WhatsApp is
  unbuilt and needs a Business API number.
- **Chat titles match case-insensitively and partially**, because Android
  decorates them (`Ops Team (3 messages)`).
- **Auth is optional HTTP Basic**, enabled by setting `DASHBOARD_PASSWORD`.
  `/healthz` stays open for uptime probes; `/api/ingest/*` and `/api/devices`
  use `DEVICE_REGISTRATION_KEY` instead, so the phone can call them with a
  plain URL.

---

## Running and testing

```
.venv\Scripts\python run.py                  # binds 0.0.0.0 so the phone can reach it
.venv\Scripts\python tools\selftest.py       # whole pipeline, offline, ~1 min
.venv\Scripts\python tools\check_mailbox.py  # IMAP login, folders, unread count
.venv\Scripts\python tools\scan_recent.py 100  # read-only: what would the rules do?
```

`selftest.py` points the channels at a throwaway localhost server, restores the
real settings afterwards and deletes its own data. Run it after any change.
Section 11 reports missing *configuration* rather than broken code.

There is no pytest suite yet — `selftest.py` is the safety net. Converting it
to pytest is a worthwhile piece of work.

---

## Current state (2026-08-05)

Working and verified: email pipeline, rule engine, four parsers, incident
dedup, notification layer with three channels, repeat-until-acknowledged,
escalation, WhatsApp ingest, dashboard, history/search/CSV, settings, PWA,
optional auth, Android app source.

Configured: mailbox `digne@esicia.rw` on `mail.esicia.rw:993` (connection
verified), watched chats `esicia team` and `vubavuba africa`, dashboard auth on,
`PUBLIC_URL` pointing at the LAN address `192.168.2.131:8000`.

**Blocking a working alarm:** no notification channel is configured yet. The
user must install ntfy, subscribe to a topic and save it on `/setup`, and paste
the MacroDroid webhook URL. Until then incidents are recorded silently — the
dashboard shows a red banner saying so.

Not built: outbound WhatsApp/Slack/SMS/email notifiers (the interface is ready,
one file each), per-user routing and on-call rotation (the `users` table and its
UI exist but every channel still notifies everyone), Zabbix and UptimeRobot
parsers, pytest suite, deployment.

Deployment is deliberately deferred — the user chose to run locally for now.
`render.yaml`, `Dockerfile` and `Procfile` are ready. A free tier that sleeps is
useless here: a sleeping AlertBot notices nothing.

---

## Watch out

- **The git repo rooted at `C:\Users\user`** is a stray: no commits, and its
  `origin` points at an unrelated project (`digne23/AidVault`). Never commit
  from there — it would stage the whole user profile. AlertBot's own repo is
  `github.com/digne23/alertbot` (private), rooted at the project directory.
- `.env` holds live credentials and is gitignored, as is
  `credentials/firebase.json`. `android/app/google-services.json` is committed
  on purpose: it is public client config and the CI build needs it.
- This machine cannot run Android Studio, so the APK is built by
  `.github/workflows/android.yml`.
- Commands here are slow (a bare `import app.main` can take a minute). Prefer
  background execution with generous timeouts over assuming a hang.
- Long terminal output gets truncated on the user's screen. Keep answers short
  and put the important line first.
