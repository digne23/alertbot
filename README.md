# 🚨 AlertBot

On-call incident management for ESICIA. Watches the alert mailbox, turns
monitoring emails into incidents, and makes a phone scream until an engineer
acknowledges.

> The phone is the product. The dashboard is the receipt.

---

## The pipeline

```
Email (IMAP)
   ↓
EmailClient          app/services/email_client.py
   ↓
RuleEngine           app/services/rule_engine.py      (DB-backed senders + keywords)
   ↓
Provider parser      app/services/parsers/*.py        (Pingdom, ESICIA Monitor, AOS, generic)
   ↓
IncidentService      app/services/incident_service.py ← the ONLY place incidents are created
   ↓
NotificationService  app/services/notification_service.py
   ↓
Notifiers            app/services/notifiers/*.py      (ntfy, MacroDroid, Firebase)
   ↓
Phone alarm  →  engineer acknowledges  →  escalation stops
```

Two rules hold the architecture together:

1. **Only `IncidentService.create_incident()` creates incidents.** Routes, the
   poller and the test-alert endpoint all go through it.
2. **Only IncidentService (and the escalation job acting for it) calls
   NotificationService.** No route ever talks to a notifier.

---

## Run it locally

```bash
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
copy .env.example .env          # then fill in the mailbox credentials
.venv\Scripts\python -m uvicorn app.main:app --reload
```

Open <http://127.0.0.1:8000>.

| Page | What it is |
|------|------------|
| `/` | Live incidents, stats, notification log, mailbox activity |
| `/history` | Search, filter by provider/state/date, CSV export |
| `/incident/{id}` | Detail view with the full delivery timeline |
| `/settings` | Senders, keywords, channels, escalation, users, rule tester |
| `/setup` | Step-by-step phone setup |

---

## Waking the engineer

Three channels sit behind one interface. Enable any combination in Settings.

### 1. ntfy — works today, no app to build

