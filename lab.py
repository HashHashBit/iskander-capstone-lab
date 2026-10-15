#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Iskander Capstone — Kill-Chain Lab (INERT educational simulation).

This is a SAFE, self-contained SIMULATION of a phishing kill-chain for the
Iskander Cyber Bootcamp capstone. It runs entirely on your own machine:

  * It serves a fictitious company website (Rafid Financial Services) on
    http://localhost so you can practise OSINT / reconnaissance.
  * It lets you compose a phishing email and "send" it to a simulated inbox.
  * A simulated victim decides whether your email is convincing enough.
  * If it is, an INERT payload "runs" and reveals YOUR flag.

What it is NOT: there is no real email, no real malware, no real network
target, no keystroke capture, no data collection. Nothing leaves this
process. The "payload" does nothing but print your flag. Everything here is
non-routable (.local) and matches nothing real.

Run:  python lab.py
Then submit your flag at  https://iskander.sh/capstone
"""

import hashlib
import json
import os
import re
import subprocess
import sys
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
PORT = 8000

try:                                     # keep Arabic/unicode readable on Windows consoles
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# The exact derivation the portal uses, so the flag this lab reveals is the one
# the portal expects for your code (ctf_start in 20261013120000_capstone_portal.sql):
#   ISK{ first 8 bytes of sha256(code + ':iskander-capstone-v1') , hex }
FLAG_SALT = ":iskander-capstone-v1"
CODE_RE = re.compile(r"^ISK-[0-9A-F]{8}$")


def derive_flag(code):
    h = hashlib.sha256((code + FLAG_SALT).encode("utf-8")).digest()
    return "ISK{" + h[:8].hex() + "}"


def load(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        return json.load(f)


# ----------------------------------------------------------------- presentation
def line():
    print("-" * 68)


def banner():
    print()
    line()
    print("  ISKANDER CAPSTONE  -  KILL-CHAIN LAB  (inert simulation)")
    line()


def consent():
    print("""
This is an EDUCATIONAL SIMULATION. By continuing you confirm that:

  * You will use it only to learn, on your own machine.
  * You understand real phishing and malware against real people or
    systems is a crime, and this lab targets nothing real.
  * Everything here is a local, inert simulation for the Iskander
    Cyber Bootcamp capstone.
""")
    ans = input('Type  I AGREE  to continue: ').strip().lower()
    if ans not in ("i agree", "iagree"):
        print("Not confirmed. Exiting.")
        sys.exit(0)


def get_code():
    print("""
