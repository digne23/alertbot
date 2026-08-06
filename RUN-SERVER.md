# Starting the AlertBot server

Step 1 of `PHONE-SETUP.md`, written out. Every command here was run in this
Codespace on 2026-08-05 and the output below is the real output, not an
example.

---

## Start it

```bash
cd /workspaces/alertbot
.venv/bin/python run.py
```

**`.venv/bin/python`, never a bare `python`.** This container has no `pip`, no
`pip3`, no `python3 -m pip` and no system-level FastAPI — only `.venv` has the
dependencies. (The devcontainer's `postCreateCommand` would have installed
them, but it never ran: this is a recovery container. See
`PORT-8000-PUBLIC.md`.)

Startup takes 30–60 seconds. Commands are slow here; a long pause is not a
hang.

### What a healthy start looks like

```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [2680] using WatchFiles
INFO:     Started server process [2711]
INFO:     Waiting for application startup.
... [apscheduler.scheduler] Scheduler started
... [alertbot.scheduler] Scheduler started — polling every 30s, escalation tick every 20s
... [alertbot] AlertBot ready — auth ON
INFO:     Application startup complete.
```

The three lines that matter:

| Line | Means |
|---|---|
| `Scheduler started — polling every 30s` | The mailbox is actually being watched. Without this, no email will ever raise an incident. |
| `escalation tick every 20s` | Repeat-until-acknowledged is live. |
| `AlertBot ready — auth ON` | `DASHBOARD_PASSWORD` is set, so the dashboard is protected. `auth OFF` means anyone with the URL can read your incidents — check `.env`. |

Leave the terminal running. Closing it stops AlertBot, and a stopped AlertBot
notices nothing.

---

## Confirm it is really up

```bash
curl -s http://localhost:8000/healthz
```

Expected, exactly:

```json
{"status":"ok","app":"AlertBot"}
```

And check something is listening on all interfaces, not just loopback —
`0.0.0.0:8000` is what lets the phone in:

```bash
ss -ltnp | grep 8000
```

```
tcp  0  0  0.0.0.0:8000  0.0.0.0:*  LISTEN  2680/.venv/bin/pyth
```

Then the public URL, which is the one your phone will use:

```bash
curl -s -o /dev/null -w "%{http_code}\n" \
  https://super-duper-halibut-wwwqxxpqj7jfvj97-8000.app.github.dev/healthz
```

`200` = reachable. `302` = the port is still forwarded **private** and the
phone will get a GitHub login page — fix that with `PORT-8000-PUBLIC.md`.
Local `200` plus public `302` is exactly the state this Codespace is in until
you flip the port; the server is fine, the door is shut.

---

## Running it in the background

To get your terminal back:

```bash
cd /workspaces/alertbot
nohup .venv/bin/python run.py > /tmp/alertbot.log 2>&1 &
```

Watch it:

```bash
tail -f /tmp/alertbot.log
```

---

## Stopping it

**Ctrl+C** in its terminal. If it is in the background:

```bash
pkill -f "python run.py"
```

Confirm nothing is left holding the port:

```bash
ss -ltnp | grep 8000     # no output = stopped
```

---

## Editing code while it runs

`run.py` starts uvicorn with `reload=True`, so saving any file under
`/workspaces/alertbot` restarts the app automatically — you will see
`WatchFiles detected changes` and a fresh startup block. No manual restart
needed for code changes.

Two things reload does **not** pick up:

- **`.env` changes** — restart properly for those.
- **Settings changed in the dashboard** — those live in `alerts.db` and are
  read at use time, so they take effect without any restart.

---

## When it will not start

| Symptom | Cause |
|---|---|
| `ModuleNotFoundError: No module named 'fastapi'` | You used bare `python`. Use `.venv/bin/python`. |
| `[Errno 98] Address already in use` | An older copy is still running. `pkill -f "python run.py"` and start again. |
| `AlertBot ready — auth OFF` | `DASHBOARD_PASSWORD` is missing from `.env`. |
| Starts, but no `Scheduler started` line | The scheduler failed — the dashboard will work but nothing will ever be polled or escalated. Read the traceback above it. |
| Silence for a minute | Normal. Startup is slow in this container. |

---

## The thing to remember

**The Codespace suspends after ~30 minutes idle, and takes the server with
it.** A suspended AlertBot polls no mailbox, raises no incident and rings no
phone. Nothing in this file changes that — it is the same objection
`CLAUDE.md` raises against a free host that sleeps. For real on-call use this
needs somewhere that stays awake; `render.yaml`, `Dockerfile` and `Procfile`
are already in the repo for when you want that.

---

## Full offline check

Independent of the running server, this exercises the whole pipeline in about
a minute:

```bash
.venv/bin/python tools/selftest.py
```

It points the channels at a throwaway localhost server, restores your real
settings afterwards and deletes its own data. Currently **39/39 passing**.
Section 11 reports missing *configuration* rather than broken code.

---

Next: `PORT-8000-PUBLIC.md` to let the phone in, then `PHONE-SETUP.md` Step 2
for ntfy.
