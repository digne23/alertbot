# Next steps — for Steve

> **Part A** is the onboarding/branding rewrite (2026-08-07, second pass).
> **Part C** is the dashboard restyle and the notification changes
> (2026-08-07, third pass) — the most recent work. **Part B** is the
> post-rewrite checklist, updated for the two-field sign-in.
>
> **Short version:** the Android *source* now signs in with a name and a PIN;
> the app *on your phone* does not, and will not until CI builds it and you
> reinstall. Start at **A0**. The browser dashboard is now white/blue/gold and
> needs no rebuild — reload and it is there (**C1**).
>
> **`APP_PIN` is set** and a live sign-in was checked against it — restart the
> server to load it. The value is not recorded here; see A7 for why.
>
> **Three things still need you:** rebuild the APK (Part B step 3), decide
> whether to rotate `DEVICE_REGISTRATION_KEY`, which is still `devtestkey`
> (A7), and confirm you want quiet hours on — the phone is now silent
> 06:00–24:00 (**C3**). Optionally, get me the real brand hexes (A1).

---

# Part A — onboarding + branding rewrite

## A0. Is the Android app updated?

**The source is. The app on your phone is not.**

| | Status |
|---|---|
| Android **source** in `android/` | ✅ rewritten — name + PIN sign-in, no URL anywhere |
| Android **compiled** | ❌ never built — this container has no Android SDK |
| APK **on the Galaxy A15** | ❌ still the old three-field build until you rebuild and reinstall |
| Backend | ✅ updated **and** verified — `selftest.py` 45/45 |
| Brand colours | ⬜ unchanged — could not verify them, see A1 |

So: nothing you can see on the phone has changed yet. The two-field sign-in
exists only as Kotlin source until GitHub Actions compiles it (Part B step 3)
and you sideload the result. Set `APP_PIN` first (A5) or the new build will
refuse to sign anyone in.

### What actually changed

**Backend — shared PIN sign-in**

| File | Change |
|---|---|
| `app/api/app_auth.py` | **new.** `POST /api/app/signin` — checks `APP_PIN`, returns the registration key and whether push is really on. 503 when no PIN is configured, 429 after five wrong tries from one address. |
| `app/auth.py` | **new** `require_app_or_auth` — accepts admin Basic *or* the registration key, plus `app_key_ok()`. An unset key never matches anything. |
| `app/api/incidents.py`, `app/api/test.py` | routers swapped onto `require_app_or_auth`, so the phone can read alerts, acknowledge and fire a test without the admin password. |
| `app/main.py` | registers the new router. |
| `app/config.py`, `.env.example`, `.env` | added `APP_PIN`. The key is in your `.env` already, empty, waiting for a value. |
| `tools/selftest.py` | new section **2b**, six checks on the PIN path. |

Deliberately *not* changed: the dashboard pages and `/api/settings/*` still
require the admin password. The registration key is compiled into every APK, so
it must never unlock configuration — there is a selftest check that proves it
does not.

**Android — onboarding**

| File | Change |
|---|---|
| `ui/SignInScreen.kt` | rewritten. Two fields: **Your name**, **PIN**. The server address, username, password and registration key fields are all gone. |
| `data/ApiClient.kt` | Basic auth removed entirely; one `X-Registration-Key` header instead. New `signIn(name, pin)` distinguishing wrong PIN / locked out / not configured / unreachable. `fetchRegistrationKey` and `normaliseUrl` deleted — nothing needs them now. |
| `data/Prefs.kt` | no longer stores a password or a server address. Stores the issued key and a display name. |
| `data/Config.kt` | `DEFAULT_SERVER_URL` is now the sole source of the address and is never rendered. |
| `ui/AlertsScreen.kt` | the account sheet no longer prints the server URL. |
| `res/values/strings.xml` | every string that named a server, username or password replaced with plain language. |
| `res/drawable/ic_chat.xml` | chat bubble → Material Symbols `smartphone`, per the no-chat-bubble note. It sits next to the word "WhatsApp", so nothing is lost; one-line revert if you disagree. |
| `AlertBotApp.kt` | keystore warm-up reads the new pref. |