Install [ntfy](https://ntfy.sh) from the Play Store / App Store, subscribe to a
secret topic, put the topic in Settings. AlertBot POSTs with priority 5 and an
inline **Acknowledge** action. Set the topic's sound to an alarm tone and allow
it to override Do Not Disturb.

### 2. MacroDroid — the loud one

A push notification is still a notification. MacroDroid's cloud webhook trigger
runs a macro that forces the alarm stream to 100%, loops a siren, vibrates and
wakes the screen. AlertBot passes `title`, `message`, `service`, `provider`,
`severity`, `state`, `event`, `level`, `incident` and `alarm` as webhook
variables. `/setup` walks through the macro.

### 3. Firebase + the AlertBot Android app

`android/` holds a Kotlin app: FCM push → full-screen alarm over the lock
screen → one-tap acknowledge. It consumes the REST API only, no business logic.

Build it in CI (no Android Studio needed):

1. Push to GitHub.
2. **Actions → Build Android APK → Run workflow.**
3. Download the `alertbot-apk` artifact, install it on the phone.
4. Open it, enter the backend URL (and dashboard password if set), tap
   **Save and register**. The device appears under Settings → devices.
5. Enable the Firebase channel in Settings and hit its Test button.

### Repeat until acknowledged

While an incident is `OPEN`, unacknowledged and not silenced, the escalation job
re-notifies every `escalation.repeat_minutes` (default 2) and switches to
escalation level 1 after `escalation.escalate_after_minutes` (default 10).
Acknowledging, silencing or resolving stops it immediately.

---

## WhatsApp chats as an incident source

WhatsApp has no official way to read chats you are already in — Meta's Cloud API
only delivers messages sent *to a business number you own*. So the phone does the
reading: a MacroDroid macro triggers on the WhatsApp notification and forwards it
to AlertBot, which decides whether it matters.

```
WhatsApp notification → MacroDroid → GET /api/ingest/whatsapp
    → watched-chat match → IncidentService.create_incident() → alarm
```

Nothing is linked to your WhatsApp account and no third party sees the messages.

1. **Settings → WhatsApp chats:** add the chat titles exactly as WhatsApp shows
   them. Matching is case-insensitive and partial, so `Ops Team` also catches
   `Ops Team (3 messages)`. Leave keywords empty to alarm on every message, or
   list words (`down, urgent`) to ignore chit-chat.
2. **MacroDroid macro:** trigger on *Notification Received* from WhatsApp, action
   *HTTP Request (GET)* with URL encoding on:
   ```
   {PUBLIC_URL}/api/ingest/whatsapp?key={DEVICE_REGISTRATION_KEY}&chat={not_title}&message={not_text}
   ```
   `/setup` renders this with your real key filled in, ready to copy.
3. **Test it** from Settings without waiting for a message.

Incidents show up with provider `WhatsApp` and the chat as the service, so they
filter and export like any other incident. A new message in a chat whose incident
was already acknowledged re-opens it and rings again — unlike a monitor resending
the same DOWN alert, a new message is new information.

Caveat: this runs on the phone, so it needs the phone awake, online, and able to
reach AlertBot. On localhost that means the same Wi-Fi and your PC's LAN address.

## Install the dashboard as an app (PWA)

- **Android/Chrome:** ⋮ → Add to Home screen.
- **iPhone/Safari:** Share → Add to Home Screen (web push needs iOS 16.4+ and
  installed mode).
- **Desktop:** the install icon in the address bar.

Offline-safe: the shell is cached, API responses never are.

---

## Deploy to Render

The repo ships `render.yaml`. Create a Blueprint from the repo, then set the
secrets Render marks as `sync: false`:

| Variable | Why |
|----------|-----|
| `GMAIL_EMAIL`, `GMAIL_APP_PASSWORD` | mailbox access |
| `PUBLIC_URL` | so notification taps open the right dashboard |
| `NTFY_TOPIC` | your ntfy topic |
| `MACRODROID_WEBHOOK_URL` | your macro trigger |
| `FIREBASE_CREDENTIALS_JSON` | the whole service-account JSON (no file on disk) |
| `DASHBOARD_PASSWORD` | **required** — the dashboard is public otherwise |
| `DEVICE_REGISTRATION_KEY` | stops strangers registering push tokens |

Notes:

- The poller runs in-process with APScheduler, so no separate worker is needed —
  but the service must not sleep. Render's free tier idles; a paid instance is
  the difference between being woken and not.
- SQLite lives on the mounted disk at `/var/data/alerts.db`. For PostgreSQL just
  set `DATABASE_URL=postgresql+psycopg://…`; the models are portable and the
  SQLite-only ALTER migrations are skipped automatically.
- `Dockerfile` and `Procfile` are included for other hosts.

---

## Configuration

`.env` seeds the database on first boot; after that the Settings page wins, so
you can retune the system without a redeploy. See `.env.example` for every key.

| Setting | Default | Meaning |
|---------|---------|---------|
| `notifications.enabled` | on | master switch |
| `notifications.notify_on_resolve` | on | quiet push when a service recovers |
| `ntfy.*` | — | server, topic, token, priority |
| `macrodroid.*` | — | webhook URL |
| `firebase.enabled` | off | turn on once a device is registered |
| `escalation.repeat_minutes` | 2 | how often to re-alert |
| `escalation.escalate_after_minutes` | 10 | when to escalate |
| `escalation.max_repeats` | 0 | 0 = until acknowledged |
| `poll.interval_seconds` | 30 | mailbox polling |

---

## API

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/incidents` | filter by `state`, `provider`, `acknowledged`, `q`, `since`, `until`, `limit`, `offset` |
| GET | `/api/incidents/{id}` | incident + notification + source emails |
| POST | `/api/incidents/{id}/ack` | acknowledge, stops the alarm |
| POST | `/api/incidents/{id}/silence` | stop the alarm without acknowledging |
| POST | `/api/incidents/{id}/resolve` | close manually |
| GET | `/api/incidents.csv` | export the current filter |
| GET | `/api/stats` | tiles, per-day counts, channel status, MTTA |
| POST | `/api/poll` | poll the mailbox now |
| POST | `/api/test-alert` | create a test incident through IncidentService |
| POST | `/api/simulate-email` | dry-run the rules against a pasted email |
| GET/PUT | `/api/settings` | runtime configuration |
| CRUD | `/api/settings/{senders,keywords,users,devices}` | rules and people |
| POST | `/api/settings/test-notification` | fire a test push |
| GET/POST | `/api/ingest/whatsapp` | inbound WhatsApp message from the phone |
| POST/DELETE | `/api/devices` | Android token registration |
| GET | `/healthz` | unauthenticated uptime probe |

Interactive docs at `/docs`.

---

## Security

Set `DASHBOARD_PASSWORD` and every page and `/api/*` route needs HTTP Basic
credentials. Leave it empty and there is no login — fine on a laptop, not on the
internet. `/api/devices` is separately protected by `DEVICE_REGISTRATION_KEY` so
the phone can register without dashboard credentials. `/healthz` is always open.

`credentials/firebase.json` holds a private key and is gitignored. The Android
`google-services.json` holds only public client config and is committed so CI can
build.

---

## Repository layout

```
app/
  api/          incidents.py  test.py  settings.py  devices.py
  models/       incident, email_log, rule, app_setting, notification_log, device, user
  services/
    notifiers/  base.py  ntfy.py  macrodroid.py  firebase.py
    email_client.py  rule_engine.py  incident_service.py
    notification_service.py  escalation_service.py  poller.py  settings_service.py
    parsers/    pingdom, esicia_monitor, aos, generic
  templates/    base, dashboard, history, incident, settings, setup, offline
  static/       style.css  app.js  sw.js  manifest.webmanifest  icons/
  auth.py  config.py  database.py  scheduler.py  main.py
android/        Kotlin FCM alarm app
tools/          make_icons.py (regenerates the PWA icons, no dependencies)
render.yaml  Dockerfile  Procfile  requirements.txt
```

---

## Still open

- Outbound WhatsApp / Slack / SMS / email notifiers. WhatsApp currently works as
  an *input* source only; sending alerts out over WhatsApp needs a Business API
  number. The notifier interface is ready.
- Per-user routing and on-call rotation — the `users` table exists and the
  Settings page edits it, but every enabled channel still notifies everyone.
- Zabbix and UptimeRobot parsers.
- Automated tests.
