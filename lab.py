#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Iskander Capstone - Kill-Chain Lab (INERT educational simulation, web UI).

A SAFE, self-contained simulation of a phishing kill-chain for the Iskander
Cyber Bootcamp capstone. Everything runs on your own machine:

  * A LOCAL MAIL SERVER (SMTP, like Mailpit in Lecture 5) runs in the backend.
  * A WEB UI (http://localhost:8000) lets you enter your code, do recon on a
    fake company, and compose + SEND a phishing email over real SMTP.
  * A simulated victim reads your mail from the server and decides whether it
    is convincing. If it is, an INERT payload reveals YOUR flag.

What it is NOT: no real email leaves this machine, no real malware, no real
target, no capture, no data collection. The mail server never relays outside.
The "payload" does nothing but reveal your flag. The company is fictitious on
a non-routable .local domain.

Run:  python lab.py     (then your browser opens http://localhost:8000)
Submit your flag at  https://iskander.sh/capstone
"""

import email as emaillib
import hashlib
import http.server
import json
import mimetypes
import os
import re
import smtplib
import socket
import subprocess
import sys
import threading
import webbrowser
from email.message import EmailMessage

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
DIST = os.path.join(HERE, "dist")
WEB_HOST, WEB_PORT = "127.0.0.1", 8000
SMTP_HOST, SMTP_PORT = "127.0.0.1", 1025

# Same derivation the portal uses (ctf_start): ISK{ first 8 bytes of
# sha256(code + ':iskander-capstone-v1'), hex }. Kept private in student docs.
FLAG_SALT = ":iskander-capstone-v1"
CODE_RE = re.compile(r"^ISK-[0-9A-F]{8}$")

SUPPLIERS = []


def derive_flag(code):
    h = hashlib.sha256((code + FLAG_SALT).encode("utf-8")).digest()
    return "ISK{" + h[:8].hex() + "}"


def load_json(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        return json.load(f)


# ----------------------------------------------------------- the victim policy
def gullibility(recipient, sender, subject):
    """Farah Karim (Accounts Payable) decides whether to open the attachment.
    A careful reader of the recon site passes on the first try."""
    rcpt = (recipient or "").strip().lower()
    m = re.search(r"[\w.+-]+@[\w.-]+", rcpt)
    if m:
        rcpt = m.group(0)
    elif "@" not in rcpt and rcpt:
        rcpt += "@rafidfs.local"
    snd = (sender or "").strip().lower()
    ms = re.search(r"[\w.+-]+@[\w.-]+", snd)
    snd = ms.group(0) if ms else snd
    subj = (subject or "").strip().lower()
    sup_domains = {s["domain"].lower() for s in SUPPLIERS}

    if rcpt == "y.karim@rafidfs.local":
        return False, "Yusuf Karim is in Facilities, not Finance. He does not process invoices. There are two Karims: pick the one in Accounts Payable."
    if rcpt != "f.karim@rafidfs.local":
        return False, "That mailbox does not handle supplier invoices. Who in Accounts Payable opens every vendor invoice same-day? Read the Team and Contact pages."

    dom = snd.split("@")[-1] if "@" in snd else ""
    if dom == "rafidfs.local":
        return False, "An internal sender for an external vendor invoice looks wrong to AP. Impersonate a supplier Rafid actually pays. Read the Suppliers page."
    if dom not in sup_domains:
        return False, "Farah does not recognise that sender. Impersonate one of Rafid's real suppliers so the invoice looks expected. Read the Suppliers page."

    signals = ("invoice", "remittance", "payment", "same-day", "same day",
               "overdue", "statement", "فاتورة", "دفع", "حوالة", "مستحق")
    if not any(s in subj for s in signals):
        return False, "The subject does not read like a vendor invoice, so it does not jump the queue. What does Farah say she processes same-day? Read the News page."

    return True, "Farah recognised the supplier and opened the attachment to process the invoice same-day."


# -------------------------------------------------------- the local mail store
class MailStore:
    def __init__(self):
        self.msgs = []

    def add(self, raw):
        self.msgs.append(raw)


STORE = MailStore()


def handle_smtp(conn):
    """A minimal SMTP receiver: enough of the protocol for smtplib to deliver a
    message. Stores the raw message. Never relays anywhere (closed lab)."""
    rf = conn.makefile("rb")

    def reply(s):
        try:
            conn.sendall((s + "\r\n").encode("utf-8"))
        except Exception:
            pass

    reply("220 iskander-lab ESMTP (inert simulation)")
    mail_from, rcpts = None, []
    while True:
        line = rf.readline()
        if not line:
            break
        cmd = line.decode("utf-8", "replace").rstrip("\r\n")
        up = cmd.upper()
        if up.startswith("EHLO") or up.startswith("HELO"):
            reply("250 iskander-lab")
        elif up.startswith("MAIL FROM"):
            mail_from = cmd[10:].strip()
            reply("250 OK")
        elif up.startswith("RCPT TO"):
            rcpts.append(cmd[8:].strip())
            reply("250 OK")
        elif up == "DATA":
            reply("354 End data with <CR><LF>.<CR><LF>")
            data = []
            while True:
                dl = rf.readline()
                if not dl or dl in (b".\r\n", b".\n"):
                    break
                if dl.startswith(b".."):
                    dl = dl[1:]
                data.append(dl)
            STORE.add(b"".join(data))
            reply("250 OK: message queued")
            mail_from, rcpts = None, []
        elif up == "QUIT":
            reply("221 Bye")
            break
        elif up == "RSET":
            mail_from, rcpts = None, []
            reply("250 OK")
        else:
            reply("250 OK")
    try:
        conn.close()
    except Exception:
        pass


def smtp_server():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((SMTP_HOST, SMTP_PORT))
    srv.listen(8)
    while True:
        conn, _ = srv.accept()
        threading.Thread(target=handle_smtp, args=(conn,), daemon=True).start()


def send_phish(to, frm, subject, body):
    """Build a MIME email and send it over real SMTP to the local mail server,
    with a benign (inert) attachment standing in for the payload."""
    m = EmailMessage()
    m["To"] = to or ""
    m["From"] = frm or ""
    m["Subject"] = subject or ""
    m.set_content(body or "Please find the attached invoice for same-day processing.")
    m.add_attachment(b"INERT SIMULATION - this attachment contains no real payload.",
                     maintype="application", subtype="octet-stream",
                     filename="Invoice-2026.pdf")
    s = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=5)
    try:
        s.send_message(m)
    finally:
        try:
            s.quit()
        except Exception:
            pass


def handle_send(data):
    code = (data.get("code") or "").strip().upper()
    if not CODE_RE.match(code):
        return {"ok": False, "reason": "Enter your code (looks like ISK-1A2B3C4D) first.", "need_code": True}
    to = (data.get("to") or "").strip()
    frm = (data.get("from") or "").strip()
    subject = (data.get("subject") or "").strip()
    body = (data.get("body") or "").strip()
    if not (to and frm and subject):
        return {"ok": False, "reason": "Fill in the recipient, the sender you impersonate, and the subject."}

    try:
        send_phish(to, frm, subject, body)
    except Exception as e:
        return {"ok": False, "reason": "Could not reach the local mail server (is the lab still running?): %s" % e}

    # The victim reads the message back FROM the mail server (proves the round trip).
    raw = STORE.msgs[-1] if STORE.msgs else b""
    em = emaillib.message_from_bytes(raw) if raw else None
    r_to = em.get("To", "") if em else to
    r_from = em.get("From", "") if em else frm
    r_subj = em.get("Subject", "") if em else subject

    ok, reason = gullibility(r_to, r_from, r_subj)
    inbox = []
    for m in STORE.msgs[-6:]:
        e = emaillib.message_from_bytes(m)
        inbox.append({"to": e.get("To", ""), "from": e.get("From", ""), "subject": e.get("Subject", "")})
    out = {"ok": ok, "reason": reason, "inbox": inbox}
    if ok:
        out["flag"] = derive_flag(code)
    return out


# --------------------------------------------------------------------- web UI
UI_HTML = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Iskander Capstone - Kill-Chain Lab</title>
<style>
:root{--bg:#0e1116;--card:#171c24;--line:#2a313c;--ink:#e6e9ee;--mut:#9aa4b2;--acc:#c9a227;--green:#46a05a;--red:#d16565;}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.6 system-ui,Segoe UI,Roboto,sans-serif}
.wrap{max-width:760px;margin:0 auto;padding:24px 16px 60px}
h1{font-size:22px;margin:.2em 0}.sub{color:var(--mut);margin:0 0 18px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px 18px;margin:14px 0}
.card h2{font-size:16px;margin:.1em 0 .5em}
label{display:block;color:var(--mut);font-size:13px;margin:10px 0 4px}
input,textarea{width:100%;background:#0e1319;border:1px solid var(--line);color:var(--ink);border-radius:7px;padding:9px 10px;font:14px monospace}
textarea{min-height:70px;font-family:system-ui}
.row{display:flex;gap:10px;flex-wrap:wrap}.row>div{flex:1;min-width:220px}
button{background:var(--acc);color:#0e1116;border:0;border-radius:7px;padding:10px 16px;font-weight:700;cursor:pointer;font-size:14px}
button.ghost{background:transparent;color:var(--acc);border:1px solid var(--acc)}
a{color:var(--acc)}
.note{color:var(--mut);font-size:13px}
.flag{font:18px/1.5 monospace;font-weight:700;color:var(--acc);background:#0e1319;border:1px solid var(--line);border-radius:7px;padding:10px 12px;margin:8px 0;word-break:break-all}
.ok{color:var(--green)}.bad{color:var(--red)}
.inbox{font:13px monospace;color:var(--mut)}
.inbox div{padding:5px 0;border-top:1px solid var(--line)}
.warn{background:rgba(201,162,39,.1);border:1px solid rgba(201,162,39,.4);border-radius:8px;padding:10px 12px;font-size:13px;color:var(--mut)}
.step{color:var(--acc);font-weight:700}
.hidden{display:none}
</style></head><body><div class="wrap">
<h1>Iskander Capstone - Kill-Chain Lab</h1>
<p class="sub">Inert local simulation - no real email, malware, or target. Everything runs on your machine.</p>

<div class="warn">This is an educational simulation for the Iskander Cyber Bootcamp. Real phishing or malware against real people or systems is a crime. This lab targets a fictitious company (<code>rafidfs.local</code>) and does nothing harmful.</div>

<div class="card">
  <h2><span class="step">1.</span> Your code</h2>
  <p class="note">Sign in at <a href="https://iskander.sh/capstone" target="_blank">iskander.sh/capstone</a>, press Start, and paste your personal code here. It looks like <code>ISK-1A2B3C4D</code>.</p>
  <input id="code" placeholder="ISK-XXXXXXXX" autocomplete="off" spellcheck="false">
</div>

<div class="card">
  <h2><span class="step">2.</span> Reconnaissance</h2>
  <p class="note">Investigate the target company. Work out who processes invoices, which supplier to impersonate, and what subject gets processed same-day.</p>
  <p><a href="/recon/" target="_blank"><button class="ghost" type="button">Open the Rafid Financial Services site</button></a></p>
</div>

<div class="card">
  <h2><span class="step">3.</span> Compose &amp; send the phishing email</h2>
  <p class="note">Your email is sent over SMTP to the lab's local mail server, where the victim reads it.</p>
  <div class="row">
    <div><label for="to">To (recipient email)</label><input id="to" placeholder="f.lastname@rafidfs.local" autocomplete="off"></div>
    <div><label for="from">From (the sender you impersonate)</label><input id="from" placeholder="name@supplier.local" autocomplete="off"></div>
  </div>
  <label for="subject">Subject</label><input id="subject" placeholder="..." autocomplete="off">
  <label for="body">Body (optional)</label><textarea id="body" placeholder="Dear ..."></textarea>
  <p style="margin-top:12px"><button id="send" type="button">Send phishing email</button></p>
</div>

<div class="card hidden" id="result">
  <h2>Mail server &amp; victim</h2>
  <div id="verdict"></div>
  <div class="flag hidden" id="flagbox"></div>
  <div id="flagmsg" class="note hidden">Submit this flag at <a href="https://iskander.sh/capstone" target="_blank">iskander.sh/capstone</a>. Optional: record a <b>Challenge Walkthrough</b> for the 50% bonus (see the portal for YouTube guidelines).</div>
  <h2 style="margin-top:16px">Inbox (local mail server)</h2>
  <div class="inbox" id="inbox"></div>
</div>

<script>
function $(id){return document.getElementById(id)}
$('send').addEventListener('click',function(){
  var btn=this; btn.disabled=true; btn.textContent='Sending...';
  var payload={code:$('code').value,to:$('to').value,from:$('from').value,subject:$('subject').value,body:$('body').value};
  fetch('/send',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify(payload)})
    .then(function(r){return r.json()})
    .then(function(d){
      $('result').classList.remove('hidden');
      var v=$('verdict');
      if(d.ok){ v.innerHTML='<p class="ok">✔ '+esc(d.reason)+'</p>';
        $('flagbox').textContent=d.flag; $('flagbox').classList.remove('hidden'); $('flagmsg').classList.remove('hidden');
      } else { v.innerHTML='<p class="bad">✖ '+esc(d.reason)+'</p>';
        $('flagbox').classList.add('hidden'); $('flagmsg').classList.add('hidden'); }
      var box=$('inbox'); box.innerHTML='';
      (d.inbox||[]).forEach(function(m){var x=document.createElement('div');
        x.textContent='To: '+(m.to||'')+'  |  From: '+(m.from||'')+'  |  Subject: '+(m.subject||'');box.appendChild(x);});
      $('result').scrollIntoView({behavior:'smooth'});
    })
    .catch(function(){$('result').classList.remove('hidden');$('verdict').innerHTML='<p class="bad">Network error talking to the lab.</p>';})
    .then(function(){btn.disabled=false;btn.textContent='Send phishing email';});
});
function esc(s){var d=document.createElement('div');d.textContent=s==null?'':s;return d.innerHTML;}
</script>
</div></body></html>"""


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="text/html; charset=utf-8"):
        b = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        try:
            self.wfile.write(b)
        except Exception:
            pass

    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/", "/index.html"):
            self._send(200, UI_HTML)
        elif path.startswith("/recon/"):
            self._serve_recon(path[len("/recon/"):])
        else:
            self._send(404, "not found", "text/plain")

    def _serve_recon(self, rel):
        if rel == "" or rel.endswith("/"):
            rel += "index.html"
        full = os.path.normpath(os.path.join(DIST, rel))
        if not full.startswith(DIST) or not os.path.isfile(full):
            self._send(404, "not found", "text/plain")
            return
        ctype = mimetypes.guess_type(full)[0] or "application/octet-stream"
        with open(full, "rb") as f:
            self._send(200, f.read(), ctype)

    def do_POST(self):
        if self.path != "/send":
            self._send(404, "not found", "text/plain")
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            data = json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception:
            self._send(400, json.dumps({"ok": False, "reason": "bad request"}), "application/json")
            return
        self._send(200, json.dumps(handle_send(data)), "application/json; charset=utf-8")


def build_site():
    try:
        subprocess.run([sys.executable, os.path.join(HERE, "build_recon.py")],
                       cwd=HERE, check=True, stdout=subprocess.DEVNULL)
    except Exception as e:
        print("  (could not build the recon site: %s)" % e)


def main():
    global SUPPLIERS
    SUPPLIERS = load_json("suppliers.json")
    print("Building the recon site...")
    build_site()

    threading.Thread(target=smtp_server, daemon=True).start()
    httpd = http.server.ThreadingHTTPServer((WEB_HOST, WEB_PORT), Handler)

    url = "http://%s:%d" % (WEB_HOST, WEB_PORT)
    print("\n  Iskander Capstone lab is running (inert simulation).")
    print("  Local mail server: %s:%d  |  Web UI: %s" % (SMTP_HOST, SMTP_PORT, url))
    print("  Open %s in your browser. Press Ctrl+C here to stop.\n" % url)
    if "--no-browser" not in sys.argv:
        try:
            webbrowser.open(url)
        except Exception:
            pass
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping. Bye.")


if __name__ == "__main__":
    main()
