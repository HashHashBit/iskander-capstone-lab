# Iskander Capstone — Kill-Chain Lab

An **inert, local, educational simulation** of a phishing kill-chain, for the
[Iskander Cyber Bootcamp](https://iskander.sh) capstone (Course 0).

> **This is a safe simulation.** There is **no real email, no real malware,
> no real network target, no keystroke capture, and no data collection.**
> The lab runs [Mailpit](https://mailpit.axe.email) (the same open-source
> mail server from Lecture 5) on your own machine. Phishing emails you send
> never leave your computer — Mailpit never relays. The company is fictitious
> on a non-routable `.local` domain. Use it only to learn. Real phishing or
> malware against real people or systems is a crime.

## What you do

1. Sign in at **https://iskander.sh/capstone**, press **Start**, and copy your
   personal code (looks like `ISK-1A2B3C4D`).
2. Run the lab (below). It starts **Mailpit** (SMTP + web UI) and opens a
   dashboard at **http://localhost:8000**.
3. In the dashboard: paste your code, then **open the Rafid Financial Services
   site** and do your reconnaissance (OSINT).
4. Work out **who** processes invoices, **which supplier** to impersonate, and
   **what subject** gets processed same-day.
5. **Send a phishing email via SMTP** to the local Mailpit server. Adapt
   `send-phish.py` from Lecture 5 or craft your own MIME email — the email must
   include the **filename-disguise technique** you learned in Lecture 5.
6. The lab's evaluator bot watches incoming mail and grades it automatically.
   The dashboard shows which criteria passed and which need work.
7. When all criteria pass, your **flag** appears on the dashboard.
8. Submit the flag back at **https://iskander.sh/capstone** to pass Part 1.

The flag is derived from *your* code, so every student's flag is different —
copying someone else's does not work.

## Requirements

- **Python 3.8+** — standard library only. **No `pip install`, no dependencies.**
- A web browser. Any OS (Windows, macOS, Linux). Runs entirely offline after
  the one-time Mailpit download.
- **Mailpit** is auto-downloaded on first run. If the download fails (firewall,
  no internet), install it manually: https://mailpit.axe.email/docs/install/

## Run

```bash
python lab.py
```

Or double-click **`run.bat`** on Windows / run **`./run.sh`** on macOS/Linux.

The dashboard opens at `http://localhost:8000`. Mailpit's web UI is at
`http://localhost:8025` (see your emails arrive). SMTP is at
`127.0.0.1:1025`. Press `Ctrl+C` in the terminal to stop.

## The two halves of the capstone

This lab is **Part 1** (the operation). **Part 2** is a Pull Request to the
educational keylogger repo — see the capstone page. Finishing both earns the
certificate; an optional, policy-compliant *Challenge Walkthrough* video earns a
50% course discount. Details and the YouTube guidelines are on the portal and in
the CTF intro chapter.

## Files

| File | Role |
|---|---|
| `lab.py` | The lab: starts Mailpit, the recon site, the evaluator bot, and the dashboard |
| `build_recon.py` | Dependency-free generator for the Rafid recon site |
| `data/*.json` | The fictitious company (identity, staff, suppliers, posts) |

Educational use only, within the Iskander Cyber Bootcamp.
