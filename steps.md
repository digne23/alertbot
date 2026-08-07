# Getting AlertBot onto the phone

Current state as verified on **2026-08-06**. This is the short action list.
`PHONE-SETUP.md` is the full reference; this file is what to do *next*.

---

## Start here: what actually rings today

**ntfy is the only working channel.** It needs no port forwarding, no APK, and
no Firebase — delivery goes out through ntfy.sh rather than into the Codespace.
Do this and the phone screams:

1. Install **ntfy** from the Play Store.
2. Tap **+** → **Subscribe to topic**.
   - Topic: `alertbot-1javcgmgzg7e06`
   - Server: `https://ntfy.sh` (the default)
3. Allow notifications when Android asks.
4. Long-press the subscription → set priority to **Max**, and allow it to
   override Do Not Disturb. The server already sends at priority 5; Android
   still has to be told to honour it.
5. Fire a test from the dashboard: **Settings → ntfy → Test**, or the test-alert
   endpoint. The phone should sound immediately.

Verified server-side:

```
ntfy.enabled  = true
ntfy.topic    = alertbot-1javcgmgzg7e06
ntfy.priority = 5      (escalated_priority also 5)
ntfy.server   = https://ntfy.sh
ntfy.token    = set
```

---

## The server has to be running

A suspended Codespace polls nothing, so nothing ever alarms.

```bash
.venv/bin/python run.py
```

Always the venv interpreter — the container has no `pip` and no system-level
FastAPI. Look for this line:

```
AlertBot ready — auth ON
```

`auth OFF` means `DASHBOARD_PASSWORD` is missing from `.env` and anyone with the
URL can read your incidents.

> **Known limit:** the Codespace suspends after ~30 minutes idle. While
> suspended AlertBot notices no email and no WhatsApp message. This is fine for
> testing and not yet a real on-call setup.

---

## Blocker 1 — port 8000 is forwarded private

Every request from outside gets a GitHub sign-in page, which a notification tap,
the ntfy app and the APK can never satisfy.

```
$PUBLIC_URL/healthz             -> 302
$PUBLIC_URL/static/alertbot.apk -> 302
```

**Fix:** VS Code **PORTS** panel → right-click **8000** → **Port Visibility** →
**Public**.

The `"visibility": "public"` line now in `.devcontainer/devcontainer.json` only
applies when a container is *created*, so it does not rescue this Codespace. It
will work for the next one.

**Verify:**

```bash
curl -o /dev/null -w "%{http_code}\n" $PUBLIC_URL/healthz
# 200 = public, 302 = still private
```

This does **not** block ntfy. It blocks the dashboard, the Acknowledge button in
a notification, and downloading the APK.

---

## Blocker 2 — the APK cannot ring, and installing it will not help

The Android app is pure FCM. It receives alarms only through Firebase, and the
server currently has nothing to push through:

```
firebase.enabled          = false
credentials/firebase.json = does not exist
FIREBASE_CREDENTIALS_JSON = unset
```

Install it today and it will open, register, and sit silent forever.

**What unblocks it:** only Steve (`digne@esicia.rw`) can generate a
service-account key from Firebase project `alertbot-c4dfd`. Then:

1. Save the key as `credentials/firebase.json`, or set
   `FIREBASE_CREDENTIALS_JSON` to its contents.
2. Restart the server.
3. **Settings → Firebase → enable**, then hit its Test button.

### Installing the APK once Firebase is ready

The build already exists at `app/static/alertbot.apk` (7.4 MB, from
**Actions → Build Android APK**). It is gitignored, so it lives only on this
machine.

1. Make port 8000 public (Blocker 1) — otherwise the download 302s.
2. Open `/setup` **on the phone**. A **Download alertbot.apk** button appears
   when the file is present.
3. Tap it. Android will ask to allow installs from unknown sources; that prompt
   is expected.
4. Open the app, enter the dashboard URL, username `admin`, and your
   `DASHBOARD_PASSWORD`. It fetches an FCM token and registers via
   `POST /api/devices`.

To refresh the build later, download the CI artifact again and drop the APK back
at `app/static/alertbot.apk`.

---

## MacroDroid — also unconfigured

`macrodroid.enabled = false`, `macrodroid.webhook_url = ""`.

MacroDroid matters for the *other* direction too: it is what forwards WhatsApp
notifications from the phone into `/api/ingest/whatsapp`, since there is no
official way to read chats you are already in. Watched chats are `ESICIA Team`
and `Vubavuba Africa`. See `PHONE-SETUP.md` for the macro.

---

## Order of work

| # | Step | Blocked by |
|---|------|-----------|
| 1 | Subscribe the phone to ntfy, send a test | nothing — do this now |
| 2 | Keep `run.py` running | Codespace idle suspend |
| 3 | Make port 8000 public | one click in the PORTS panel |
| 4 | Generate the Firebase key | Steve only |
| 5 | Install and register the APK | steps 3 and 4 |
| 6 | Wire MacroDroid for WhatsApp ingest | step 3 |

Steps 1 and 2 alone get the phone ringing. Everything after that is redundancy
and the WhatsApp input path.