Enter your personal capstone code. Get it by signing in at
https://iskander.sh/capstone and pressing "Start". It looks like ISK-1A2B3C4D.
""")
    for _ in range(5):
        code = input("Your code: ").strip().upper()
        if CODE_RE.match(code):
            return code
        print("  That does not look like a code (expected ISK-XXXXXXXX). Try again.")
    print("No valid code entered. Exiting.")
    sys.exit(0)


# ----------------------------------------------------------------- recon server
def build_site():
    """Generate the Rafid recon site locally (no real flag in it: recon is pure OSINT)."""
    try:
        subprocess.run([sys.executable, os.path.join(HERE, "build_recon.py")],
                       cwd=HERE, check=True, stdout=subprocess.DEVNULL)
    except Exception as e:
        print("  (could not build the recon site: %s)" % e)
    for cand in (os.path.join(HERE, "dist"), os.path.join(HERE, "recon", "dist")):
        if os.path.isdir(cand):
            return cand
    return None


def serve(dist):
    import http.server
    import socketserver

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **k):
            super().__init__(*a, directory=dist, **k)

        def log_message(self, *a):
            pass

    httpd = socketserver.TCPServer(("127.0.0.1", PORT), Handler)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    return httpd


# ----------------------------------------------------------------- the victim
def gullibility(recipient, sender, subject, suppliers):
    """The simulated victim (Farah Karim, Accounts Payable) decides whether to open
    the attachment. Returns (ok, reason). A careful reader of the recon site passes
    on the first try; this mirrors the gullibility policy in 01-architecture.md.
    """
    rcpt = recipient.strip().lower()
    if "@" not in rcpt:
        rcpt += "@rafidfs.local"
    snd = sender.strip().lower()
    subj = subject.strip().lower()
    sup_domains = {s["domain"].lower() for s in suppliers}

    if rcpt == "y.karim@rafidfs.local":
        return False, "Yusuf Karim is in Facilities, not Finance. He does not process invoices. (Two Karims — pick the right one.)"
    if rcpt != "f.karim@rafidfs.local":
        return False, "That mailbox does not handle supplier invoices. Who in Accounts Payable opens every vendor invoice same-day? (Read /team and /contact.)"

    dom = snd.split("@")[-1] if "@" in snd else ""
    if dom == "rafidfs.local":
        return False, "An internal sender for an external vendor invoice looks wrong to AP. Impersonate a supplier Rafid actually pays. (Read /suppliers.)"
    if dom not in sup_domains:
        return False, "Farah does not recognise that sender. Impersonate one of Rafid's real suppliers so the invoice looks expected. (Read /suppliers.)"

    signals = ("invoice", "remittance", "payment", "same-day", "same day",
               "overdue", "statement", "فاتورة", "دفع", "حوالة", "مستحق")
    if not any(s in subj for s in signals):
        return False, "The subject does not read like a vendor invoice, so it does not jump the queue. What does Farah say she processes same-day? (Read /news.)"

    return True, "convincing"


def payload_reveal(flag):
    """INERT payload. In a real campaign this is where the student's tool would run.
    Here it does nothing but reveal the flag — no capture, no persistence, no network."""
    print("""
  [simulated victim] New mail from a known supplier about an invoice.
  [simulated victim] Opening the attachment to process it same-day...
  [inert payload]    (this is a SIMULATION: the payload does nothing but reveal your flag)
""")


# ----------------------------------------------------------------- the campaign
def campaign(flag, suppliers):
    print("""
RECON DONE?  Compose your phishing email. The victim is Rafid's Accounts
Payable specialist. To get her to open your attachment you must pick the
right recipient, impersonate a sender she trusts, and use a subject that
fits what she handles same-day. Re-read the site if a check fails.
""")
    attempts = 0
    while True:
        attempts += 1
        print()
        line()
        recipient = input("  To (recipient email):      ").strip()
        sender = input("  From (sender you impersonate): ").strip()
        subject = input("  Subject:                   ").strip()
        ok, reason = gullibility(recipient, sender, subject, suppliers)
        if ok:
            print("\n  >> The email is delivered to Farah's inbox.")
            payload_reveal(flag)
            line()
            print("  SUCCESS after %d attempt(s). Your flag:\n" % attempts)
            print("        " + flag + "\n")
            print("  Submit it at  https://iskander.sh/capstone")
            print("  Optional: record a Challenge Walkthrough for the 50% bonus")
            print("  (see the portal for the YouTube guidelines).")
            line()
            return
        print("\n  >> Rejected: " + reason)


def main():
    banner()
    consent()
    code = get_code()
    flag = derive_flag(code)

    suppliers = load("suppliers.json")

    print("\nBuilding your recon site...")
    dist = build_site()
    httpd = None
    if dist:
        try:
            httpd = serve(dist)
            print("\n  Recon site is live:  http://localhost:%d" % PORT)
            print("  Open it in your browser and investigate Rafid Financial Services.")
            print("  Learn: who processes invoices, which suppliers to impersonate,")
            print("  and what subject gets processed same-day.")
        except Exception as e:
            print("  (could not start the local server: %s)" % e)
            print("  You can still open the generated site under: %s" % dist)
    input("\nPress Enter when you have finished your recon and are ready to phish...")

    try:
        campaign(flag, suppliers)
    finally:
        if httpd:
            httpd.shutdown()


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nBye.")
