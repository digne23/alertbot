# Next steps — for Steve

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

The app was rewritten in Jetpack Compose. **It has not been compiled** — this
container has no Android SDK, so GitHub Actions is the only real check. A
Compose migration typically fails at the Gradle or compiler-plugin level if it
fails at all, so a green build here is a genuine gate.

The work is on branch **`mobile-app-rewrite`**. The workflow only builds
automatically on `main`, so for the branch you trigger it by hand:

1. GitHub → **Actions** → **Build Android APK** → **Run workflow**.
2. Change the branch dropdown to `mobile-app-rewrite` → **Run workflow**.

If it goes red, send me the failing step's log and I will fix it.

Once it is green, merge the branch to `main` (pushes to `main` build
automatically from then on).

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
2. Launch AlertBot. The sign-in screen asks for **three** things:

   | Field | Value |
   |---|---|
   | Server address | already filled in |
   | Username | `admin` |
   | Password | your `DASHBOARD_PASSWORD` |

   There is deliberately **no registration key field** — the app fetches that
   itself. If you see one, you are running the old APK.
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
