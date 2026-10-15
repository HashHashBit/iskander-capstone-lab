# Iskander Capstone — Kill-Chain Lab

An **inert, local, educational simulation** of a phishing kill-chain, for the
[Iskander Cyber Bootcamp](https://iskander.sh) capstone (Course 0).

> ⚠️ **This is a safe simulation.** There is **no real email, no real malware,
> no real network target, no keystroke capture, and no data collection.**
> Everything runs on your own machine and targets a fictitious company on a
> non-routable `.local` domain that matches nothing real. The "payload" does
> nothing but reveal your flag. Use it only to learn. Real phishing or malware
> against real people or systems is a crime.

## What you do

1. Sign in at **https://iskander.sh/capstone** and press **Start** to get your
   personal code (looks like `ISK-1A2B3C4D`).
2. Run the lab. It serves a fake company website (**Rafid Financial Services**)
   on `http://localhost:8000` for you to investigate (OSINT / reconnaissance).
3. From your recon, work out **who** processes invoices, **which supplier** to
   impersonate, and **what subject** gets processed same-day.
4. Compose your phishing email. A simulated victim decides whether it is
   convincing. If it is, an inert payload "runs" and reveals **your flag**.
5. Submit the flag back at **https://iskander.sh/capstone** to pass Part 1.

The flag is derived from *your* code, so every student's flag is different —
copying someone else's does not work. If your email is rejected, the lab tells
you why; re-read the site and try again.

## Requirements

- **Python 3.8+** — standard library only. **No `pip install`, no dependencies.**
- Any OS (Windows, macOS, Linux). Runs entirely offline.

## Run

```bash
python lab.py
```

Or double-click **`run.bat`** on Windows / run **`./run.sh`** on macOS/Linux.

## The two halves of the capstone

This lab is **Part 1** (the operation). **Part 2** is a Pull Request to the
educational keylogger repo — see the capstone page. Finishing both earns the
certificate; an optional, policy-compliant *Challenge Walkthrough* video earns a
50% course discount. Details and the YouTube guidelines are on the portal.

## Files

| File | Role |
|---|---|
| `lab.py` | The whole simulation: consent, code → flag, recon server, phishing, inert reveal |
| `build_recon.py` | Dependency-free generator for the Rafid recon site |
| `data/*.json` | The fictitious company (identity, staff, suppliers, posts) |

Educational use only, within the Iskander Cyber Bootcamp.
