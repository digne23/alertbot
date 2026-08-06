# Wiring AlertBot up to your phone

Written 2026-08-05. Everything here was checked against this Codespace, not
recalled from the docs — where the repo's own notes disagree with reality, this
file says so.

Your server address:

```
https://super-duper-halibut-wwwqxxpqj7jfvj97-8000.app.github.dev
```

Work through the steps in order. Steps 0–3 get the phone alarming. Steps 4–6
are optional extras.

---

## Step 0 — Make port 8000 public (nothing works until you do this)

**Right now your phone cannot reach AlertBot at all.** I tested the URL above
and it redirects to a GitHub sign-in page. The port is forwarded *privately*,
which means only a browser already logged into your GitHub account can open it.
A notification tap, the ntfy app and the Android APK cannot satisfy that login.

`.devcontainer/devcontainer.json` does set `"visibility": "public"`, but that
file never ran: this Codespace is a **recovery container**
(`CODESPACES_RECOVERY_CONTAINER=true`), i.e. the devcontainer failed to build
and Codespaces booted a plain fallback image instead. None of your
`devcontainer.json` applied — which is also why there is no `pip` in here.

Fix it in the VS Code UI:

1. Open the **PORTS** panel (next to TERMINAL at the bottom). Not there?
   Ctrl+Shift+P → `Ports: Focus on Ports View`.
2. Find the row for port **8000** — start the server first (Step 1), or it may
   not be listed.
3. Right-click it → **Port Visibility** → **Public**.

**Full walkthrough, including what to do when the row or the menu item is
missing: [`PORT-8000-PUBLIC.md`](PORT-8000-PUBLIC.md).**

The Visibility column should then read `Public`. Verify from the terminal:

```bash
curl -s -o /dev/null -w "%{http_code}\n" \
  https://super-duper-halibut-wwwqxxpqj7jfvj97-8000.app.github.dev/healthz
```

**`200` means done.** `302` means it is still private — the phone will see a
GitHub login page instead of AlertBot.

> `/healthz` is deliberately unauthenticated, which is why it is the honest
> test here. The dashboard itself will still ask for a password, as it should.

### Two things about Codespaces you need to know

- **A stopped Codespace notices nothing.** Codespaces suspend after ~30 minutes
  of inactivity. When it suspends, AlertBot stops polling the mailbox and no
  alarm will ever fire. This is the same reason `CLAUDE.md` rejects a
  free-sleeping host: *a sleeping AlertBot notices nothing*. For real on-call
  use this needs a machine that stays awake.
- **The URL is tied to this Codespace.** Delete or rebuild it and the hostname
  changes, which breaks the phone, the APK config and `PUBLIC_URL` in `.env`
  all at once.

---

## Step 1 — Start the server

```bash
cd /workspaces/alertbot
.venv/bin/python run.py
```

Use `.venv/bin/python`, not plain `python`. This container has no `pip` and no
system-level FastAPI — only the venv has the dependencies. (`postCreateCommand`
in the devcontainer runs `pip install --user`, which never ran here anyway —
recovery container.)

Wait for `AlertBot ready — auth ON` and `Scheduler started — polling every
30s`. Leave it running. Confirm with `/healthz` as in Step 0.

**Running it in the background, stopping it, and what to do when it will not
start: [`RUN-SERVER.md`](RUN-SERVER.md).**

---

## Step 2 — ntfy (this is what actually wakes you)

The custom APK cannot ring yet (Step 4 explains why). **ntfy is the working
alarm path**, and it needs no Codespace access at all — ntfy.sh delivers the
push, so this keeps working even while port 8000 is private.

Already configured and verified on the server:

| Setting | Value |
|---|---|
| Server | `https://ntfy.sh` |
| Topic | `alertbot-1javcgmgzg7e06` |
| Priority | 5 (max — bypasses silent mode) |
| Enabled | yes |

On the phone:

1. Install **ntfy** from the Play Store (or F-Droid).
2. **+** → Subscribe to topic → enter exactly `alertbot-1javcgmgzg7e06`,
   leave the server as `ntfy.sh`.
3. Android will ask for notification permission — allow it.
4. In Android settings, put the ntfy app's notification channel on
   **Alarm/Urgent** and exempt it from battery optimisation, or Doze will
   delay the very alert you needed at 3am.

Test it from the dashboard (Settings → ntfy → Test), or from the terminal:

```bash
curl -H "Title: AlertBot test" -H "Priority: 5" \
  -d "If this buzzes, the alarm path works." \
  https://ntfy.sh/alertbot-1javcgmgzg7e06
```

Your phone should make noise within a couple of seconds. **If this works, the
product works** — everything below is refinement.

> Anyone who guesses the topic name can read your alerts and send fake ones.
> The random suffix is the only thing protecting it. Fine for now; worth
> revisiting before this carries customer-visible incidents.

---

## Step 3 — Open the dashboard on the phone

Once Step 0 is done, browse to the URL at the top of this file.

Log in with username `admin` and the dashboard password. To print your
credentials:

```bash
grep -E "DASHBOARD_USER|DASHBOARD_PASSWORD|DEVICE_REGISTRATION_KEY" .env
```

Then install it as an app: Chrome menu **⋮ → Add to Home screen → Install**.
It is a PWA, so it gets its own icon and runs without browser chrome.

Useful pages: `/` live incidents, `/history` search and CSV, `/settings`
channels and chats, `/setup` the phone-setup walkthrough.

---

## Step 4 — Install the Android app and prove it runs

**You can install this app and hear it scream today. No Firebase key needed.**

The app has a built-in **Test alarm** button that launches the full alarm screen
locally — full-volume alarm tone on the alarm stream, vibration, screen wake,
over the lock screen. I read the code path: `previewAlarm()` → `AlarmActivity` →
`AlarmPlayer.start()` touches only `RingtoneManager`, `MediaPlayer` and
`Vibrator`. **No network, no Firebase, no server involved.** That button is the
proof the app installs and runs.

What the missing Firebase key blocks is narrower than it sounds: the *server*
cannot push *to* the app. Everything else — install, launch, permissions, the
alarm itself, registering with AlertBot — works now.

I verified against the actual build:

| Check | Result |
|---|---|
| APK signature | v2 signing block present → installs on Android 7+ |
| Package / version | `com.alertbot.mobile`, v1.0 (code 1) |
| minSdk / targetSdk | 24 / 35 — fine for the Galaxy A15 (Android 14) |
| Firebase project | `alertbot-c4dfd`, matching package, API key present |
| Permissions | `POST_NOTIFICATIONS`, `USE_FULL_SCREEN_INTENT`, `WAKE_LOCK`, `VIBRATE` all declared |
| Runtime permission | `MainActivity` requests `POST_NOTIFICATIONS` on launch (required on Android 13+) |
| `POST /api/devices` | tested with the app's exact JSON payload → **HTTP 200** |

### Download it

With the server running and the port public, open on the phone:

```
https://super-duper-halibut-wwwqxxpqj7jfvj97-8000.app.github.dev/static/alertbot.apk
```

Or tap **Download alertbot.apk** on the `/setup` page. Android will warn about
installing from unknown sources; allow it for Chrome. The download itself needs
no password (`/static` is not behind auth), which is deliberate so the phone can
fetch it with a plain URL.

The APK on disk is 7,479,677 bytes, built by GitHub Actions
(`.github/workflows/android.yml`). To rebuild: Actions → **Build Android APK** →
run → download the artifact → drop it at `app/static/alertbot.apk`.

### Configure it

On first launch it asks for four things, stored by `Prefs.kt` and read at
runtime — so pointing it at a different server later never needs a rebuild:

| Field | Value |
|---|---|
| Base URL | `https://super-duper-halibut-wwwqxxpqj7jfvj97-8000.app.github.dev` |
| Username | `admin` |
| Password | your `DASHBOARD_PASSWORD` |
| Registration key | your `DEVICE_REGISTRATION_KEY` |

Tap **Save**. It fetches an FCM token, registers via `POST /api/devices`, and
the phone appears under Settings → devices. The `devices` table has **0 rows**
right now, so that row appearing is your confirmation. This step needs Step 0
done — otherwise the app gets a GitHub login page instead of the API.

### Prove it runs — tap Test alarm

Then tap the **Test alarm** button. The phone should light up and make a loud
noise immediately. **That is the session goal met: app installed, running,
alarming.**

Notes on the preview screen:

- **Snooze** (or the back button) stops the noise and closes it.
- **Acknowledge** stops the noise too, but the button will then say retry —
  the preview passes incident ID `0`, and `ApiClient.acknowledge()` refuses
  anything `<= 0` without calling the server. Expected, not a fault.

