#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Iskander Capstone - Kill-Chain Lab

An educational simulation for the Iskander Cyber Bootcamp capstone.
Uses Mailpit (the same open-source mail server from Lecture 5) as a
real SMTP + web-mail interface.  The student sends a phishing email
via SMTP — adapting send-phish.py from Lecture 5 or crafting their
own — and a background evaluator grades it automatically.

What this starts:
  1. Mailpit  (SMTP on port 1025, web UI + REST API on port 8025)
  2. The Rafid Financial Services recon site  (on /recon/)
  3. An evaluator bot that watches incoming mail via the Mailpit API
  4. A dashboard at http://localhost:8000 showing progress + flag

No real email leaves this machine.  Mailpit never relays.
The company is fictitious on a non-routable .local domain.

Run:  python lab.py     (opens http://localhost:8000)
"""

import hashlib
import http.server
import json
import mimetypes
import os
import platform
import re
import shutil
import socket
import stat
import subprocess
import sys
import tarfile
import threading
import time
import webbrowser
import zipfile
from urllib.request import urlopen, Request
from urllib.error import URLError

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
DIST = os.path.join(HERE, "dist")

WEB_HOST, WEB_PORT = "127.0.0.1", 8000
MAILPIT_SMTP = 1025
MAILPIT_HTTP = 8025
MAILPIT_API = "http://127.0.0.1:%d/api/v1" % MAILPIT_HTTP
MAILPIT_DIR = os.path.join(HERE, ".mailpit")

FLAG_SALT = ":iskander-capstone-v1"
CODE_RE = re.compile(r"^ISK-[0-9A-F]{8}$")
RLO = "‮"

SUPPLIERS = []

# ------------------------------------------------------------------ state
_lock = threading.Lock()
_state = {
    "code": None,
    "latest_eval": None,
    "flag": None,
    "solved": False,
}


def derive_flag(code):
    h = hashlib.sha256((code + FLAG_SALT).encode("utf-8")).digest()
    return "ISK{" + h[:8].hex() + "}"


def load_json(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        return json.load(f)


def _maybe_solve():
    ev = _state.get("latest_eval")
    if _state["code"] and ev and ev.get("passed"):
        _state["flag"] = derive_flag(_state["code"])
        _state["solved"] = True


# ------------------------------------------------------ Mailpit management
def _mailpit_exe():
    return "mailpit.exe" if sys.platform == "win32" else "mailpit"


def _find_mailpit():
    found = shutil.which("mailpit")
    if found:
        return found
    local = os.path.join(MAILPIT_DIR, _mailpit_exe())
    if os.path.isfile(local):
        return local
    return None


def _mailpit_url():
    s = sys.platform
    m = platform.machine().lower()
    if s == "win32":
        return "https://github.com/axllent/mailpit/releases/latest/download/mailpit-windows-amd64.zip"
    elif s == "darwin":
        arch = "arm64" if m in ("arm64", "aarch64") else "amd64"
        return "https://github.com/axllent/mailpit/releases/latest/download/mailpit-darwin-%s.tar.gz" % arch
    else:
        arch = "arm64" if m in ("arm64", "aarch64") else "amd64"
        return "https://github.com/axllent/mailpit/releases/latest/download/mailpit-linux-%s.tar.gz" % arch


def _download_mailpit():
    url = _mailpit_url()
    os.makedirs(MAILPIT_DIR, exist_ok=True)
    is_zip = url.endswith(".zip")
    archive = os.path.join(MAILPIT_DIR, "mailpit" + (".zip" if is_zip else ".tar.gz"))

    print("  Downloading Mailpit...")
    req = Request(url, headers={"User-Agent": "iskander-capstone-lab/1.0"})
    with urlopen(req, timeout=120) as resp:
        total = int(resp.headers.get("Content-Length") or 0)
        got = 0
        with open(archive, "wb") as f:
            while True:
                chunk = resp.read(65536)
                if not chunk:
                    break
                f.write(chunk)
                got += len(chunk)
                if total:
                    print("\r  Downloading Mailpit... %d%%" % (got * 100 // total), end="", flush=True)
        if total:
            print()

    exe = _mailpit_exe()
    target = os.path.join(MAILPIT_DIR, exe)

    if is_zip:
        with zipfile.ZipFile(archive) as zf:
            for name in zf.namelist():
                if os.path.basename(name).lower() == exe.lower():
                    with open(target, "wb") as f:
                        f.write(zf.read(name))
                    break
    else:
        bare = exe.replace(".exe", "")
        with tarfile.open(archive) as tf:
            for member in tf.getmembers():
                if os.path.basename(member.name) == bare:
                    src = tf.extractfile(member)
                    if src:
                        with open(target, "wb") as f:
                            f.write(src.read())
                    break

    if sys.platform != "win32":
        os.chmod(target, os.stat(target).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    try:
        os.remove(archive)
    except Exception:
        pass
    return target


def _port_in_use(port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", port))
        return False
    except OSError:
        return True
    finally:
        s.close()


def ensure_mailpit():
    binary = _find_mailpit()
    if binary:
        return binary
    print("  Mailpit not found locally or in PATH.")
    try:
        return _download_mailpit()
    except Exception as e:
        print("\n  Could not download Mailpit: %s" % e)
        print("  Install manually: https://mailpit.axe.email/docs/install/")
        print("  Or download from: %s" % _mailpit_url())
        print("  Place the binary in: %s" % MAILPIT_DIR)
        sys.exit(1)


def start_mailpit(binary):
    return subprocess.Popen(
        [binary,
         "--smtp", "127.0.0.1:%d" % MAILPIT_SMTP,
         "--listen", "127.0.0.1:%d" % MAILPIT_HTTP],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


def wait_for_mailpit(timeout=15):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            req = Request(MAILPIT_API + "/messages?limit=1",
                          headers={"Accept": "application/json"})
            urlopen(req, timeout=2)
            return True
        except Exception:
            time.sleep(0.5)
    return False


# -------------------------------------------------------- Mailpit API
def _api_get(path):
    req = Request(MAILPIT_API + path, headers={"Accept": "application/json"})
    with urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode("utf-8"))


def list_messages():
    return _api_get("/messages?limit=50").get("messages", [])


def fetch_message(mid):
    return _api_get("/message/%s" % mid)


# ----------------------------------------------------------- evaluator
def check_recipient(detail):
    for addr in detail.get("To", []):
        a = (addr.get("Address") or "").lower()
        if a == "f.karim@rafidfs.local":
            return {"ok": True, "msg": "Correct target: Farah Karim, Accounts Payable."}
        if a == "y.karim@rafidfs.local":
            return {"ok": False, "msg": "Yusuf Karim is in Facilities, not Finance. Two Karims — pick the one in Accounts Payable."}
    return {"ok": False, "msg": "Wrong recipient. Who processes every vendor invoice same-day? Check the Team page."}


def check_sender(detail):
    frm = detail.get("From", {})
    addr = (frm.get("Address") or "").lower()
    dom = addr.split("@")[-1] if "@" in addr else ""
    sup_domains = {s["domain"].lower() for s in SUPPLIERS}
    if dom == "rafidfs.local":
        return {"ok": False, "msg": "Internal sender for an external invoice? Impersonate a supplier Rafid pays."}
    if dom in sup_domains:
        return {"ok": True, "msg": "Impersonating a known supplier (%s)." % dom}
    return {"ok": False, "msg": "Farah doesn’t recognise that sender. Impersonate one of Rafid’s real suppliers."}


def check_subject(detail):
    subj = (detail.get("Subject") or "").lower()
    signals = ("invoice", "remittance", "payment", "same-day", "same day",
               "overdue", "statement", "فاتورة",
               "دفع", "حوالة",
               "مستحق")
    if any(s in subj for s in signals):
        return {"ok": True, "msg": "Subject reads like a vendor invoice."}
    return {"ok": False, "msg": "Subject doesn’t look like an invoice. What does Farah process same-day?"}


def check_rlo_trick(detail):
    attachments = detail.get("Attachments") or []
    if not attachments:
        return {"ok": False, "msg": "No attachment. The phish needs a file with the filename-disguise technique from Lecture 5."}

    for att in attachments:
        fname = att.get("FileName") or ""
        if RLO not in fname:
            continue
        after = fname[fname.index(RLO) + 1:]
        if not after.lower().endswith(".exe"):
            return {"ok": False, "msg": "RLO character found, but the real extension isn’t .exe."}
        visual = after[::-1]
        if visual.lower().endswith(".pdf"):
            return {"ok": True, "msg": "RLO trick detected: real .exe disguised as .pdf."}
        return {"ok": False, "msg": "RLO found and .exe detected, but the visual result doesn’t end in .pdf. Check your reversed string."}

    return {"ok": False, "msg": "Attachment present but no RLO trick. Use the U+202E technique from Lecture 5 to disguise the extension."}


def evaluate(msg_id):
    detail = fetch_message(msg_id)
    criteria = {
        "recipient": check_recipient(detail),
        "sender":    check_sender(detail),
        "subject":   check_subject(detail),
        "rlo_trick": check_rlo_trick(detail),
    }
    frm = detail.get("From", {})
    to_list = detail.get("To", [])
    summary = {
        "from":    frm.get("Address", ""),
        "to":      to_list[0].get("Address", "") if to_list else "",
        "subject": detail.get("Subject", ""),
    }
    passed = all(c["ok"] for c in criteria.values())
    return {"criteria": criteria, "summary": summary, "passed": passed,
            "time": time.strftime("%H:%M:%S")}


def evaluator_loop():
    seen = set()
    while True:
        try:
            for m in list_messages():
                mid = m["ID"]
                if mid in seen:
                    continue
                seen.add(mid)
                result = evaluate(mid)
                with _lock:
                    _state["latest_eval"] = result
                    _maybe_solve()
        except Exception:
            pass
        time.sleep(3)


# ---------------------------------------------------------------- web UI
UI_HTML = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Iskander Capstone - Kill-Chain Lab</title>
<style>
:root{--bg:#0e1116;--card:#171c24;--line:#2a313c;--ink:#e6e9ee;--mut:#9aa4b2;--acc:#c9a227;--green:#46a05a;--red:#d16565}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.6 system-ui,Segoe UI,Roboto,sans-serif}
.wrap{max-width:760px;margin:0 auto;padding:24px 16px 60px}
h1{font-size:22px;margin:.2em 0}.sub{color:var(--mut);margin:0 0 18px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px 18px;margin:14px 0}
.card h2{font-size:16px;margin:.1em 0 .5em}
label{display:block;color:var(--mut);font-size:13px;margin:10px 0 4px}
input{width:100%;background:#0e1319;border:1px solid var(--line);color:var(--ink);border-radius:7px;padding:9px 10px;font:14px monospace}
.code-row{display:flex;gap:8px;align-items:center}
.code-row input{flex:1}
button{background:var(--acc);color:#0e1116;border:0;border-radius:7px;padding:10px 16px;font-weight:700;cursor:pointer;font-size:14px}
button.ghost{background:transparent;color:var(--acc);border:1px solid var(--acc)}
a{color:var(--acc)}
.note{color:var(--mut);font-size:13px}
.ok{color:var(--green)}.bad{color:var(--red)}
.warn{background:rgba(201,162,39,.1);border:1px solid rgba(201,162,39,.4);border-radius:8px;padding:10px 12px;font-size:13px;color:var(--mut)}
.step{color:var(--acc);font-weight:700}
.hidden{display:none}
.info-box{background:#0e1319;border:1px solid var(--line);border-radius:7px;padding:10px 12px;font:14px monospace;margin:8px 0}
.info-box div{padding:2px 0}
.info-box b{color:var(--mut);font-family:system-ui;font-size:13px}
.eval-item{display:flex;gap:8px;padding:7px 0;border-top:1px solid var(--line);align-items:baseline}
.eval-icon{font-weight:700;width:18px;text-align:center;flex-shrink:0}
.eval-label{font-weight:600;min-width:70px;flex-shrink:0}
.eval-msg{color:var(--mut);font-size:13px}
.eval-summary{font:13px monospace;color:var(--mut);margin:0 0 4px;word-break:break-all}
.flag{font:18px/1.5 monospace;font-weight:700;color:var(--acc);background:#0e1319;border:1px solid var(--line);border-radius:7px;padding:10px 12px;margin:8px 0;word-break:break-all}
.solved-card{border-color:var(--green)}
.pulse{display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--green);margin-right:6px;animation:pulse 2s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.3}}
.btns{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px}
</style></head><body><div class="wrap">
<h1>Iskander Capstone &mdash; Kill-Chain Lab</h1>
<p class="sub">Educational simulation &mdash; no real email, malware, or target. Everything runs on your machine.</p>

<div class="warn">This is an educational simulation for the Iskander Cyber Bootcamp. Real phishing or malware against real people or systems is a crime. This lab targets a fictitious company (<code>rafidfs.local</code>) and does nothing harmful.</div>

<div class="card">
  <h2><span class="step">1.</span> Your code</h2>
  <p class="note">Sign in at <a href="https://iskander.sh/capstone" target="_blank">iskander.sh/capstone</a>, press Start, and paste your personal code here.</p>
  <div class="code-row">
    <input id="code" placeholder="ISK-XXXXXXXX" autocomplete="off" spellcheck="false">
    <button id="set-code" type="button">Set</button>
  </div>
  <div id="code-msg" class="note" style="margin-top:6px"></div>
</div>

<div class="card">
  <h2><span class="step">2.</span> Reconnaissance</h2>
  <p class="note">Investigate the target company. Work out who processes invoices, which supplier to impersonate, and what subject gets processed same-day.</p>
  <div class="btns"><a href="/recon/" target="_blank"><button class="ghost" type="button">Open Rafid Financial Services</button></a></div>
</div>

<div class="card">
  <h2><span class="step">3.</span> Send your phishing email</h2>
  <p class="note">Adapt <code>send-phish.py</code> from Lecture 5 or craft your own MIME email. Send it via SMTP to the local mail server. The attachment must use the filename-disguise technique from Lecture 5.</p>
  <div class="info-box">
    <div><b>SMTP server:</b> 127.0.0.1:""" + str(MAILPIT_SMTP) + r"""</div>
    <div><b>Target domain:</b> rafidfs.local</div>
  </div>
  <div class="btns"><a href="http://127.0.0.1:""" + str(MAILPIT_HTTP) + r"""" target="_blank"><button class="ghost" type="button">Open Mailpit &mdash; see your emails arrive</button></a></div>
</div>

<div class="card" id="eval-card">
  <h2><span class="step">4.</span> Evaluation <span class="pulse" id="eval-pulse" title="auto-refreshing"></span></h2>
  <div id="eval-wait" class="note">Waiting for incoming email&hellip; sends are detected automatically.</div>
  <div id="eval-body" class="hidden">
    <p class="eval-summary" id="eval-sum"></p>
    <div id="eval-list"></div>
  </div>
</div>

<div class="card solved-card hidden" id="flag-card">
  <h2 style="color:var(--green)">Challenge solved!</h2>
  <div class="flag" id="flag-val"></div>
  <p class="note">Submit this flag at <a href="https://iskander.sh/capstone" target="_blank">iskander.sh/capstone</a> to pass Part 1.</p>
  <p class="note">Optional: record a <b>Challenge Walkthrough</b> video for the 50% bonus (see the portal for YouTube guidelines).</p>
</div>

<script>
var $ = function(id){return document.getElementById(id)};
function esc(s){var d=document.createElement('div');d.textContent=s==null?'':s;return d.innerHTML;}

$('set-code').addEventListener('click', function(){
  var c = $('code').value.trim().toUpperCase();
  $('set-code').disabled = true;
  fetch('/code',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({code:c})})
    .then(function(r){return r.json()})
    .then(function(d){
      $('code-msg').textContent = d.ok ? 'Code set.' : (d.reason||'Error');
      $('code-msg').className = 'note ' + (d.ok?'ok':'bad');
      if(d.ok) $('code').readOnly = true;
    })
    .catch(function(){$('code-msg').textContent='Network error.';$('code-msg').className='note bad';})
    .then(function(){$('set-code').disabled=false;});
});

$('code').addEventListener('keydown', function(e){if(e.key==='Enter')$('set-code').click();});

var labels = {recipient:'Target', sender:'Sender', subject:'Subject', rlo_trick:'RLO Trick'};
var order = ['recipient','sender','subject','rlo_trick'];

function poll(){
  fetch('/status').then(function(r){return r.json()}).then(function(d){
    if(d.latest_eval){
      $('eval-wait').classList.add('hidden');
      $('eval-body').classList.remove('hidden');
      var ev = d.latest_eval;
      $('eval-sum').innerHTML = 'Latest email ('+esc(ev.time)+'): <b>'+esc(ev.summary.from)+'</b> &rarr; <b>'+esc(ev.summary.to)+'</b><br>Subject: '+esc(ev.summary.subject);
      var list = $('eval-list'); list.innerHTML='';
      order.forEach(function(key){
        var c = ev.criteria[key];
        var row = document.createElement('div'); row.className='eval-item';
        row.innerHTML = '<span class="eval-icon '+(c.ok?'ok':'bad')+'">'+(c.ok?'✓':'✗')+'</span>'
          +'<span class="eval-label">'+labels[key]+'</span>'
          +'<span class="eval-msg">'+esc(c.msg)+'</span>';
        list.appendChild(row);
      });
    }
    if(d.solved && d.flag){
      $('flag-card').classList.remove('hidden');
      $('flag-val').textContent = d.flag;
    }
    if(d.latest_eval && d.latest_eval.passed && !d.code_set){
      $('code-msg').textContent = 'All criteria passed! Enter your code above to reveal your flag.';
      $('code-msg').className = 'note ok';
    }
  }).catch(function(){});
}
poll();
setInterval(poll, 3000);
</script>
</div></body></html>"""


# ------------------------------------------------------------ HTTP handler
class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _json(self, code, obj):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except Exception:
            pass

    def _html(self, code, html):
        body = html.encode("utf-8") if isinstance(html, str) else html
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except Exception:
            pass

    def _file(self, code, data, ctype):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        try:
            self.wfile.write(data)
        except Exception:
            pass

    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/", "/index.html"):
            self._html(200, UI_HTML)
        elif path == "/status":
            with _lock:
                self._json(200, {
                    "code_set": _state["code"] is not None,
                    "solved":   _state["solved"],
                    "flag":     _state["flag"],
                    "latest_eval": _state["latest_eval"],
                })
        elif path.startswith("/recon/"):
            self._serve_recon(path[7:])
        else:
            self._html(404, "not found")

    def _serve_recon(self, rel):
        if rel == "" or rel.endswith("/"):
            rel += "index.html"
        full = os.path.normpath(os.path.join(DIST, rel))
        if not full.startswith(DIST) or not os.path.isfile(full):
            self._html(404, "not found")
            return
        ctype = mimetypes.guess_type(full)[0] or "application/octet-stream"
        with open(full, "rb") as f:
            self._file(200, f.read(), ctype)

    def do_POST(self):
        if self.path == "/code":
            try:
                length = int(self.headers.get("Content-Length", 0))
                data = json.loads(self.rfile.read(length).decode("utf-8"))
            except Exception:
                self._json(400, {"ok": False, "reason": "Bad request."})
                return
            code = (data.get("code") or "").strip().upper()
            if not CODE_RE.match(code):
                self._json(200, {"ok": False, "reason": "Invalid format. Your code looks like ISK-1A2B3C4D."})
                return
            with _lock:
                _state["code"] = code
                _maybe_solve()
            self._json(200, {"ok": True})
        else:
            self._json(404, {"ok": False, "reason": "not found"})


# ------------------------------------------------------------------- main
def build_site():
    try:
        subprocess.run([sys.executable, os.path.join(HERE, "build_recon.py")],
                       cwd=HERE, check=True, stdout=subprocess.DEVNULL)
    except Exception as e:
        print("  (Could not build the recon site: %s)" % e)


def main():
    global SUPPLIERS
    SUPPLIERS = load_json("suppliers.json")

    print("Building the recon site...")
    build_site()

    # --- Mailpit ---
    mailpit_proc = None
    if _port_in_use(MAILPIT_HTTP):
        print("  Mailpit already running on port %d." % MAILPIT_HTTP)
    else:
        binary = ensure_mailpit()
        print("  Starting Mailpit...")
        mailpit_proc = start_mailpit(binary)
        if not wait_for_mailpit():
            print("  ERROR: Mailpit did not start. Check port %d." % MAILPIT_HTTP)
            sys.exit(1)
    print("  Mailpit ready (SMTP :%d, UI :%d)." % (MAILPIT_SMTP, MAILPIT_HTTP))

    # --- evaluator ---
    threading.Thread(target=evaluator_loop, daemon=True).start()

    # --- web server ---
    if _port_in_use(WEB_PORT):
        print("\n  ERROR: Port %d already in use. Stop the other program and retry." % WEB_PORT)
        sys.exit(1)
    httpd = http.server.ThreadingHTTPServer((WEB_HOST, WEB_PORT), Handler)

    url = "http://%s:%d" % (WEB_HOST, WEB_PORT)
    mp = "http://127.0.0.1:%d" % MAILPIT_HTTP
    print("\n  Iskander Capstone Lab is running (educational simulation).")
    print("  Dashboard:   %s" % url)
    print("  Mailpit UI:  %s" % mp)
    print("  SMTP:        127.0.0.1:%d" % MAILPIT_SMTP)
    print("\n  Send your phishing email via SMTP. Press Ctrl+C to stop.\n")

    if "--no-browser" not in sys.argv:
        try:
            webbrowser.open(url)
        except Exception:
            pass
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping...")
        if mailpit_proc:
            mailpit_proc.terminate()
        print("Bye.")


if __name__ == "__main__":
    main()
