# Testing AlertBot

Two ways to check things work.

- **Automatic** — `python tools/selftest.py` proves the whole pipeline in about
  a minute without touching your phone, your mailbox or the internet.
- **Manual** — the walkthrough below proves the part no script can: that a real
  phone actually wakes you up.

Do the automatic one first. If it fails, the manual walkthrough will fail too.

---

## Test 0 · Is the mailbox reachable?

```
.venv\Scripts\python tools\check_mailbox.py
```

**Expect**

```
Host    : mail.esicia.rw:993
Mailbox : digne@esicia.rw
OK — connected as digne@esicia.rw
INBOX: 1423 message(s), 7 unread
Folders on the server:
  - INBOX
  - INBOX.Sent
  ...
```

**If it fails**

| Message | Meaning |
|---|---|
| `No mailbox credentials configured` | `MAILBOX_PASSWORD` is still empty in `.env` |
| `LOGIN failed` / `AUTHENTICATIONFAILED` | Wrong password, or the mailbox needs the full address as the username |
| `certificate verify failed` / `getaddrinfo failed` | Wrong `IMAP_HOST`. cPanel → Email Accounts → Connect Devices shows the real one — sometimes `serverN.host.com`, not `mail.esicia.rw` |
| Connects, but the alerts are not in `INBOX` | Pick the right folder from the printed list and set `IMAP_FOLDER` in `.env` |

AlertBot does **not** mark mail as read and does not care whether you have read
it — it tracks its own position by IMAP UID. Reading your mail normally cannot
hide an alert from it.

---

## Test 1 · The automatic self-test

```
.venv\Scripts\python tools\selftest.py
```

It starts a fake "phone" on localhost, points the notification channels at it,
runs the real code, then puts your settings back and deletes its own test data.
**Nothing is sent to ntfy.sh, MacroDroid, Firebase or your mailbox.**

**Expect** `39/39 checks passed` once configuration is complete. Until then the
section-11 checks fail on purpose — they are a to-do list, not a bug.

It covers: every page loads · login protection · an alert reaching the phone ·
duplicate alerts not spamming · repeat-until-acknowledged · escalation ·
acknowledgement silencing it · recovery closing it · rules matching the right
mail · WhatsApp chats raising incidents · stats, history and CSV.

Section 11 is the exception: it reports missing configuration rather than broken
code. `mailbox credentials present` fails until `MAILBOX_PASSWORD` is in `.env`,
and `a real notification channel is configured` fails until you save an ntfy
topic or MacroDroid webhook. That check reads your saved settings, not the mock
ones the test just used, so it cannot pass by accident.

Run this again after any change — it is the fastest way to know nothing broke.

---

## Test 2 · Start it up

```
.venv\Scripts\python -m uvicorn app.main:app --reload
```

Open <http://127.0.0.1:8000>. The browser asks for a username and password —
they are `DASHBOARD_USER` and `DASHBOARD_PASSWORD` from `.env`.

**Expect** the dark dashboard, a green live dot at the top right, and stat tiles
showing zeroes. A red banner saying *No notification channel is enabled* is
correct at this point — Test 3 fixes it.

---

## Test 3 · Wake the phone with ntfy

1. Install **ntfy** from the Play Store.
2. On the dashboard go to **Phone** (`/setup`), copy the generated topic, and
   subscribe to it in the ntfy app (**+** → paste → Subscribe).
3. Back on `/setup`, paste the same topic into step 3 and press **Save topic**.
4. Press **Send test**.

**Expect** the phone to buzz within a couple of seconds with *AlertBot test
notification*.

**If nothing arrives**

- Is the topic identical in both places? A single typo means silence.
- Does the ntfy app show *Connected* at the top of the topic screen?
- Is the phone's battery optimisation killing ntfy? Settings → Apps → ntfy →
  Battery → **Unrestricted**.
- Settings → Mailbox/notification panel: press **Test** next to ntfy and read
  the error toast — it reports the real HTTP failure.

Then make it loud: in the ntfy app open the topic → ⋮ → Notification settings →
alarm-style sound, priority **Max**, and allow it to override Do Not Disturb.

---

## Test 4 · The whole chain, for real

On the dashboard press **🚨 Test alert** (top right).

**Expect, in order**

1. The phone rings — *CRITICAL — portal.esicia.rw* or similar.
2. A red incident card appears on the dashboard with a pulsing border.
3. `Open` and `Unacknowledged` tiles both show 1.
4. **Two minutes later the phone rings again**, titled *STILL DOWN*. This is the
   point of the whole system: it does not give up.
