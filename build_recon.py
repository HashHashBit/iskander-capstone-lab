#!/usr/bin/env python3
"""
build_recon.py — render the fictitious-company recon site, static, no dependencies.

Reads recon/data/*.json and writes a full static site into recon/dist/. Astro is
deliberately NOT used: node_modules is zeroed on this repo's Drive mount, and the
site never needs client JS. Matches the main site's pure-Python house style.

The recon site is the ONLY thing students see before choosing a pretext. It carries
the layered breadcrumbs from 03-web-app-spec.md §3 so a careful reader walks the
path in 30-45 minutes and a careless one fails the phish.

Per-student vs shared:
    python build_recon.py                      # shared/preview build (placeholder flag)
    python build_recon.py --nn 07 --flag ISK{...}
        # student 07's build: the target's onboarding PDF carries the real stage-1
        # flag in its Creator metadata, and the workstation hostname comment reads
        # WKSTN-FIN07. This is what rangectl/enroll calls per student.

Stage-1 flag lives in the PDF's Creator field (found with `exiftool`, not with eyes).
The PDF is written by hand (valid 1.4, correct xref) so no reportlab is needed here.
"""

import argparse, html, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
OUT = os.path.join(HERE, "dist")


def load(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        return json.load(f)


CO = load("company.json")
EMP = load("employees.json")
SUP = load("suppliers.json")
NEWS = load("news.json")
JOBS = load("careers.json")
BY_ID = {e["id"]: e for e in EMP}
E = html.escape


# ---------------------------------------------------------------- avatars ----
def avatar_svg(emp):
    """Deterministic initials-on-colour SVG. License-clean, offline, consistent."""
    initials = "".join(p[0] for p in emp["name"].split()[:2]).upper()
    h = sum(ord(c) for c in emp["id"]) % 360
    bg = f"hsl({h},32%,42%)"
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 96 96" role="img" '
        f'aria-label="{E(emp["name"])}"><rect width="96" height="96" rx="8" fill="{bg}"/>'
        f'<text x="48" y="58" font-family="Segoe UI,Arial,sans-serif" font-size="38" '
        f'font-weight="600" fill="#fff" text-anchor="middle">{initials}</text></svg>'
    )


# ------------------------------------------------------------------ layout ----
def page(title, body, rel="", desc=""):
    b = CO["brand"]
    nav = "".join(
        f'<a href="{rel}{href}">{E(label)}</a>'
        for href, label in [
            ("index.html", "Home"), ("about.html", "About"), ("team.html", "Team"),
            ("careers.html", "Careers"), ("news.html", "News"),
            ("suppliers.html", "Suppliers"), ("contact.html", "Contact"),
        ]
    )
    return f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{E(title)} — {E(CO['name'])}</title>
