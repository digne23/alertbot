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
- **Staff sign into the app with a name and a shared PIN**, never the admin
  password — non-technical users have neither a server URL nor a dashboard
  login, and requiring them made the app usable by exactly one person.
  `POST /api/app/signin` checks `APP_PIN` and returns the registration key; the
  app sends that as `X-Registration-Key` from then on. `require_app_or_auth`
  accepts either Basic or that key, and is applied **only** to the incidents and
  test routers — the key ships inside every APK, so it must not unlock the
  dashboard pages or the settings API. Empty `APP_PIN` disables app sign-in
  (503) rather than leaving it open. The `name` is a device label, not an
  account: revoking one person means changing the PIN for everyone. Per-user
  PINs are the obvious upgrade and the `users` table is already shaped for it.

---

## Running and testing

On the Windows machine:

```
.venv\Scripts\python run.py                  # binds 0.0.0.0 so the phone can reach it
.venv\Scripts\python tools\selftest.py       # whole pipeline, offline, ~1 min
.venv\Scripts\python tools\check_mailbox.py  # IMAP login, folders, unread count
.venv\Scripts\python tools\scan_recent.py 100  # read-only: what would the rules do?
```

In the Codespaces dev container, same scripts, `.venv/bin/python`:

```
.venv/bin/python run.py
.venv/bin/python tools/selftest.py
```

**Always the venv interpreter, never a bare `python`.** The container has no
`pip`, no `pip3`, no `python3 -m pip` and no system-level FastAPI — only
`.venv` has the dependencies. The devcontainer's `postCreateCommand`
(`pip install --user -r requirements.txt`) cannot succeed there.

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

Configured and verified: mailbox `digne@esicia.rw` on `mail.esicia.rw:993`;
**ntfy** on topic `alertbot-1javcgmgzg7e06` at `https://ntfy.sh`, priority 5,
enabled — this is the channel that actually rings; watched chats `ESICIA Team`
and `Vubavuba Africa` (added 2026-08-05, matching confirmed against a decorated
Android title); dashboard auth on. `selftest.py` passes 39/39.

Development moved to a **GitHub Codespace**, so `PUBLIC_URL` is now
`https://super-duper-halibut-wwwqxxpqj7jfvj97-8000.app.github.dev`, not the old
LAN address. That hostname dies with the Codespace.

**Blocking the phone reaching the dashboard:** port 8000 is forwarded
**private**, so every request 302s to a GitHub sign-in page — which a
notification tap, the ntfy app and the APK can never satisfy. Fix in the VS Code
PORTS panel → right-click 8000 → Port Visibility → Public. The
`"visibility": "public"` line in `devcontainer.json` only applies at container
creation, so it does not rescue an existing Codespace. `gh` is not installed.
Test with `curl -o /dev/null -w "%{http_code}" $PUBLIC_URL/healthz` — 200
public, 302 private. Note this does **not** block ntfy, which delivers via
ntfy.sh and needs no inbound access.

**The Android app** (rewritten 2026-08-07, v2.0; onboarding reworked the same
day): a Jetpack Compose client in Esicia's brand colours — blue `#0F5C92` and
gold `#CCAE3A`. Four screens: sign in, alarm-permission setup, open alerts, one
alert with Acknowledge. Plus the full-screen alarm. Sign-in is **name + PIN
only** — no URL, no username, no password, no registration key. The server
address is compiled into `data/Config.kt` and never displayed; the registration
key arrives from `POST /api/app/signin`. UI in `ui/`, REST and storage in
`data/`, alarm plumbing at the package root.

⚠️ **The brand hexes above are unverified.** `esicia.rw` sits behind a
bot-verification WAF that blocks curl and WebFetch alike, so they could not be
re-checked on 2026-08-07 — they are inherited from an earlier session's claimed
reading of the logo SVG and stylesheet. Note that a naive fetch returns the
interstitial page, whose spinner is **green** (`#467C45`); that is not a brand
colour. Both hexes live in exactly two files, `ui/theme/Color.kt` and
`res/values/colors.xml`, so correcting them is a two-line change. The APK builds in CI (fixed in `b123d85`) and is served for sideloading at
`/static/alertbot.apk`, offered as a download button on `/setup` when the file
is present — it is gitignored, so a fresh clone falls back to build
instructions.

FCM is **no longer blocked** (verified 2026-08-07): `firebase.enabled` is true
and `FIREBASE_CREDENTIALS_JSON` holds a real service-account key for project
`alertbot-c4dfd`, injected as a Codespaces secret rather than living in
`credentials/firebase.json`. What remains is a registered device token, which
the app does on sign-in. MacroDroid is still unconfigured (no webhook URL).

`PHONE-SETUP.md` is the end-to-end wiring guide for all of the above.

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
  `.github/workflows/android.yml`. A step-level `if` may never reference the
  `secrets` context — it fails the whole workflow at startup before any job
  runs. Pass the secret through `env:` and test that instead (`b123d85`).
- **The Codespace suspends after ~30 minutes idle**, and a suspended AlertBot
  polls nothing. Same objection as a sleeping free tier.
- Commands here are slow (a bare `import app.main` can take a minute). Prefer
  background execution with generous timeouts over assuming a hang.
- Long terminal output gets truncated on the user's screen. Keep answers short
  and put the important line first.