If it installs and previews the alarm, the Android half is proven end to end
except for the server→phone push, which is the Firebase key below.

### What is still missing: server → phone push

The app is pure Firebase Cloud Messaging
(`AlertMessagingService : FirebaseMessagingService`). The server has nothing to
push with:

- `firebase.enabled` is `false` in `alerts.db`
- the `credentials/` directory does not exist
- `FIREBASE_CREDENTIALS_JSON` is empty in `.env`

**Only you can unblock this.** In the Firebase console, project `alertbot-c4dfd`
→ Project settings → Service accounts → **Generate new private key**. Save the
JSON as `credentials/firebase.json` (gitignored), restart the server, then turn
on the Firebase channel in Settings and hit its Test button.

Until that key exists, treat the APK as a second channel that is not yet live.

---

## Step 5 — WhatsApp forwarding via MacroDroid (optional)

WhatsApp is an **input**, not an output. There is no legitimate way to read
chats you are in, so the phone forwards its own notifications to AlertBot.

**The watched chats are now configured.** They were missing — the table was
empty despite `CLAUDE.md` claiming otherwise. Added and verified 2026-08-05:

| Chat | Label | Keywords | Alarm |
|---|---|---|---|
| `ESICIA Team` | ESICIA Team (WhatsApp) | none — every message alarms | yes |
| `Vubavuba Africa` | Vubavuba Africa (WhatsApp) | none — every message alarms | yes |

Matching is a two-way, case-insensitive contains-match, so `ESICIA Team` also
matches `ESICIA Team (3 messages)` — how Android decorates group titles. I
tested exactly that decorated title: it raised an incident. A control message
from `Random Family Chat` was correctly rejected as `not_watched`.

To narrow them later (alarm only on `down, urgent, critical` rather than every
message), edit them on `/settings` → **WhatsApp chats**.

Then in MacroDroid:

- **Trigger:** Notification → Received → application WhatsApp
- **Action:** HTTP Request → GET →

```
https://super-duper-halibut-wwwqxxpqj7jfvj97-8000.app.github.dev/api/ingest/whatsapp
  ?chat={notification_title}
  &message={notification_text}
  &key=YOUR_DEVICE_REGISTRATION_KEY
```

(One line, no spaces. MacroDroid substitutes the magic-text variables.) A
`sender` parameter also exists for group chats. There is a `POST` form of the
same endpoint if you prefer JSON, and the key may travel as an
`X-Registration-Key` header instead of a query parameter.

Test without touching your phone from `/settings` → **Simulate a WhatsApp
message**.

> Unlike email, a repeat WhatsApp message **re-opens** an acknowledged incident
> and rings again (`reopen_on_repeat=True`) — a new message is genuinely new
> information.

---

## Step 6 — MacroDroid as a loud alarm channel (optional)

Separately from forwarding, MacroDroid can *receive* from AlertBot: create a
webhook trigger in MacroDroid, copy its URL, and paste it into `/settings` →
MacroDroid. That gives a second loud path without needing Firebase.

---

## Checklist

| # | Step | State |
|---|---|---|
| 0 | Port 8000 public | **Not done — do this first** |
| 1 | Server running | Running now; dies when the Codespace suspends |
| 2 | ntfy subscribed on the phone | Server side ready and verified; subscribe on the phone |
| 3 | Dashboard open + installed as PWA | After Step 0 |
| 4 | **APK installed and alarming** | **Ready — install it and tap Test alarm** |
| 4b | Server → phone push (FCM) | Blocked on the Firebase service-account key |
| 5 | WhatsApp watched chats | **Configured and verified** |
| 5b | MacroDroid forwarding rule | Build it on the phone |
| 6 | MacroDroid alarm channel | Not configured |

## If nothing rings

1. `curl .../healthz` → not `200`? Port is private (Step 0) or server is down.
2. ntfy test from Step 2 silent? The problem is on the phone — battery
   optimisation, notification permission, or the wrong topic.
3. Incidents appear on the dashboard but nothing rings? Check
   `notifications.enabled` and the channel toggles in Settings.
4. Full offline pipeline check, ~1 minute:
   `.venv/bin/python tools/selftest.py` — currently **39/39 passing**.
   Section 11 reports missing *configuration* rather than broken code.