**Branding was already done** in the merged commit `bf970f6` — the bell mark in
white and gold on Esicia blue, real Material Symbols throughout, no sparkles,
robots or gradient blobs, and `Theme.kt` wired to the brand tokens with dynamic
colour off. I verified that rather than redoing it. The only branding item still
open is whether the two hexes are correct (A1).

---

## A1. Colour extraction — blocked, not done

I could **not** get the real values from the live site. `esicia.rw` sits behind
a bot-verification WAF ("One moment, please... your request is being
verified"). Every route returned that interstitial instead of the asset:

- `curl` plain, and with a full Chrome User-Agent + cookie jar → interstitial
  (or `415 Unsupported Media Type` when sent an SVG `Accept` header)
- `WebFetch` on both the logo SVG and `/css/style.css` → interstitial
- the `www.` variant → same

**A false positive worth knowing about:** the first extraction attempt appeared
to succeed and returned *green* (`#467C45`, `rgba(38, 122, 72, 0.86)`). That was
the colour of the spinner graphic on the interstitial page, not the Esicia logo.
It was caught by checking `Content-Type`, which came back `text/html` even for
the `.svg` URL. If green shows up anywhere, that is where it came from — it is
not a brand colour.

### What the repo currently claims

`Color.kt` and `colors.xml` already carry these, recorded by an earlier session
with specific provenance:

| Role | Hex | Claimed source |
|---|---|---|
| Brand blue (primary) | `#0F5C92` | stroke on the accent rule in `esicia-logo-compressor.svg`; section background in `css/style.css` |
| Brand gold (accent) | `#CCAE3A` | most-used colour in `css/style.css` (47 uses) |

Supporting, non-brand (state and chrome only):

| Role | Hex |
|---|---|
| Critical | `#F45E58` |
| Critical deep (alarm bg) | `#8E1F1B` |
| Resolved | `#33D685` |
| Page surface | `#F7F7F7` |
| Card surface | `#FFFFFF` |
| Text primary | `#333333` |
| Text secondary | `#666666` |
| Hairline | `#E2E5E9` |

These match your description — white background, blue and gold. But **they have
not been verified against the live asset**; they are what is in the repo, not
what was extracted this session.

**Decision was: fetch them through your Chrome browser.** That route is also
unavailable — the Claude in Chrome extension is not connected to this session,
so there is no browser to drive. Connect it at <https://claude.ai/chrome> and I
can retry, or simply paste me the logo SVG source or the stylesheet and I will
read the fills out of it.

**Status: still unverified.** The app currently ships the two hexes in the table
above. They live in exactly two files —
`android/app/src/main/java/com/alertbot/mobile/ui/theme/Color.kt` and
`android/app/src/main/res/values/colors.xml` — and everything else refers to
them by name, so correcting them is a two-line change with no other edits. That
is why the rest of the work went ahead rather than waiting.

---

## A2. Auth — what is actually there now

The blocker is bigger than the sign-in screen. Every endpoint the app uses sits
behind the single admin Basic-auth password:

| Endpoint | Protection |
|---|---|
| `/api/incidents/*`, `/api/stats`, `/api/test-alert` | `require_auth` — Basic, one `DASHBOARD_USER` / `DASHBOARD_PASSWORD` |
| `/api/devices`, `/api/ingest/*` | `DEVICE_REGISTRATION_KEY` header |
| `/api/health` | Basic, and returns `ingest_key` — the existing trick the app uses to hide the registration key from the user |

The app stores `baseUrl` + `username` + `password` in `EncryptedSharedPreferences`
and sends Basic on every call. **So staff cannot use the app today without being
handed the admin password.** That is the real defect, not the extra text fields.

Useful things already in place: the `users` table exists (name, email, role,
`notify_*`, `active`) with full CRUD at `/api/settings/users` *and* a management
UI in `settings.html`; and `database.py` has a `_MIGRATIONS` dict that safely
`ALTER TABLE ADD COLUMN`s on an existing SQLite file.

**Decision: shared PIN.** One PIN in baked config gates the app; the name the
user types is a device label, used to identify the phone in the dashboard. The
app then registers the device using the existing registration key behind the
scenes. The user only ever sees **Name** and **PIN**. Roughly 30 lines of
backend.

Consequence to be aware of, accepted with this choice: there is no per-user
identity, so revoking one person's access means changing the PIN for everyone
and reinstalling/re-signing-in on every phone. The per-user route (individual
PINs, bearer sessions, lockout, admin-managed in the existing users UI) stays
available later — the `users` table is already shaped for it.

---

## A3. Onboarding flow — built

1. **Sign in** — logo, **Name**, **PIN**, one button. No URL, no username, no
   password, no registration key. Server address comes from `DEFAULT_SERVER_URL`
   and is never shown.
2. **Alarm setup** — the existing permission checks (notifications, background
   running, lock-screen alarms), rebranded. Kept as-is functionally; on One UI
   all three genuinely matter.
3. **Alerts** — open alerts list.
4. **Alert detail** — Acknowledge.
5. **Full-screen alarm** — unchanged behaviour, rebranded.

Same screen count as now, minus every technical field.

---

## A4. Flags — true regardless of the above

- **`DEFAULT_SERVER_URL` is the Codespace hostname**, and it is baked into the
  APK. That hostname dies with the Codespace, so every installed APK breaks when
  it is recreated. Fine for testing; needs a stable host before staff install it.
  See Part B step 6.
- **Port 8000 must be forwarded Public** or the app gets a GitHub sign-in page
  instead of the API. See Part B step 2.
- A short PIN on a public URL is guessable. With a shared PIN there is no
  per-user lockout to lean on, so make it longer than 4 digits and treat it as a
  password you would not print. Five wrong PINs from one address now buys a
  15-minute lockout, but that is a speed bump, not a substitute for a good PIN.

---

## A5. What you need to do

1. ~~Set `APP_PIN` in `.env`~~ — **done.** A 4-digit PIN is set and was checked
   against a live sign-in: the right PIN returns 200, a wrong one 401. The value
   is not written down here on purpose; see A7. **Restart the server** so it
   picks the value up — `.env` is read once at import.
2. **Rebuild the APK** — push to `main`, or Actions → Build Android APK → Run
   workflow. Nothing here has been compiled: this container has no Android SDK,
   so CI is the only real check. See Part B step 3.
3. **Decide about `DEVICE_REGISTRATION_KEY`** — it is still `devtestkey`. See
   A7.
4. *(optional)* **Get me the real brand hexes**, per A1.

## A6. What was verified, and what was not

**Verified:** the backend. `tools/selftest.py` passes **45/45**, up from 39 —
six new checks cover the PIN path specifically: correct PIN signs in, the key
comes back, wrong PIN is refused, the key opens the alert list, the key does
*not* open the settings API, and an unset `APP_PIN` returns 503 rather than
letting anyone through.

**Not verified:** the Android code does not compile here — no SDK in this
container — and no screen has been run on a device. The res XML all parses and
every `ApiClient` call site and `R.string` reference was checked by hand against
the new signatures, but that is not a build. Part B step 3 remains the real
gate.

---

## A7. Secrets — where they live, and why they are not in here

**The PIN is not written in this file, and cannot be committed.** It lives only
in `.env`, which is gitignored (`.gitignore:5`) and untracked. That is
deliberate on two counts: this file is committed and pushed, and `.env` also
holds the live mailbox password, the ntfy token and the Firebase paths — putting
any of it in git would be awkward to undo.

Nothing breaks as a result. The PIN never needs to reach GitHub or the APK:

- the **server** reads it from `.env`;
- the **phone** never stores it — staff type it once, and the server hands back
  the registration key in exchange.

So "commit the PIN change" has nothing to commit. The code that *reads*
`APP_PIN` was committed and pushed in `572229e`; only the value changed, and
values do not belong in the repo.

### `DEVICE_REGISTRATION_KEY` is still `devtestkey`

Worth a decision. That key used to be low-stakes: it only allowed WhatsApp
ingest and device registration. It now also opens the alert list, acknowledge
and test-alert, because the app authenticates with it instead of a dashboard
password — and it is compiled into every APK. A guessable key on a public URL is
a weaker link than the PIN sitting in front of it.

Rotating it is one line in `.env`, but it means re-signing-in every phone and
re-pasting the key into any MacroDroid macro that forwards WhatsApp
notifications. Ask me and I will generate one; the MacroDroid side is yours,
since that configuration is not visible from here.

### A 4-digit PIN

Ten thousand combinations. The lockout is carrying more of the weight than the
PIN is: five wrong tries from one address buys fifteen minutes, so about twenty
attempts an hour. It is per-address and in-memory per process, so someone with
several addresses moves faster, and a process restart clears it. Adequate behind
a decision made knowingly; lengthen the PIN if this ever faces anything other
than staff.

# Part C — dashboard restyle + notification changes

Written 2026-08-07, third pass. Unlike Part A, **all of this is live the moment
you reload the dashboard** — none of it needs an APK rebuild.

`tools/selftest.py` passes **45/45** after every change below.

## C1. The dashboard is now white, blue and gold

The browser dashboard was a dark NOC console. It is now Esicia-branded, using
the exact hexes already in the Android app (`#0F5C92` blue, `#CCAE3A` gold), so
the two match. Blue sidebar, white cards, gold on active nav.

Same pages, same buttons, same routes, same data — this was a restyle, not a
rewrite. `android/` was not touched.

| File | Change |
|---|---|
| `app/static/style.css` | rewritten light theme. Every colour is a token; the brand hexes appear once each. |
| `app/templates/base.html` | inline SVG icon sprite (39 Material Symbols glyphs), brand mark, light `theme-color`. |
| all five page templates | icons instead of emoji, panel headers, spacing and hierarchy. |
| `app/static/app.js` | `AlertBot.icon()` helper; badges carry icons. |
| `icon.svg`, the three PNGs, `manifest.webmanifest`, `sw.js` | brand-coloured PWA mark; cache bumped to `v2` so stale dark CSS is dropped. |
| `tools/make_icons.py` | draws the mark in brand colours now. |

**Icons are inlined, not fetched from Google Fonts.** A webfont link would show
raw text like `warning` mid-layout whenever the CDN is unreachable or the PWA is
offline. Costs ~4KB in `base.html`.

**Contrast.** `#F45E58` and `#33D685` were tuned for a black screen and fail on
white — the green measures **1.89:1** where 4.5 is the floor for small text.
They are kept for shapes (rails, dots, badge borders) and paired with darker
text variants. Every text/background pair in the theme was measured and clears
4.5:1; two gold pairs came in at 4.38 on the first pass and the gold text token
was darkened to `#7C620F` to fix it.

**Not verified: how it actually looks.** There is no headless browser in this
container, so the layout and spacing were never rendered. Open `/` and `/setup`
on both desktop and a phone before trusting it.

## C2. Phone page copy is now staff-first

`/setup` read as though every engineer had to configure ntfy, MacroDroid and
Firebase themselves. Restructured so **section 1 is the only part staff read**:
install the APK, sign in with name and PIN, done. ntfy, Firebase, MacroDroid and
WhatsApp are sections 2–5, each tagged **Admin**.

Deleted the step telling users to enter a backend URL and dashboard password —
that has been wrong since the name+PIN rewrite. The APK download button moved
into the staff section.

## C3. Quiet hours — the phone is silent during the day

**This is a behaviour change worth a second look.** Notifications now only fire
between **00:00 and 06:00** local. Outside that window an incident is still
raised, still logged, still on the dashboard — but nothing rings.

Settings → Notification channels, four fields (on/off, start, end, UTC offset).

- **The UTC offset matters.** The server stores naive UTC and the scheduler runs
  UTC, so without it your window would have run 00:00–06:00 UTC = 02:00–08:00 in
  Kigali. It defaults to **2**. Verified across all 24 hours; windows crossing
  midnight work.
- **Test buttons ignore the window** — proving the alarm path at 2pm must not be
  answered with silence. Only the *first* test push is exempt; its repeats obey
  quiet hours so a forgotten test cannot nag all day.
- **A zero-width window fails open** — if start and end ever match it logs a
  warning and rings anyway, rather than muting everything forever.
- Held pushes appear in the notification log as
  `quiet-hours — held: 17:00 local, window 00:00-06:00`, so silence is never
  ambiguous.

**The trade-off, plainly:** this runs against the project's own rule that the
engineer getting woken beats everything else. A daytime outage wakes nobody
until midnight; anything still unacknowledged then starts alarming. There is a
warning banner beside the control. **Untick the box to revert.**

`selftest.py` sets `notifications.window_enabled: False` for its run — it tests
the delivery path, not the clock.

## C4. Em dashes are out of the notification titles

Push titles read `CRITICAL: Vubavuba`, not `CRITICAL — Vubavuba`. Also
`STILL DOWN:`, `ESCALATED:`, `RESOLVED:`, the test-alert sample reason, and the
browser notification title.

A colon, not a hyphen: ntfy already has to transliterate dashes out of its ASCII
headers, so a colon is the one separator that survives every channel unchanged.

**No APK rebuild needed.** The Android app composes no text of its own — it
displays the title and body the server sends, so this reaches the phone as soon
as the server restarts. The 22 em dashes left in `android/` are all in comments,
which the compiler strips.

## C5. Sender addresses were already editable

You asked for the alert-sender list to be add/removable. **It already was** —
Settings → Critical senders, chip list with an add box and an `×` on each entry,
backed by `/api/settings/senders`. I tested it live (added an address, confirmed
it appeared, deleted it, confirmed the original five survived) and built nothing
new. If it was not behaving for you, say what you saw.

## C6. Side effects from testing

- Firing one test alert deduped into your existing open incident **#14**
  (`portal.esicia.rw`), bumping its event count and sending one real escalation
  push — your phone may have buzzed.
- Incident **#19** (`windowcheck.esicia.rw`) was created and has been closed.
- Your other five open incidents are untouched.

---

# Part B — post-rewrite checklist

Written 2026-08-07, after the mobile app rewrite (`android/`, v2.0).

Everything here needs a human: a console login, a click in the VS Code UI, or a
phone in your hand. Nothing below can be done from the terminal in this
Codespace.

Work top to bottom. Steps 1 and 2 are independent of each other; steps 3–5 are
a chain.

---

## 1. Rotate the Firebase service-account key — do this first

**Why:** the private key for `alertbot-c4dfd` was printed into an assistant
session transcript on 2026-08-07. It was read out of the
`FIREBASE_CREDENTIALS_JSON` Codespaces secret by a shell command that was meant
only to check whether the variable was set. Treat the key as exposed.

The key to revoke is the one with client email
`firebase-adminsdk-fbsvc@alertbot-c4dfd.iam.gserviceaccount.com`, key id
starting `a226278d8ad3316ae`.

1. Firebase console → project **alertbot-c4dfd** → ⚙ Project settings →
   **Service accounts**.
2. **Generate new private key** → download the JSON.
3. Google Cloud console → IAM & Admin → Service Accounts → that account →
   **Keys** → delete the old key id.
4. Update the Codespaces secret: GitHub → Settings → Codespaces → secrets →
   `FIREBASE_CREDENTIALS_JSON` → paste the whole new JSON on one line.
5. Rebuild the Codespace (or restart the server) so the new value is picked up,
   then check `/settings` → Firebase reports no init error.

Nothing else in this list depends on step 1, but do not leave it.

---

## 2. Make port 8000 public

**Why:** as of right now `curl $PUBLIC_URL/healthz` returns **302** — a redirect
to a GitHub sign-in page. A notification tap, the ntfy app and the phone app
cannot satisfy that login, so the app will fail to sign in until this changes.

1. Open the **PORTS** panel (next to TERMINAL). Missing? Ctrl+Shift+P →
   `Ports: Focus on Ports View`.
2. Find port **8000** — start the server first if it is not listed
   (`.venv/bin/python run.py`).
3. Right-click → **Port Visibility** → **Public**.

Verify:

```bash
curl -o /dev/null -w "%{http_code}\n" $PUBLIC_URL/healthz
```

**200** = public and working. **302** = still private.

The `"visibility": "public"` line in `.devcontainer/devcontainer.json` only
applies when a container is created, so it cannot fix an existing Codespace.

---

## 3. Build the APK

The app was rewritten in Jetpack Compose, then its onboarding was rewritten
again (Part A). **None of it has been compiled** — this container has no Android
SDK, so GitHub Actions is the only real check. A Compose migration typically
fails at the Gradle or compiler-plugin level if it fails at all, so a green
build here is a genuine gate.

`mobile-app-rewrite` has been merged into `main`, and the Part A changes are on
`main` too — so pushing is enough to trigger a build:

1. Commit and push to `main`.
2. GitHub → **Actions** → **Build Android APK** — it should already be running.

To build without pushing, use **Run workflow** and pick the branch.

If it goes red, send me the failing step's log and I will fix it.

Then download the artifact and put it where the phone can reach it:

```bash
# from the downloaded alertbot-apk.zip
unzip -j alertbot-apk.zip '*.apk' -d /workspaces/alertbot/app/static/
mv /workspaces/alertbot/app/static/*.apk /workspaces/alertbot/app/static/alertbot.apk
```

The `/setup` page then shows a **Download alertbot.apk** button.

---

## 4. Install and sign in on the Galaxy A15

Needs steps 2 and 3 done.

1. On the phone, open `$PUBLIC_URL/setup` and tap **Download alertbot.apk**
   (or go straight to `$PUBLIC_URL/static/alertbot.apk`). Allow installs from
   unknown sources for Chrome when Android asks.
2. Launch AlertBot. The sign-in screen asks for **two** things:

   | Field | Value |
   |---|---|
   | Your name | anything — it labels this phone in the dashboard |
   | PIN | your `APP_PIN` |

   There is deliberately **no server address, username, password or
   registration key** on this screen. If you see any of them, you are running
   the old APK.

   **Set `APP_PIN` in `.env` first** (see `.env.example`) and restart the
   server, or sign-in fails with "ask your administrator to finish setting it
   up". Make it six characters or more.
3. Tap **Sign in**, then work through **Alarm setup**. Turn on all three:
   notifications, background running, and lock-screen alarms. All three matter
   on One UI — Samsung will otherwise doze the app and it will never ring at
   3am.

**What success looks like:** the phone appears in the dashboard under
Settings → devices. If it does not, sign-in did not reach the API — recheck
step 2.

---

## 5. Prove the alarm works end to end

On the phone: account icon (top right) → **Send a test alert** → confirm.

This is a real alert, not a simulation. It goes through
`IncidentService.create_incident()`, so it **rings every phone signed in to
AlertBot** and creates an incident that stays in the history until someone
acknowledges it. That is why the app asks first.

Expected: the phone lights up full-screen with a loud alarm within a few
seconds, over the lock screen.

The app waits 15 seconds for the push to reach itself and then tells you which
of these happened:

- *"The test alarm reached this phone"* — the whole path works. Done.
- *"The server created the test alert, but no alarm reached this phone"* — the
  incident was raised but the push did not arrive. Check `/settings` → Firebase;
  its summary line reports the registered token count and any init error.

Also worth trying once, so you trust it later:

- **Acknowledge** — silences every phone and marks the incident acknowledged.
- **Snooze 5 min** — silences this phone and genuinely comes back in five
  minutes. Acknowledge it from the dashboard in the meantime and the snooze
  stays quiet, which is the behaviour to confirm.

---

## 6. Then: give it a permanent home

Not urgent, but it decides how much of the above you repeat.

`DEFAULT_SERVER_URL` in `android/app/src/main/java/com/alertbot/mobile/data/Config.kt`
is currently the Codespace hostname. That hostname dies with the Codespace, and
it is **baked into the APK** — so every time the Codespace is recreated you are
back to rebuilding and reinstalling on every phone.

`render.yaml`, `Dockerfile` and `Procfile` are ready. Deploy somewhere with a
stable hostname, point that constant at it, rebuild once, and steps 3–4 become a
one-time job instead of a recurring chore. Avoid a free tier that sleeps: a
sleeping AlertBot notices nothing.

The same argument applies to the Codespace itself, which suspends after about
30 minutes idle and polls no mail while suspended.
