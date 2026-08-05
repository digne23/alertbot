# AlertBot — Session Summary

## Where the project stands

The whole chain now exists and was verified end to end:

```
email → rule engine → parser → IncidentService → NotificationService
      → ntfy / MacroDroid / Firebase → phone → acknowledge → escalation stops
```

Sprints 1–7, 9 and 10 of `system.md` are done. Sprint 8 (WhatsApp/Slack/SMS and
per-user routing) is not started. See `REMAINING_WORK.md`.

## Built in the latest session

**Notification layer (Sprint 6)**

- `services/notification_service.py` — provider-independent, called only by
  IncidentService.
- `services/notifiers/` — `base.py`, `ntfy.py`, `macrodroid.py`, `firebase.py`.
  Adding WhatsApp means adding one file.
- `notification_logs` table records every delivery attempt with its result.

**Escalation (Sprint 7)**

- `services/escalation_service.py` re-alerts every 2 minutes while an incident is
  open, unacknowledged and not silenced; escalates to level 1 after 10 minutes;
  stops on acknowledge, silence or resolve.
- Second APScheduler job runs the cycle every 20 seconds.

**Android app**

- `android/` — Kotlin, FCM, full-screen alarm over the lock screen, max-volume
  alarm stream, vibration, one-tap acknowledge, notification-shade ack action.
- `.github/workflows/android.yml` builds the APK in CI, since Android Studio
  will not run on the dev PC.

**Dashboard rebuild**

- Sidebar + topbar shell, dark NOC theme, responsive down to a phone.
- `/` live incidents with stat tiles, notification log and mailbox activity.
- `/history` filters, search, pagination, per-day chart, CSV export.
- `/incident/{id}` detail page with the delivery timeline and source emails.
- `/settings` senders, keywords, channels, escalation, polling, users, devices,
  and a rule tester that dry-runs a pasted email.
- `/setup` step-by-step phone configuration.
- PWA: manifest, service worker, offline page, generated icons, installable on
  Android/iOS/desktop.

**Configuration and deployment**

- Rules and settings moved from `.env` into the database, editable at runtime.
  Changing the poll interval reschedules the job without a restart.
- Optional HTTP Basic auth (`DASHBOARD_PASSWORD`) across pages and API.
- `render.yaml`, `Dockerfile`, `Procfile`, `.env.example`, README.
- PostgreSQL-ready models; SQLite-only ALTER migrations are skipped on Postgres.

## Bugs fixed

1. `api/test.py` created an `Incident` directly, bypassing IncidentService — so
   test alerts could never trigger a notification. It now goes through
   `IncidentService.create_incident()`.
2. `requirements.txt` was UTF-16-corrupted again; rewritten as UTF-8 and pinned
   to what is actually installed.
3. `services/firebase_service.py` was an empty file; the implementation now lives
   in `services/notifiers/firebase.py` with a compatibility shim.
4. Timestamps were serialised without a timezone, so the browser rendered UTC as
   local time. They are now tagged `Z`.
5. `func.date()` in the stats query was SQLite-specific; replaced with a portable
   cast.

## Verified

An end-to-end run against a local mock push endpoint (nothing sent to ntfy.sh or
Firebase) covered: page loads, test alert → push delivered with priority 5 and an
Acknowledge action, MacroDroid webhook with `alarm=1`, duplicate DOWN reusing one
incident without re-pushing, repeat alert after the interval, escalation to level
1, acknowledgement stopping the alarm, recovery resolving the incident and
sending `alarm=0`, rule tester accepting a Pingdom DOWN and rejecting normal
mail, settings/users/devices CRUD, CSV export and stats.

## Not committed

Nothing has been committed to git — your call when you want to review.
