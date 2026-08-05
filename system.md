# 🚨 AlertBot

Version: Sprint 10 Complete (Production candidate)

Author: Steve Manzi

---

# Project Overview

AlertBot is an on-call incident management and notification system built for ESICIA.

Its purpose is to monitor critical operational emails, detect infrastructure incidents, create incidents automatically, and immediately notify the on-call engineer on their phone.

The primary objective is:

> Wake the engineer during the night whenever a critical incident occurs.

The dashboard is secondary.

The phone notification is the primary feature.

---

# Final Architecture

Email (IMAP)

↓

Email Client

↓

Rule Engine

↓

Provider Parser

↓

Incident Service

↓

Notification Service

↓

Notifier (ntfy / MacroDroid / Firebase)

↓

Phone

↓

Engineer wakes up

↓

Dashboard

The Incident Service is the single source of truth.

Every notification originates from IncidentService.

---

# Current Progress

## Sprint 1 ✅ FastAPI, project structure, configuration, SQLite, scheduler

## Sprint 2 ✅ Provider-independent IMAP email engine (Gmail, Outlook, cPanel, M365, any IMAP)

## Sprint 3 ✅ Rule Engine, provider parsers (Pingdom, ESICIA Monitor, AOS, Generic), dedup, UP/DOWN recognition

## Sprint 4 ✅ Dashboard, REST API, acknowledgement, SQLite integration

## Sprint 5 ✅ Generate Test Alert

## Sprint 6 ✅ Notification Layer

- `services/notification_service.py` — provider-independent dispatch
- `services/notifiers/` — one file per channel behind one interface
  - `ntfy.py` — priority-5 push with an inline Acknowledge action
  - `macrodroid.py` — cloud webhook that drives the loud alarm macro
  - `firebase.py` — FCM to registered device tokens
- `notification_logs` table — every delivery attempt is auditable
- Called only by IncidentService

## Sprint 7 ✅ Phone alarm and escalation

- `services/escalation_service.py` — re-alerts every 2 minutes while an
  incident is OPEN, unacknowledged and not silenced
- Escalates to level 1 after 10 minutes
- Stops on acknowledge / silence / resolve
- Second scheduler job runs the cycle every 20 seconds
- `/setup` page walks through ntfy and MacroDroid configuration
- Android app in `android/` (Kotlin + FCM): full-screen alarm over the lock
  screen, max-volume alarm stream, vibration, one-tap acknowledge

## Sprint 8 ⏳ WhatsApp / Slack / SMS

The notifier interface is ready; the providers are not written.

## Sprint 9 ✅ Settings page

- Critical senders and keywords moved from `.env` into the database with CRUD
- Notification provider configuration
- Escalation timings
- Polling interval (reschedules the job live, no restart)
- Users (name, email, phone, role, notification preferences, FCM token, active)
- Registered devices
- Rule tester — paste a real email, see exactly what AlertBot would do

## Sprint 10 ✅ Analytics, history, search

- `/history` — filters by provider, state, acknowledgement and date range
- Full-text search across service, provider, reason, severity
- Pagination and CSV export
- Incidents-per-day chart, mean time to acknowledge
- `/incident/{id}` — detail page with the full delivery timeline

## New in this pass

- **PWA** — installable on Android, iPhone Safari and desktop; service worker,
  manifest, offline page, generated icons
- **Optional authentication** — HTTP Basic across every page and API route when
  `DASHBOARD_PASSWORD` is set
- **Deployment** — `render.yaml`, `Dockerfile`, `Procfile`, `.env.example`
- **PostgreSQL-ready** — portable column types, SQLite-only migrations skipped
  automatically, `DATABASE_URL` switch
- **Bug fixes** — `api/test.py` no longer creates incidents directly (it now
  goes through IncidentService, so test alerts fire the phone);
  `requirements.txt` rewritten as UTF-8; timestamps serialised as UTC

---

# Current Folder Structure

```
app/
    api/          incidents.py  test.py  settings.py  devices.py
    models/       incident  email_log  rule  app_setting  notification_log  device  user
    parsers/      (in services/parsers/) pingdom  esicia_monitor  aos  generic
    services/
        notifiers/    base  ntfy  macrodroid  firebase
        email_client.py  rule_engine.py  incident_service.py
        notification_service.py  escalation_service.py
        poller.py  settings_service.py  firebase_service.py
    static/       style.css  app.js  sw.js  manifest.webmanifest  icons/
    templates/    base  dashboard  history  incident  settings  setup  offline
    auth.py  config.py  database.py  scheduler.py  main.py
android/          Kotlin FCM alarm app
tools/            make_icons.py
render.yaml  Dockerfile  Procfile  requirements.txt  .env.example
```

---

# Database Model

Incident

provider · service · state · severity · reason · event_count · source ·
acknowledged · acknowledged_at · resolved · resolved_at ·
notify_count · last_notified_at · escalation_level · escalated_at · silenced ·
created_at · updated_at

IMPORTANT

The model uses

state

NOT

status

Other tables: email_logs, notification_logs, critical_senders, critical_keywords,
app_settings, devices, users.

---

# Critical Senders

Seeded into the database on first boot, editable from Settings:

alert@pingdom.com · monitor@esicia.site · noc@esicia.rw · support@esicia.com · innocent.ishimwe@aos.rw

---

# Critical Alert Types

Pingdom — DOWN, UP, HTTP 503, Socket timeout, Network unreachable

ESICIA Monitor — Incident OPENED, Search String Missing, HTTP Response Code != 200

AOS — Server Unreachable

---

# Notification Layer

`NotificationService.notify(incident, event)` where event is
OPENED · REPEAT · ESCALATED · RESOLVED · TEST.

Providers are separate classes implementing `BaseNotifier`:
`is_enabled()`, `config_summary()`, `send(alert) -> DeliveryResult`.

Adding WhatsApp or Slack means adding one file and registering it in
`notifiers/__init__.py`. Nothing else changes.

---

# Phone Strategy

Target device: Samsung Galaxy A15.

Android Studio does not run on the development PC, so the APK is built by
GitHub Actions (`.github/workflows/android.yml`) and side-loaded.

ntfy and MacroDroid need no build at all and work the same day.

---

# Coding Rules

Always generate complete files.

Avoid partial snippets.

Maintain existing architecture.

Keep provider parsers separated.

Keep notification providers separated.

Never duplicate incident creation logic.

IncidentService is the only source of truth.

NotificationService is called only by IncidentService.

Routes remain thin. Business logic belongs in services.

---

# Mission

The MVP is complete when:

A Pingdom DOWN email arrives → AlertBot detects it → creates an incident →
the phone wakes the engineer immediately → the engineer acknowledges →
the incident closes when the recovery email arrives.

Status: the full chain is implemented and verified end to end against a local
mock push endpoint. What remains is operational, not architectural —

1. Real IMAP credentials in `.env` (`GMAIL_EMAIL`, `GMAIL_APP_PASSWORD`).
2. An ntfy topic (or MacroDroid webhook) saved on the `/setup` page.
3. Deploy to Render so it no longer depends on the development PC.
