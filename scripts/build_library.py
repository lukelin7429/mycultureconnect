#!/usr/bin/env python3
"""
Build the MCC Teaching Library.

    python3 scripts/build_library.py

Reads                        Writes
    data/library.json            library/index.html          the shelf itself
    data/lesson-plans.json       library/lesson-plans/        Dom Jones's curriculum

Edit the JSON, re-run, never hand-edit the generated HTML.

Why the catalogue links out instead of copying pages in: the same booklets were
once copied by hand onto two other MCC sites, and both copies are now older than
the originals — silently, because the audio and PDFs are absolute URLs and keep
playing. One home per collection, links from everywhere else.
"""
import html
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The site has no shared layout — every page carries its own copy of the nav.
# Keep this list in step with the other pages when the menu changes.
NAV = [("/index.html", "Home"), ("/team.html", "Team"), ("/partners.html", "Partners"),
       ("/opportunities.html", "Opportunities"), ("/school-tour.html", "School Tour"),
       ("/library/", "Library"), ("/contact.html", "Contact")]


def e(s):
    return html.escape(str(s))


def write(rel, content):
    path = os.path.join(ROOT, rel.strip("/"), "index.html")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            if f.read() == content:
                return False
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return True


def head(title, desc, extra_css=""):
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)} — My Culture Connect</title>
<meta name="description" content="{e(desc)}">
<link rel="icon" type="image/png" href="/assets/img/favicon.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noticia+Text:wght@400;700&family=Questrial&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/assets/css/style.css">
<style>
{extra_css}</style>
<link rel="stylesheet" href="/assets/css/search.css">
</head>
<body>
<header class="site-header"><div class="wrap">
  <a class="brand" href="/index.html">
    <img src="/assets/img/logo.png" alt="My Culture Connect logo">
    <span><b>My Culture Connect</b><span>Renshi · 人師教育協會</span></span>
  </a>
  <button class="nav-toggle" aria-label="Menu" aria-expanded="false"><span></span><span></span><span></span></button>
  <nav class="main">
{chr(10).join(f'    <a href="{h}"{" class=" + chr(34) + "active" + chr(34) if h == "/library/" else ""}>{l}</a>' for h, l in NAV)}
  </nav>
</div></header>
'''


FOOT = '''<footer class="site-footer"><div class="wrap">
  <div class="cb-credit">
    © <span id="yr"></span> My Culture Connect · 人師教育協會. All rights reserved.<br>
    No. 136, Sec. 1, Wenyuan Rd., Beidou Township, Changhua County 521, Taiwan (R.O.C.)
  </div>
