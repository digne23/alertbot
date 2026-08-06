# Making port 8000 public

This is Step 0 of `PHONE-SETUP.md`, written out in full. Until this is done,
every request from your phone to the dashboard, the APK or a notification tap
lands on a GitHub sign-in page instead of AlertBot.

Written 2026-08-05, checked against this Codespace.

---

## Why it is private right now

`.devcontainer/devcontainer.json` **does** ask for a public forward:

```jsonc
"portsAttributes": {
  "8000": { "visibility": "public" }
}
```

But that file never ran. This Codespace is a **recovery container** —
`CODESPACES_RECOVERY_CONTAINER=true` in the environment. When a devcontainer
fails to build, Codespaces boots a plain fallback image instead, and none of
your `devcontainer.json` is applied. That is the same reason there is no `pip`
in here. So the setting is correct and simply was never read; you have to flip
the port by hand.

---

## Do it in the PORTS panel

### 1. Start the server first

The port has to exist before you can change its visibility, and nothing is
listening on 8000 at the moment:

```bash
cd /workspaces/alertbot
.venv/bin/python run.py
```

VS Code notices the new listener and auto-forwards it. Leave this running in
its own terminal.

### 2. Open the PORTS panel

It is a tab in the bottom panel, in the same row as **TERMINAL**, **PROBLEMS**,
**OUTPUT** and **DEBUG CONSOLE**.

If you cannot see it:

- Press **Ctrl+Shift+P** (**Cmd+Shift+P** on a Mac) to open the Command
  Palette, type `Ports: Focus on Ports View`, press Enter. This works in the
  browser and in desktop VS Code.
- Or **View → Open View… → Ports**.

The panel has these columns: **Port**, **Forwarded Address**, **Running
Process**, **Visibility**, **Origin**.

### 3. Flip the row

1. Find the row where **Port** is `8000` (Running Process will mention
   `python run.py`).
2. **Right-click** that row.
3. Choose **Port Visibility** → **Public**.

On a phone or tablet, or if right-click is awkward, hover the row and use the
**⋯** more-actions button at its right end — the same menu appears.

> There will also be a **Private to Organization** option. That is not enough
> here: it still requires a GitHub session, which a notification tap cannot
> provide.

### 4. If port 8000 is not listed at all

Click the **Forward a Port** button at the top of the panel (or the **+** in
the panel's title bar), type `8000`, press Enter. The row appears; then do
step 3.

### 5. Confirm

The **Visibility** column for 8000 should now read `Public`. Prove it from a
second terminal:

```bash
curl -s -o /dev/null -w "%{http_code}\n" \
  https://super-duper-halibut-wwwqxxpqj7jfvj97-8000.app.github.dev/healthz
```

| Result | Meaning |
|---|---|
| **`200`** | Done. The phone can reach AlertBot. |
| `302` | Still private — the redirect is the GitHub login page. |
| `502` / `404` | Visibility is fine, but nothing is listening. Go back to step 1. |
| `000` | curl could not connect at all — check the hostname. |

The URL does **not** change when you make it public. It stays exactly what it
was.

---

## What you are actually exposing

A public forward means **anyone with the URL** can reach port 8000. No GitHub
account, no password at the edge. What protects each path after that:

| Path | Protection |
|---|---|
| `/` and the rest of the dashboard | HTTP Basic — `DASHBOARD_PASSWORD` |
| `/healthz` | none, deliberately — it is the uptime probe and the test above |
| `/static/*` including `alertbot.apk` | none, deliberately — so the phone can download with a plain URL |
| `/api/ingest/*`, `/api/devices` | `DEVICE_REGISTRATION_KEY`, not the dashboard password |

The hostname is long and random, so it is not going to be stumbled upon, but it
is not a secret either — anyone you send it to keeps access. Set it back to
Private when you are done testing if that bothers you.

---

## Things that will undo this

- **Rebuilding or recreating the Codespace.** If the rebuild succeeds normally
  (not into recovery), `devcontainer.json` applies and 8000 comes up public on
  its own. If it lands in recovery again, you are back here.
- **A new Codespace** gets a new hostname, which breaks the phone, the APK's
  Base URL and `PUBLIC_URL` in `.env` all at once.
- **Suspension** does not reset visibility — but it does stop the server, so
  the URL will 502 until you start `run.py` again.

---

## If the menu item is not there

The panel only offers **Port Visibility** for Codespaces-forwarded ports. If
you are looking at a local VS Code window rather than the Codespace, or the row
came from something other than the Codespace forwarder, the item is absent —
check the browser tab is on `github.dev`/the Codespace window.

The `gh` CLI can do this in one command:

```bash
gh codespace ports visibility 8000:public -c super-duper-halibut-wwwqxxpqj7jfvj97
```

but `gh` is **not installed** in this container, and installing it here needs a
download. The PORTS panel is the shorter road.

---

Next: `PHONE-SETUP.md` Step 2 — subscribe the phone to ntfy topic
`alertbot-1javcgmgzg7e06`. Note that ntfy rings whether or not this port is
public; it delivers via ntfy.sh and needs no inbound access to the Codespace.