5. Press **Acknowledge** on the dashboard (or the Acknowledge action in the
   notification). The card turns amber, and the repeat stops.
6. Open the incident (**Details →**) and check the timeline shows every push
   with its delivery result.

If step 4 does not happen, check Settings → Escalation → *Repeat until
acknowledged* is on, and that you did not acknowledge it too early.

---

## Test 5 · The night test

The one that actually matters. Before trusting AlertBot with a night:

1. Put the phone on **silent**, screen off, in another room.
2. From a laptop, open the dashboard and press **Test alert**.
3. Go to the other room.

**Expect** to have heard it. If a silent phone stays silent, a push notification
alone is not enough — set up the MacroDroid alarm (`/setup` step 2), which
forces the alarm stream to full volume and loops a siren, or install the Android
app (`/setup` step 4) for a full-screen lock-screen alarm.

Leave one incident unacknowledged overnight and check in the morning that the
notification log shows it retried the whole time.

---

## Test 6 · A real monitoring email

Sending yourself a fake Pingdom email will not work — the rules only trust the
five known senders, and your address is not one of them.

Two honest ways to test:

**A · Wait for a real alert.** The most truthful test. Keep the server running
and check `/history` after the next genuine Pingdom or ESICIA Monitor mail.

**B · Test the rules with the real text.** Open a genuine alert email you have
already received, copy the sender, subject and body into
**Settings → Rule tester**, and press **Test rules**.

**Expect** *Would raise an incident*, with the matched sender and keywords, the
chosen parser, and the service name it extracted. Tick **Actually create the
incident** to run the full path including the phone alarm.

This is also how you check a *new* alert format the parsers have not seen — if
the service name comes out as `unknown-service`, that provider needs parser
work.

---

## Test 7 · WhatsApp chats

Watched chats: **ESICIA Team** and **Vubavuba Africa**, both set to alarm on
every message.

**Without the phone:** Settings → WhatsApp chats → type `ESICIA Team` and a
message → **Test a message**. Expect *Incident raised — the phone would ring*.

**With the phone**, once the MacroDroid macro from `/setup` step 3 exists:

1. Have someone send a message in one of the two chats (or send one yourself
   from another device).
2. Expect an incident within seconds, and the phone to ring.
3. A message in any other chat must do nothing — check `/history` stays quiet.

**If nothing happens**

- The macro must target **WhatsApp Business** (`com.whatsapp.w4b`), not
  WhatsApp. They are separate apps in MacroDroid's list.
- MacroDroid needs notification access (it prompts on first run).
- A muted chat produces no notification at all, so there is nothing to react to.
- The phone must be able to reach AlertBot. On `127.0.0.1` it cannot — see below.

---

## Test 8 · Can the phone even reach AlertBot?

While AlertBot runs on your PC, the phone needs your PC's LAN address, not
`127.0.0.1`.

1. Find it: `ipconfig` → IPv4 Address, e.g. `192.168.1.20`.
2. Start the server so it listens beyond localhost:
   `.venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0`
3. Set `PUBLIC_URL=http://192.168.1.20:8000` in `.env` and restart, so
   notification taps open the dashboard.
4. On the phone's browser open `http://192.168.1.20:8000/healthz`.

**Expect** `{"status":"ok","app":"AlertBot"}`.

If it times out, Windows Firewall is blocking Python — allow it on private
networks. Note this only works on the same Wi-Fi, and the address changes when
your PC's IP does. That is the argument for deploying.

---

## Test 9 · Install the dashboard as an app

- **Android/Chrome:** ⋮ → *Add to Home screen*.
- **iPhone/Safari:** Share → *Add to Home Screen*.

**Expect** an AlertBot icon that opens without browser chrome, and works
one-handed: the sidebar becomes a bottom bar and incidents stack vertically.

---

## Quick reference

| Symptom | Where to look |
|---|---|
| Poll finds nothing | `tools/check_mailbox.py`; is `IMAP_FOLDER` right? |
| No notification anywhere | Settings → is a channel enabled? Press its **Test** |
| ntfy silent on a locked phone | ntfy topic settings: priority Max, override DND, battery unrestricted |
| Alarm never repeats | Settings → Escalation → *Repeat until acknowledged* |
| Phone cannot reach the server | Test 8 — LAN address, `--host 0.0.0.0`, firewall |
| WhatsApp macro never fires | Wrong app (`com.whatsapp.w4b`), no notification access, or the chat is muted |
| Something broke after a change | `python tools/selftest.py` |

Server logs print every decision — `Incident #12 OPENED`,
`Notification OPENED via ntfy: OK`, `Re-alerting incident #12` — so the console
is usually faster than guessing.