</div></footer>
<script src="/assets/js/main.js"></script>
<script defer src="/assets/js/search.js"></script>
</body>
</html>'''


# --------------------------------------------------------------- the shelf
LIBRARY_CSS = '''  .lib-stats { display:grid; grid-template-columns:repeat(4,1fr); gap:26px; text-align:center; }
  .lib-stats .stat p { font-size:.82rem; }
  .lib-stats .stat small { display:block; margin-top:4px; font-size:.86rem;
    letter-spacing:0; text-transform:none; color:#fff; opacity:.82; font-family:var(--body); }
  .lib-jump { display:flex; flex-wrap:wrap; gap:10px; list-style:none; padding:0;
    margin:0 0 4px; justify-content:center; }
  .lib-jump a { display:inline-block; background:#fff; border:1px solid var(--line);
    border-radius:30px; padding:9px 18px; font-family:var(--eyebrow); font-size:.92rem;
    color:var(--muted); text-decoration:none; transition:border-color .2s, color .2s, transform .2s; }
  .lib-jump a:hover { border-color:var(--orange); color:var(--orange-dark);
    transform:translateY(-2px); text-decoration:none; }
  .lgroup { margin-bottom:66px; scroll-margin-top:90px; }
  .lgroup:last-child { margin-bottom:0; }
  .lg-head { max-width:760px; margin-bottom:28px; }
  .lg-head h2 { font-size:1.9rem; margin:0 0 .15em; }
  .lg-head .lg-zh { font-family:var(--body); font-size:1.1rem; color:var(--muted-2); }
  .lg-head p { color:var(--muted); margin:14px 0 0; line-height:1.7; }
  .lg-head p.zh { color:var(--muted-2); font-size:.96rem; margin-top:6px; }
  .lgrid { display:grid; grid-template-columns:repeat(3,1fr); gap:24px; }
  .lib-card { position:relative; display:flex; flex-direction:column; background:#fff;
    border:1px solid #e7e7e7; border-radius:16px; padding:26px 26px 22px; overflow:hidden;
    text-decoration:none; color:var(--ink);
    box-shadow:inset 4px 0 0 0 var(--accent,#F58220), 0 4px 14px rgba(20,20,20,.06);
    transition:transform .28s cubic-bezier(.2,.7,.2,1), box-shadow .28s ease, border-color .28s ease; }
  .lib-card:nth-child(6n+1) { --accent:#b8431c; }
  .lib-card:nth-child(6n+2) { --accent:#0c8599; }
  .lib-card:nth-child(6n+3) { --accent:#7048e8; }
  .lib-card:nth-child(6n+4) { --accent:#2f9e44; }
  .lib-card:nth-child(6n+5) { --accent:#d6336c; }
  .lib-card:nth-child(6n+6) { --accent:#e8590c; }
  .lib-card:hover { transform:translateY(-8px); border-color:var(--accent); text-decoration:none;
    box-shadow:inset 4px 0 0 0 var(--accent,#F58220), 0 26px 52px -18px var(--accent,rgba(245,130,32,.4)); }
  .lc-head { display:flex; align-items:center; justify-content:space-between; gap:10px; margin-bottom:10px; }
  .lc-kind { font-family:var(--eyebrow); text-transform:uppercase; letter-spacing:.12em;
    font-size:.7rem; color:var(--accent,var(--orange)); }
  .lc-badge { background:var(--orange); color:#fff; border-radius:30px; padding:4px 12px;
    font-family:var(--eyebrow); text-transform:uppercase; letter-spacing:.1em; font-size:.66rem; }
  .lc-en { font-family:var(--serif); font-weight:400; font-size:1.34rem; line-height:1.2; }
  .lc-zh { font-size:1rem; color:var(--muted-2); margin-top:3px; }
  .lc-desc { color:var(--muted); font-size:.98rem; line-height:1.65; margin-top:12px; }
  .lc-desc-zh { color:var(--muted-2); font-size:.9rem; margin-top:6px; }
  .lc-tags { display:flex; flex-wrap:wrap; gap:7px; margin:16px 0 0; }
  .lc-tag { background:var(--bg-soft); border:1px solid var(--line); border-radius:30px;
    padding:4px 12px; font-size:.78rem; color:var(--muted-2); }
  .lc-go { margin-top:18px; font-family:var(--eyebrow); letter-spacing:.04em; font-weight:700;
    font-size:.94rem; color:var(--orange-dark); }
  .lib-card:hover .lc-go { color:var(--orange); }
  .lib-card.feature { grid-column:1 / -1; }
  .lib-card.feature .lc-en { font-size:2rem; }
  .lib-card.feature .lc-zh { font-size:1.12rem; }
  .lib-card.feature .lc-desc { font-size:1.06rem; max-width:70ch; }
  @media(max-width:980px) { .lgrid { grid-template-columns:repeat(2,1fr); }
    .lib-stats { grid-template-columns:repeat(2,1fr); gap:34px; } }
  @media(max-width:700px) { .lgrid { grid-template-columns:1fr; }
    .lib-stats { grid-template-columns:1fr; } .lg-head h2 { font-size:1.6rem; } }
  @media (prefers-reduced-motion:reduce) {
    .lib-card, .lib-jump a { transition:none; }
    .lib-card:hover, .lib-jump a:hover { transform:none; }
  }
'''


def card(c):
    """One catalogue entry. Cross-domain entries open in a new tab — they are
    just as much ours, but a teacher mid-browse should not lose the shelf."""
    external = c["href"].startswith("http")
    attrs = ' target="_blank" rel="noopener"' if external else ""
    badge = f'<span class="lc-badge">{e(c["badge"])}</span>' if c.get("badge") else ""
    tags = "".join(f'<span class="lc-tag">{e(t)}</span>' for t in c.get("tags", []))
    cls = "lib-card feature" if c.get("feature") else "lib-card"
    return f'''<a class="{cls}" href="{e(c["href"])}"{attrs} data-reveal>
        <span class="lc-head"><span class="lc-kind">{e(c["kind"])}</span>{badge}</span>
        <b class="lc-en">{e(c["en"])}</b>
        <span class="lc-zh">{e(c["zh"])}</span>
        <span class="lc-desc">{e(c["desc_en"])}</span>
        <span class="lc-desc lc-desc-zh">{e(c["desc_zh"])}</span>
        <span class="lc-tags">{tags}</span>
        <span class="lc-go">Open {"↗" if external else "→"}</span>
      </a>'''


def library_page(d):
    nl = "\n"
    stats = nl.join(
        f'''      <div class="stat" data-reveal>
        <div class="big" data-count="{s["num"]}" data-suffix="{e(s["suffix"])}">{s["num"]:,}{e(s["suffix"])}</div>
        <p>{e(s["label"])}<small>{e(s["label_zh"])}</small></p>
      </div>''' for s in d["stats"])

    principles = nl.join(
        f'''      <div class="card" data-reveal>
        <h3>{e(p["en"])}<br><span style="font-size:1rem;color:var(--muted-2)">{e(p["zh"])}</span></h3>
        <p>{e(p["desc_en"])}</p>
        <p style="margin-top:10px;font-size:.92rem;color:var(--muted-2)">{e(p["desc_zh"])}</p>
      </div>''' for p in d["principles"])

    jump = nl.join(
        f'      <li><a href="#{e(g["id"])}">{e(g["title_en"])}</a></li>' for g in d["groups"])

    groups = nl.join(f'''    <section class="lgroup" id="{e(g["id"])}">
      <div class="lg-head" data-reveal>
        <h2>{e(g["title_en"])}</h2>
        <div class="lg-zh">{e(g["title_zh"])}</div>
        <p>{e(g["blurb_en"])}</p>
        <p class="zh">{e(g["blurb_zh"])}</p>
      </div>
      <div class="lgrid">
{nl.join(card(c) for c in g["cards"])}
      </div>
    </section>''' for g in d["groups"])

    h = d["hero"]
    total = sum(len(g["cards"]) for g in d["groups"])
    return f'''{head("MCC Teaching Library",
                     "Every English teaching material My Culture Connect has made — graded readers with human audio, thousands of classroom videos, slide decks and lesson plans. Free to use, free to adapt.",
                     LIBRARY_CSS)}
<section class="page-hero">
  <div class="wrap">
    <p class="eyebrow">{e(h["eyebrow"])}</p>
    <h1>{e(h["h1"])}</h1>
    <p class="lead">{e(h["lead_en"])}</p>
    <p class="lead" style="color:var(--muted-2);font-size:1rem">{e(h["lead_zh"])}</p>
  </div>
</section>

<section class="band">
  <div class="orbs"><span class="orb a"></span><span class="orb b"></span><span class="orb c"></span></div>
  <div class="wrap">
    <div class="lib-stats">
{stats}
    </div>
  </div>
</section>

<section>
  <div class="wrap">
    <div class="section-head" data-reveal>
      <p class="eyebrow">How to use this library</p>
      <h2>Yours to take, yours to change</h2>
      <p>教材庫怎麼用</p>
    </div>
    <div class="grid cols-3">
{principles}
    </div>
  </div>
</section>

<section style="background:var(--bg-soft);padding-top:54px;padding-bottom:54px">
  <div class="wrap">
    <div class="section-head" style="margin-bottom:26px" data-reveal>
      <p class="eyebrow">The shelves · 書架</p>
      <h2>{total} collections</h2>
    </div>
    <ul class="lib-jump" data-reveal>
{jump}
    </ul>
  </div>
</section>

<section>
  <div class="wrap">
{groups}
  </div>
</section>

<section class="band">
  <div class="orbs"><span class="orb a"></span><span class="orb b"></span><span class="orb c"></span></div>
  <div class="wrap">
    <div class="section-head" data-reveal>
      <p class="eyebrow">Something missing?</p>
      <h2>Tell us what your class needs</h2>
      <p style="color:#fff;opacity:.94">We have been making English materials for rural Changhua since 2002, and we
        keep making them. If there is a topic your students need and we do not have it, write to us.<br>
        <span style="font-size:.95rem;opacity:.9">如果有你班上需要、而我們還沒做的主題，歡迎告訴我們。</span></p>
      <p style="margin-top:22px"><a class="btn ghost" style="border-color:#fff;color:#fff" href="/contact.html">Contact us · 聯絡我們</a></p>
    </div>
  </div>
</section>

{FOOT}'''


# ---------------------------------------------------- Dom's 46-week curriculum
PLANS_CSS = '''  .lp-author { display:flex; align-items:center; gap:18px; margin:26px 0 0; }
  .lp-author img { width:74px; height:74px; border-radius:50%; object-fit:cover;
    object-position:center top; border:3px solid #fff; box-shadow:var(--shadow); }
  .lp-author b { font-family:var(--serif); font-weight:400; font-size:1.2rem; display:block; }
  .lp-author span { color:var(--muted-2); font-size:.94rem; }
  .lp-notice { display:flex; gap:16px; align-items:flex-start; background:#fff8f0;
    border:1px solid #ffe0c2; border-left:4px solid var(--orange); border-radius:14px;
    padding:20px 24px; margin-bottom:38px; }
  .lp-notice b { font-family:var(--eyebrow); text-transform:uppercase; letter-spacing:.1em;
    font-size:.74rem; color:var(--orange-dark); display:block; margin-bottom:6px; }
  .lp-notice p { margin:0; color:var(--muted); line-height:1.65; }
  .lp-notice p.zh { color:var(--muted-2); font-size:.92rem; margin-top:4px; }
  .wgrid { display:grid; grid-template-columns:repeat(4,1fr); gap:16px; }
  .wcard { display:flex; flex-direction:column; gap:4px; background:#fff; border:1px solid var(--line);
    border-radius:14px; padding:18px 20px; text-decoration:none; color:var(--ink); min-height:104px;
    transition:transform .24s cubic-bezier(.2,.7,.2,1), box-shadow .24s ease, border-color .24s ease; }
  .wcard .wn { font-family:var(--eyebrow); text-transform:uppercase; letter-spacing:.12em;
    font-size:.7rem; color:var(--orange); }
  .wcard b { font-family:var(--serif); font-weight:400; font-size:1.06rem; line-height:1.25; }
  .wcard .wzh { font-size:.9rem; color:var(--muted-2); }
  .wcard.live:hover { transform:translateY(-5px); border-color:var(--orange);
    box-shadow:0 18px 38px -14px rgba(245,130,32,.45); text-decoration:none; }
  .wcard.soon { background:transparent; border-style:dashed; border-color:#e2e2e2; cursor:default; }
  .wcard.soon .wn { color:var(--muted-2); }
  .wcard.soon .wsoon { color:#b4b4b4; font-size:.86rem; }
  @media(max-width:980px) { .wgrid { grid-template-columns:repeat(3,1fr); } }
  @media(max-width:700px) { .wgrid { grid-template-columns:repeat(2,1fr); } .lp-notice { flex-direction:column; gap:8px; } }
  @media (prefers-reduced-motion:reduce) { .wcard { transition:none; } .wcard.live:hover { transform:none; } }
'''


def plans_page(d):
    nl = "\n"
    a = d["author"]
    by_n = {w["n"]: w for w in d.get("weeks", [])}
    cells = []
    for n in range(1, d.get("total_weeks", 46) + 1):
        w = by_n.get(n)
        if w:
            cells.append(f'''      <a class="wcard live" href="{e(w["href"])}" data-reveal>
        <span class="wn">Week {n} · 第 {n} 週</span>
        <b>{e(w["title_en"])}</b>
        <span class="wzh">{e(w.get("title_zh", ""))}</span>
      </a>''')
        else:
            cells.append(f'''      <div class="wcard soon" data-reveal>
        <span class="wn">Week {n} · 第 {n} 週</span>
        <span class="wsoon">Coming · 準備中</span>
      </div>''')
    ready = len(by_n)

    notice = ""
    if d.get("status") == "preparing":
        notice = f'''    <div class="lp-notice" data-reveal>
      <div>
        <b>Status · 上架進度</b>
        <p>{e(d["status_note_en"])} <b style="display:inline;font-family:var(--body);text-transform:none;letter-spacing:0;font-size:1rem;color:var(--ink)">{ready} of {d.get("total_weeks", 46)} ready.</b></p>
        <p class="zh">{e(d["status_note_zh"])}</p>
      </div>
    </div>'''

    return f'''{head(d["title_en"],
                     f'{d["title_en"]} by Dom Jones — a full academic year of English lesson plans, free for any teacher to use or adapt.',
                     PLANS_CSS)}
<section class="page-hero">
  <div class="wrap">
    <a class="backlink" href="/library/">← MCC Teaching Library</a>
    <p class="eyebrow">{e(d["eyebrow"])}</p>
    <h1>{e(d["title_en"])}</h1>
    <p class="lead">{e(d["lead_en"])}</p>
    <p class="lead" style="color:var(--muted-2);font-size:1rem">{e(d["lead_zh"])}</p>
    <div class="lp-author">
      <img src="{e(a["photo"])}" alt="{e(a["name"])}">
      <div>
        <b>{e(d["title_zh"])}</b>
        <span>by <a href="{e(a["href"])}">{e(a["name"])}</a> · {e(a["role_en"])}</span>
      </div>
    </div>
  </div>
</section>

<section>
  <div class="wrap">
{notice}
    <div class="wgrid">
{nl.join(cells)}
    </div>
    <p class="muted" style="margin-top:34px;max-width:64ch">{e(d["note_en"])}</p>
    <p class="muted" style="margin-top:6px;max-width:64ch;font-size:.94rem">{e(d["note_zh"])}</p>
  </div>
</section>

{FOOT}'''


def main():
    lib = json.load(open(os.path.join(ROOT, "data", "library.json"), encoding="utf-8"))
    plans = json.load(open(os.path.join(ROOT, "data", "lesson-plans.json"), encoding="utf-8"))

    n = sum(len(g["cards"]) for g in lib["groups"])
    print(f"  {'✓' if write('/library/', library_page(lib)) else '·'} /library/  "
          f"({n} collections in {len(lib['groups'])} groups)")
    ready = len(plans.get("weeks", []))
    print(f"  {'✓' if write('/library/lesson-plans/', plans_page(plans)) else '·'} /library/lesson-plans/  "
          f"({ready}/{plans.get('total_weeks', 46)} weeks live)")
    print("  → re-run scripts/build_search.py to index the new pages")


if __name__ == "__main__":
    main()