<meta name="description" content="{E(desc or CO['tagline'])}">
<style>
  :root{{--p:{b['primary']};--a:{b['accent']};--ink:{b['ink']};--paper:{b['paper']}}}
  *{{box-sizing:border-box}}
  body{{margin:0;background:var(--paper);color:var(--ink);
    font:16px/1.6 Georgia,'Times New Roman',serif}}
  a{{color:var(--p)}}
  header.top{{background:var(--p);color:#fff}}
  .bar{{max-width:960px;margin:0 auto;padding:14px 20px;display:flex;flex-wrap:wrap;
    align-items:center;gap:16px}}
  .logo{{font-weight:700;font-size:20px;color:#fff;text-decoration:none;letter-spacing:.02em}}
  .logo b{{color:var(--a)}}
  nav{{margin-left:auto;display:flex;flex-wrap:wrap;gap:16px;font-family:Segoe UI,Arial,sans-serif;font-size:14px}}
  nav a{{color:#e7efe9;text-decoration:none}}
  nav a:hover{{color:#fff;text-decoration:underline}}
  main{{max-width:960px;margin:0 auto;padding:28px 20px 56px}}
  h1{{font-size:30px;margin:.2em 0 .4em;color:var(--p)}}
  h2{{font-size:22px;color:var(--p);border-bottom:2px solid var(--a);padding-bottom:4px;
    display:inline-block;margin-top:1.4em}}
  .hero{{background:#fff;border:1px solid #e3e0d6;border-radius:8px;padding:28px}}
  .tag{{font-size:20px;color:#555;font-style:italic}}
  .grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:16px;margin-top:18px}}
  .card{{background:#fff;border:1px solid #e3e0d6;border-radius:8px;padding:16px;text-decoration:none;color:inherit;display:block}}
  .card:hover{{border-color:var(--a)}}
  .card .av{{width:56px;height:56px;float:left;margin-right:12px}}
  .card .nm{{font-weight:700;color:var(--p)}}
  .card .tt{{font-size:14px;color:#555;font-family:Segoe UI,Arial,sans-serif}}
  .muted{{color:#666;font-family:Segoe UI,Arial,sans-serif;font-size:14px}}
  table{{border-collapse:collapse;width:100%;margin-top:12px;font-family:Segoe UI,Arial,sans-serif;font-size:14px}}
  td,th{{border:1px solid #e3e0d6;padding:8px 10px;text-align:left}}
  th{{background:#eef2ef}}
  .profile{{display:flex;gap:20px;align-items:flex-start;background:#fff;border:1px solid #e3e0d6;border-radius:8px;padding:20px}}
  .profile .av{{width:96px;height:96px;flex:0 0 auto}}
  .doc{{font-family:Segoe UI,Arial,sans-serif;font-size:14px}}
  footer{{background:#0f2e2b;color:#b9c9c4;font-family:Segoe UI,Arial,sans-serif;font-size:13px}}
  footer .bar{{display:block;line-height:1.8}}
  .clear{{clear:both}}
</style></head>
<body>
<header class="top"><div class="bar">
  <a class="logo" href="{rel}index.html">Rafid <b>FS</b></a>
  <nav>{nav}</nav>
</div></header>
<main>{body}</main>
<footer><div class="bar">
  {E(CO['name'])} · Reg. {E(CO['reg_no'])} · {E(CO['hq'])}<br>
  Switchboard {E(CO['switchboard'])} · Established {CO['founded']}<br>
  <span style="color:#7d938d">© {CO['founded']}–2026 {E(CO['short'])}. Privacy policy. This site uses only essential cookies.</span>
</div></footer>
</body></html>"""


def write(path, content):
    full = os.path.join(OUT, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        f.write(content)


# ------------------------------------------------------------------ pages ----
def build_home():
    body = f"""
<div class="hero">
  <h1>{E(CO['name'])}</h1>
  <p class="tag">{E(CO['tagline'])}</p>
  <p>{E(CO['sector'])}. Serving regional SMEs since {CO['founded']} from our office in {E(CO['hq'].split(',')[-1].strip())}.</p>
  <p class="muted"><a href="about.html">About the firm</a> · <a href="team.html">Meet the team</a> · <a href="contact.html">Get in touch</a></p>
</div>
<h2>What we do</h2>
<div class="grid">
  <div class="card"><div class="nm">Accounting &amp; bookkeeping</div><div class="tt">Day-to-day ledgers, reconciliations, and month-end for SMEs.</div></div>
  <div class="card"><div class="nm">Tax</div><div class="tt">Corporate and VAT filings, plus cross-border advisory.</div></div>
  <div class="card"><div class="nm">Payroll</div><div class="tt">Monthly payroll for the firm and outsourced-payroll clients.</div></div>
  <div class="card"><div class="nm">Audit &amp; advisory</div><div class="tt">Statutory audit and internal-controls reviews.</div></div>
</div>
<h2>Latest news</h2>
<ul class="doc">
{''.join(f'<li><a href="news/{E(n["slug"])}.html">{E(n["title"])}</a> <span class="muted">— {E(n["date"])}</span></li>' for n in NEWS[:4])}
</ul>"""
    write("index.html", page("Home", body, desc=CO["tagline"]))


def build_about():
    body = f"""
<h1>About {E(CO['short'])}</h1>
<p>{E(CO['name'])} was founded in {CO['founded']} by {E(BY_ID['s.rahman']['name'])} after fifteen years
in regional audit practice. What began with two desks is now a full-service firm of {len(EMP)} people
looking after the accounting, tax, payroll, and audit needs of dozens of regional SMEs.</p>
<p>We work the way our clients do — closely, and in person. Every advisory engagement is signed off by a partner,
and every client has a named contact who knows their books.</p>
<h2>Where we are</h2>
<p class="doc">{E(CO['hq'])}<br>Switchboard: {E(CO['switchboard'])}<br>
Registration: {E(CO['reg_no'])} · Established {CO['founded']}</p>
<h2>Our departments</h2>
<table><tr><th>Department</th><th>People</th></tr>
{''.join(f'<tr><td>{E(d)}</td><td>{sum(1 for e in EMP if e["dept"]==d)}</td></tr>' for d in dict.fromkeys(e["dept"] for e in EMP))}
</table>"""
    write("about.html", page("About", body))


def build_team(nn):
    cards = ""
    for e in EMP:
        cards += (
            f'<a class="card" href="team/{E(e["id"])}.html">'
            f'<div class="av">{avatar_svg(e)}</div>'
            f'<div class="nm">{E(e["name"])}</div>'
            f'<div class="tt">{E(e["title"])}</div>'
            f'<div class="tt muted">{E(e["dept"])}</div><div class="clear"></div></a>'
        )
    # Tier-3 breadcrumb: a "contractor" comment leaking the workstation hostname.
    wkstn = f"WKSTN-FIN{nn}" if nn else "WKSTN-FIN&lt;NN&gt;"
    body = f"""
<h1>Our team</h1>
<p class="muted">{len(EMP)} people across {len(set(e['dept'] for e in EMP))} departments. Reach anyone using our
standard email format — see the <a href="contact.html">contact page</a>.</p>
<!-- TODO(contractor): staff photos still pulled from the old intranet host {wkstn}; migrate before launch -->
<div class="grid">{cards}</div>"""
    write("team.html", page("Team", body))
    for e in EMP:
        mgr = BY_ID.get(e["manager"]) if e["manager"] else None
        mgr_html = (f'<a href="{E(mgr["id"])}.html">{E(mgr["name"])}</a> ({E(mgr["title"])})'
                    if mgr else "—")
        extra = ""
        if e.get("target"):
            extra = ('<p class="muted">Farah handles all supplier billing questions and processes '
                     'vendor invoices same-day — see her <a href="../news/same-day-invoice-processing.html">'
                     'note on Accounts Payable</a>.</p>')
        prof = f"""
<div class="profile">
  <div class="av">{avatar_svg(e)}</div>
  <div>
    <h1 style="margin-top:0">{E(e['name'])}</h1>
    <p class="tt" style="font-size:16px;color:#555">{E(e['title'])} · {E(e['dept'])}</p>
    <p>{E(e['bio'])}</p>
    <table class="doc">
      <tr><th>Email</th><td>{E(e['email'])}</td></tr>
      <tr><th>Extension</th><td>{E(CO['switchboard'])} ext {E(e['ext'])}</td></tr>
      <tr><th>Reports to</th><td>{mgr_html}</td></tr>
      <tr><th>With Rafid FS since</th><td>{E(e['joined'])}</td></tr>
    </table>
    {extra}
  </div>
</div>
<p style="margin-top:16px"><a href="../team.html">&larr; Back to the team</a></p>"""
        write(f"team/{e['id']}.html", page(e["name"], prof, rel="../"))


def build_careers():
    rows = "".join(
        f'<tr><td><a href="careers/{E(j["slug"])}.html">{E(j["title"])}</a></td>'
        f'<td>{E(j["dept"])}</td><td class="muted">{E(j["date"])}</td></tr>' for j in JOBS
    )
    body = f"""
<h1>Careers at {E(CO['short'])}</h1>
<p>We hire for attitude and train for tools — but a head start on the software we use always helps.
Applications and questions go to our HR coordinator, {E(BY_ID['o.rashid']['name'])}
(<a href="team/o.rashid.html">{E(BY_ID['o.rashid']['email'])}</a>).</p>
<table><tr><th>Role</th><th>Department</th><th>Posted</th></tr>{rows}</table>"""
    write("careers.html", page("Careers", body))
    for j in JOBS:
        c = BY_ID.get(j["contact"])
        paras = "".join(f"<p>{E(p)}</p>" for p in j["body"])
        body = f"""
<h1>{E(j['title'])}</h1>
<p class="tt muted">{E(j['dept'])} · posted {E(j['date'])}</p>
{paras}
<p class="doc">To apply, contact {E(c['name'])} at <a href="../team/{E(c['id'])}.html">{E(c['email'])}</a>.</p>
<p><a href="../careers.html">&larr; All openings</a></p>"""
        write(f"careers/{j['slug']}.html", page(j["title"], body, rel="../"))


def build_news():
    rows = "".join(
        f'<li><a href="news/{E(n["slug"])}.html">{E(n["title"])}</a> '
        f'<span class="muted">— {E(BY_ID[n["author"]]["name"])}, {E(n["date"])}</span></li>'
        for n in NEWS
    )
    write("news.html", page("News", f'<h1>News &amp; updates</h1><ul class="doc">{rows}</ul>'))
    for n in NEWS:
        a = BY_ID[n["author"]]
        paras = "".join(f"<p>{E(p)}</p>" for p in n["body"])
        body = f"""
<h1>{E(n['title'])}</h1>
<p class="tt muted">By <a href="../team/{E(a['id'])}.html">{E(a['name'])}</a>, {E(a['title'])} · {E(n['date'])}</p>
{paras}
<p><a href="../news.html">&larr; All news</a></p>"""
        write(f"news/{n['slug']}.html", page(n["title"], body, rel="../"))


def build_contact():
    body = f"""
<h1>Contact us</h1>
<p class="doc">{E(CO['hq'])}<br>Switchboard: {E(CO['switchboard'])}</p>
<h2>Email us</h2>
<p>You can reach any member of our team directly. Our email format is
<strong>{E(CO['email_convention'])}</strong> — first initial, dot, last name, at {E(CO['domain'])}.</p>
<p>For supplier billing and invoices, contact our Accounts Payable specialist,
{E(BY_ID['f.karim']['name'])}, at <a href="team/f.karim.html">{E(BY_ID['f.karim']['email'])}</a>.</p>
<p class="muted">General enquiries: {E(BY_ID['j.nasser']['email'])}</p>"""
    write("contact.html", page("Contact", body))


def build_suppliers():
    rows = "".join(
        f'<tr><td>{E(s["name"])}</td><td>{E(s["category"])}</td>'
        f'<td>{E(s["account_manager"])}</td><td class="muted">{E(s["domain"])}</td></tr>' for s in SUP
    )
    body = f"""
<h1>Our suppliers &amp; partners</h1>
<p>Rafid FS works with a small, trusted set of vendors. Suppliers with billing questions
should contact our Accounts Payable team directly (see <a href="contact.html">contact</a>).</p>
<table><tr><th>Supplier</th><th>Category</th><th>Account manager</th><th>Domain</th></tr>{rows}</table>"""
    write("suppliers.html", page("Suppliers", body))


# ----------------------------------------------------- downloadable PDF ----
def minimal_pdf(title, author, creator):
    """Hand-rolled valid PDF 1.4 with an Info dict. `creator` carries the stage-1
    flag; `exiftool`/`pdfinfo` read it. No reportlab needed."""
    def esc(s): return s.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")
    objs = []
    objs.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objs.append(b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
    objs.append(b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
                b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>")
    text = (f"BT /F1 16 Tf 60 780 Td ({esc(title)}) Tj "
            f"0 -28 Td /F1 11 Tf ({esc(author)} — vendor onboarding form) Tj ET").encode("latin-1", "replace")
    objs.append(b"<< /Length " + str(len(text)).encode() + b" >>\nstream\n" + text + b"\nendstream")
    objs.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    info = (f"<< /Title ({esc(title)}) /Author ({esc(author)}) "
            f"/Creator ({esc(creator)}) /Producer (Rafid FS DocGen) >>").encode("latin-1", "replace")
    objs.append(info)

    out = b"%PDF-1.4\n"
    offsets = []
    for i, o in enumerate(objs, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + o + b"\nendobj\n"
    xref_pos = len(out)
    n = len(objs) + 1
    out += f"xref\n0 {n}\n".encode() + b"0000000000 65535 f \n"
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += (f"trailer\n<< /Size {n} /Root 1 0 R /Info {len(objs)} 0 R >>\n"
            f"startxref\n{xref_pos}\n%%EOF").encode()
    return out


def build_docs(nn, flag):
    target = BY_ID[CO["target"]]
    creator = flag if flag else "ISK{stage1-per-student-flag}"
    pdf = minimal_pdf("Vendor Onboarding 2026 - Rafid Financial Services",
                      target["name"], creator)
    write_bytes("docs/vendor-onboarding-2026.pdf", pdf)
    # A second, decoy doc with no flag (Author = a non-target) to reward verification.
    write_bytes("docs/expense-policy-2026.pdf",
                minimal_pdf("Expense Policy 2026", BY_ID["n.fawzi"]["name"], "Rafid FS"))
    # /archive is directory-listable and disallowed in robots — an old org chart PDF.
    write_bytes("archive/org-chart-2022.pdf",
                minimal_pdf("Rafid FS Organisation Chart 2022", BY_ID["s.rahman"]["name"], "Rafid FS"))
    listing = "".join(f'<li><a href="{f}">{f}</a></li>' for f in ["org-chart-2022.pdf"])
    write("archive/index.html",
          "<!doctype html><meta charset=utf-8><title>Index of /archive</title>"
          f"<h1>Index of /archive</h1><ul>{listing}</ul>")
    write("robots.txt", "User-agent: *\nDisallow: /archive/\n")


def write_bytes(path, data):
    full = os.path.join(OUT, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "wb") as f:
        f.write(data)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--nn", default="", help="two-digit student number (per-student build)")
    ap.add_argument("--flag", default="", help="stage-1 flag ISK{...} to stamp into the target PDF")
    args = ap.parse_args()

    if os.path.isdir(OUT):
        for root, _, files in os.walk(OUT, topdown=False):
            for f in files:
                os.remove(os.path.join(root, f))
    build_home(); build_about(); build_team(args.nn); build_careers()
    build_news(); build_contact(); build_suppliers(); build_docs(args.nn, args.flag)
    n = sum(len(files) for _, _, files in os.walk(OUT))
    tag = f"student {args.nn}" if args.nn else "shared/preview"
    print(f"recon site built into recon/dist/ ({n} files, {tag})")
    if not args.flag:
        print("  note: no --flag given, target PDF carries a placeholder Creator")


if __name__ == "__main__":
    main()
