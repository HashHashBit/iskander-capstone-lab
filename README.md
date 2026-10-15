# Iskander Capstone — Kill-Chain Lab

An **inert, local, educational simulation** of a phishing kill-chain, for the
[Iskander Cyber Bootcamp](https://iskander.sh) capstone (Course 0).

> ⚠️ **This is a safe simulation.** There is **no real email, no real malware,
> no real network target, no keystroke capture, and no data collection.**
> When you run it, a **local mail server** and a **web UI** start on your own
> machine. The phishing email you send never leaves your computer — it goes to
> the lab's local mail server, where a *simulated* victim reads it. The company
> is fictitious on a non-routable `.local` domain. The "payload" does nothing
> but reveal your flag. Use it only to learn. Real phishing or malware against
> real people or systems is a crime.

## What you do

1. Sign in at **https://iskander.sh/capstone**, press **Start**, and copy your
   personal code (looks like `ISK-1A2B3C4D`).
2. Run the lab (below). It starts a local mail server + a web UI and opens your
   browser at **http://localhost:8000**.
3. In the browser: paste your code, then **open the Rafid Financial Services
   site** and do your reconnaissance (OSINT).
4. Work out **who** processes invoices, **which supplier** to impersonate, and
   **what subject** gets processed same-day.
5. **Compose and send** the phishing email. It's delivered over SMTP to the
   lab's local mail server, where the simulated victim reads it. If it's
   convincing, your **flag** appears.
6. Submit the flag back at **https://iskander.sh/capstone** to pass Part 1.

The flag is derived from *your* code, so every student's flag is different —
copying someone else's does not work. If your email is rejected, the lab tells
you why; re-read the site and try again.

## Requirements

- **Python 3.8+** — standard library only. **No `pip install`, no dependencies.**
- A web browser. Any OS (Windows, macOS, Linux). Runs entirely offline.

## Run

```bash
python lab.py
```

Or double-click **`run.bat`** on Windows / run **`./run.sh`** on macOS/Linux.
Your browser opens at `http://localhost:8000`. Press `Ctrl+C` in the terminal to
stop the lab.

## The two halves of the capstone

This lab is **Part 1** (the operation). **Part 2** is a Pull Request to the
educational keylogger repo — see the capstone page. Finishing both earns the
certificate; an optional, policy-compliant *Challenge Walkthrough* video earns a
50% course discount. Details and the YouTube guidelines are on the portal and in
the CTF intro chapter.

## Files

| File | Role |
|---|---|
| `lab.py` | The backend: local SMTP mail server, web UI, the victim, and the inert flag reveal |
| `build_recon.py` | Dependency-free generator for the Rafid recon site |
| `data/*.json` | The fictitious company (identity, staff, suppliers, posts) |

Educational use only, within the Iskander Cyber Bootcamp.
