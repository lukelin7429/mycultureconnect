#!/usr/bin/env python3
"""
Build the MCC Teaching Library.

    python3 scripts/build_library.py

Reads                        Writes
    data/library.json            library/index.html              the shelf itself
    data/lesson-plans.json       library/lesson-plans/            Dom Jones's curriculum
                                 library/lesson-plans/week-NN/    one page per imported week

Edit the JSON, re-run, never hand-edit the generated HTML. The curriculum JSON
is produced by scripts/import_lesson_plans.py from Dom's PDF.

Why the catalogue links out instead of copying pages in: the same booklets were
once copied by hand onto two other MCC sites, and both copies are now older than
the originals — silently, because the audio and PDFs are absolute URLs and keep
playing. One home per collection, links from everywhere else.
"""
import html
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLANS = "/library/lesson-plans/"

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
  .lp-routine { display:flex; flex-wrap:wrap; align-items:center; gap:8px 6px; margin:18px 0 0; }
  .lp-routine b { font-family:var(--serif); font-weight:400; font-size:1.15rem; background:#fff;
    border:1px solid var(--line); border-radius:30px; padding:8px 18px; }
  .lp-routine i { color:var(--orange); font-style:normal; font-size:1.2rem; }
  .lp-blocks { display:grid; grid-template-columns:repeat(5,1fr); gap:10px; margin-top:22px; }
  .lp-blocks div { background:#fff; border:1px solid var(--line); border-radius:12px; padding:14px 16px; }
  .lp-blocks small { display:block; font-family:var(--eyebrow); letter-spacing:.1em;
    text-transform:uppercase; font-size:.68rem; color:var(--orange-dark); }
  .lp-blocks b { font-family:var(--serif); font-weight:400; font-size:1rem; }
  .ugroup { margin-bottom:46px; }
  .ugroup h2 { font-size:1.45rem; margin:0 0 .2em; }
  .ugroup .u-sub { color:var(--muted-2); font-size:.94rem; margin-bottom:16px; }
  .wgrid { display:grid; grid-template-columns:repeat(3,1fr); gap:16px; }
  .wcard { display:flex; flex-direction:column; gap:4px; background:#fff; border:1px solid var(--line);
    border-radius:14px; padding:18px 20px; text-decoration:none; color:var(--ink); min-height:104px;
    transition:transform .24s cubic-bezier(.2,.7,.2,1), box-shadow .24s ease, border-color .24s ease; }
  .wcard .wn { font-family:var(--eyebrow); text-transform:uppercase; letter-spacing:.12em;
    font-size:.7rem; color:var(--orange); }
  .wcard b { font-family:var(--serif); font-weight:400; font-size:1.06rem; line-height:1.25; }
  .wcard .wgo { margin-top:auto; padding-top:8px; font-family:var(--eyebrow); font-weight:700;
    font-size:.86rem; color:var(--orange-dark); }
  .wcard.live:hover { transform:translateY(-5px); border-color:var(--orange);
    box-shadow:0 18px 38px -14px rgba(245,130,32,.45); text-decoration:none; }
  .wcard.soon { background:transparent; border-style:dashed; border-color:#e2e2e2; cursor:default; }
  .wcard.soon .wn { color:var(--muted-2); }
  .wcard.soon b { color:var(--muted); }
  .wcard.soon .wsoon { margin-top:auto; padding-top:8px; color:#b4b4b4; font-size:.82rem; }
  @media(max-width:980px) { .lp-blocks { grid-template-columns:repeat(3,1fr); } }
  @media(max-width:700px) { .wgrid { grid-template-columns:1fr; } .lp-blocks { grid-template-columns:1fr 1fr; }
    .lp-notice { flex-direction:column; gap:8px; } }
  @media (prefers-reduced-motion:reduce) { .wcard { transition:none; } .wcard.live:hover { transform:none; } }
'''

BLOCK_ZH = {"Homework review": "複習作業", "Vocabulary": "單字", "New learning": "新教學",
            "Fun / application": "應用活動", "Challenge / exit ticket": "挑戰與出場券"}


def week_href(n):
    return f"{PLANS}week-{n:02d}/"


def plans_page(d):
    nl = "\n"
    a = d["author"]
    weeks = d.get("weeks", [])
    units = d.get("units", [])
    ready = sum(1 for w in weeks if w.get("blocks"))
    total = d.get("total_weeks", 46)

    def cell(w):
        n = w["n"]
        if w.get("blocks"):
            return f'''      <a class="wcard live" href="{week_href(n)}" data-reveal>
        <span class="wn">Week {n} · 第 {n} 週</span>
        <b>{e(w["title"])}</b>
        <span class="wgo">Open the lesson →</span>
      </a>'''
        title = f'<b>{e(w["title"])}</b>' if w.get("title") else ""
        return f'''      <div class="wcard soon" data-reveal>
        <span class="wn">Week {n} · 第 {n} 週</span>
        {title}
        <span class="wsoon">Full plan coming · 完整教案整理中</span>
      </div>'''

    if units:
        groups = []
        for u in units:
            mine = [w for w in weeks if w.get("unit") == u["n"]]
            if not mine:
                continue
            span = f'Weeks {mine[0]["n"]}–{mine[-1]["n"]} · {len(mine)} weeks'
            groups.append(f'''    <section class="ugroup" id="unit-{u["n"]}">
      <h2>Unit {u["n"]} · {e(u["title"])}</h2>
      <div class="u-sub">{span}</div>
      <div class="wgrid">
{nl.join(cell(w) for w in mine)}
      </div>
    </section>''')
        grid = nl.join(groups)
    else:
        by_n = {w["n"]: w for w in weeks}
        grid = f'''    <div class="wgrid">
{nl.join(cell(by_n.get(n, {"n": n})) for n in range(1, total + 1))}
    </div>'''

    notice = ""
    if d.get("status") != "complete":
        notice = f'''    <div class="lp-notice" data-reveal>
      <div>
        <b>Status · 上架進度</b>
        <p>{e(d["status_note_en"])} <b style="display:inline;font-family:var(--body);text-transform:none;letter-spacing:0;font-size:1rem;color:var(--ink)">{ready} of {total} live.</b></p>
        <p class="zh">{e(d["status_note_zh"])}</p>
      </div>
    </div>'''

    routine = ""
    if d.get("principle"):
        steps = ' <i>→</i> '.join(f'<b>{e(s)}</b>' for s in d["principle"])
        blocks = nl.join(
            f'      <div><small>{e(t)}</small><b>{e(l)}</b><br><span style="font-size:.86rem;color:var(--muted-2)">{e(BLOCK_ZH[l])}</span></div>'
            for t, l in [("0–10 min", "Homework review"), ("10–20 min", "Vocabulary"),
                         ("20–35 min", "New learning"), ("35–50 min", "Fun / application"),
                         ("50–57 min", "Challenge / exit ticket")])
        routine = f'''<section style="background:var(--bg-soft)">
  <div class="wrap">
    <div class="section-head left" style="margin-bottom:10px" data-reveal>
      <p class="eyebrow">How every week runs · 每週的固定流程</p>
      <h2>Same routine, {e(d.get("duration", "60 minutes"))}</h2>
      <p>{e(d["principle_note_en"])}<br><span style="font-size:.95rem;color:var(--muted-2)">{e(d["principle_note_zh"])}</span></p>
    </div>
    <div class="lp-routine" data-reveal>{steps}</div>
    <div class="lp-blocks" data-reveal>
{blocks}
    </div>
  </div>
</section>
'''

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

{routine}
<section>
  <div class="wrap">
{notice}
{grid}
    <p class="muted" style="margin-top:34px;max-width:64ch">{e(d["note_en"])}</p>
    <p class="muted" style="margin-top:6px;max-width:64ch;font-size:.94rem">{e(d["note_zh"])}</p>
  </div>
</section>

{FOOT}'''


# ------------------------------------------------------------- one week
WEEK_CSS = '''  .wk-meta { display:flex; flex-wrap:wrap; gap:8px; margin-top:18px; }
  .wk-meta span { background:#fff; border:1px solid var(--line); border-radius:30px; padding:6px 14px;
    font-size:.84rem; color:var(--muted); }
  .wk-two { display:grid; grid-template-columns:1fr 1fr; gap:22px; }
  .wk-card { background:#fff; border:1px solid var(--line); border-radius:16px; padding:24px 26px;
    box-shadow:0 4px 14px rgba(20,20,20,.05); }
  .wk-label { font-family:var(--eyebrow); text-transform:uppercase; letter-spacing:.12em;
    font-size:.72rem; color:var(--orange-dark); margin:0 0 10px; }
  .wk-label small { text-transform:none; letter-spacing:0; color:var(--muted-2); font-size:.8rem; margin-left:6px; }
  .wk-card p { margin:0; color:var(--ink); line-height:1.7; }
  .wk-chips { display:flex; flex-wrap:wrap; gap:8px; margin:0; padding:0; list-style:none; }
  .wk-chips li { background:#fff8f0; border:1px solid #ffe0c2; border-radius:30px; padding:7px 15px;
    font-family:var(--serif); font-size:1.05rem; }
  .wk-callout { background:#fff8f0; border:1px solid #ffe0c2; border-left:4px solid var(--orange);
    border-radius:14px; padding:20px 24px; margin-top:22px; }
  .wk-callout p { margin:0; color:var(--ink); line-height:1.7; }
  .wk-tl { list-style:none; padding:0; margin:0; position:relative; }
  .wk-tl::before { content:""; position:absolute; left:112px; top:8px; bottom:8px; width:2px;
    background:linear-gradient(180deg,var(--orange),#ffd6b0); }
  .wk-tl li { display:grid; grid-template-columns:96px 1fr; gap:34px; padding:18px 0; position:relative; }
  .wk-tl li::before { content:""; position:absolute; left:106px; top:26px; width:14px; height:14px;
    border-radius:50%; background:#fff; border:3px solid var(--orange); box-shadow:0 0 0 4px #fff; }
  .wk-tl .t { font-family:var(--eyebrow); letter-spacing:.06em; font-size:.9rem; color:var(--orange-dark);
    text-align:right; padding-top:3px; white-space:nowrap; }
  .wk-tl b { display:block; font-family:var(--serif); font-weight:400; font-size:1.25rem; margin-bottom:4px; }
  .wk-tl b small { font-family:var(--body); font-size:.9rem; color:var(--muted-2); margin-left:8px; }
  .wk-tl p { margin:0; color:var(--muted); line-height:1.7; }
  .wk-cefr { display:grid; grid-template-columns:repeat(5,1fr); gap:12px; }
  .wk-cefr div { background:#fff; border:1px solid var(--line); border-radius:12px; padding:16px 16px; }
  .wk-cefr b { display:block; font-family:var(--eyebrow); letter-spacing:.08em; color:var(--orange-dark); margin-bottom:6px; }
  .wk-cefr p { margin:0; font-size:.94rem; color:var(--muted); line-height:1.6; }
  .wk-nav { display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-top:44px; }
  .wk-nav a, .wk-nav span { display:block; border:1px solid var(--line); border-radius:14px; padding:18px 22px;
    text-decoration:none; color:var(--ink); background:#fff; transition:transform .2s, box-shadow .2s, border-color .2s; }
  .wk-nav a:hover { transform:translateY(-3px); border-color:var(--orange); box-shadow:var(--shadow); text-decoration:none; }
  .wk-nav small { display:block; font-family:var(--eyebrow); text-transform:uppercase; letter-spacing:.12em;
    font-size:.68rem; color:var(--muted-2); margin-bottom:4px; }
  .wk-nav .next { text-align:right; }
  .wk-nav span { color:var(--muted-2); border-style:dashed; }
  .wk-principle { margin-top:40px; padding-top:22px; border-top:1px solid var(--line); color:var(--muted-2);
    font-size:.92rem; }
  @media(max-width:880px) { .wk-two, .wk-nav { grid-template-columns:1fr; } .wk-cefr { grid-template-columns:repeat(2,1fr); }
    .wk-tl::before { left:14px; } .wk-tl li { grid-template-columns:1fr; gap:6px; padding-left:40px; }
    .wk-tl li::before { left:8px; top:22px; } .wk-tl .t { text-align:left; } }
  @media(max-width:520px) { .wk-cefr { grid-template-columns:1fr; } }
  @media (prefers-reduced-motion:reduce) { .wk-nav a { transition:none; } .wk-nav a:hover { transform:none; } }
'''

LEVEL_RE = re.compile(r"\b(A1|A2|B1|B2\+?|C1/C2|C1|C2)\s*:\s*")


def cefr_html(text):
    parts = LEVEL_RE.split(text)
    if len(parts) < 5:
        return f'<div class="wk-card"><p>{e(text)}</p></div>'
    pairs = list(zip(parts[1::2], parts[2::2]))
    cols = "".join(f'<div><b>{e(l)}</b><p>{e(t.strip().rstrip("."))}.</p></div>' for l, t in pairs)
    return f'<div class="wk-cefr">{cols}</div>'


def week_page(d, w, prev_w, next_w):
    nl = "\n"
    a = d["author"]
    unit = next((u for u in d.get("units", []) if u["n"] == w.get("unit")), None)
    unit_label = f'Unit {unit["n"]} · {unit["title"]}' if unit else ""
    total = d.get("total_weeks", 46)
    n = w["n"]

    chips = "".join(f"<li>{e(v)}</li>" for v in w.get("vocabulary", []))
    timeline = nl.join(
        f'''      <li data-reveal>
        <span class="t">{e(b["time"])}</span>
        <div><b>{e(b["label"])}<small>{e(BLOCK_ZH.get(b["label"], ""))}</small></b><p>{e(b["text"])}</p></div>
      </li>''' for b in w["blocks"])

    def nav_link(x, cls, label):
        if not x:
            return ""
        if x.get("blocks"):
            return f'<a class="{cls}" href="{week_href(x["n"])}"><small>{label}</small>Week {x["n"]} · {e(x["title"])}</a>'
        return f'<span class="{cls}"><small>{label}</small>Week {x["n"]} · {e(x.get("title", ""))} — coming</span>'

    nav = f'''    <div class="wk-nav">
      {nav_link(prev_w, "prev", "← Previous week") or "<div></div>"}
      {nav_link(next_w, "next", "Next week →") or "<div></div>"}
    </div>'''

    principle = ""
    if d.get("principle"):
        principle = f'''    <p class="wk-principle">Teacher principle: {e(" → ".join(d["principle"]))}. {e(d["principle_note_en"])}</p>'''

    return f'''{head(f"Week {n} · {w['title']}",
                     f"Week {n} of {total} in Dom Jones's English curriculum: {w['language_target']}",
                     WEEK_CSS)}
<section class="page-hero">
  <div class="wrap">
    <a class="backlink" href="{PLANS}">← {e(d["title_en"])}</a>
    <p class="eyebrow">{e(unit_label)}</p>
    <h1>Week {n} · {e(w["title"])}</h1>
    <p class="lead">{e(w["language_target"])}</p>
    <div class="wk-meta">
      <span>Week {n} of {total}</span>
      <span>{e(d.get("duration", "60 minutes"))}</span>
      <span>by <a href="{e(a["href"])}">{e(a["name"])}</a></span>
    </div>
  </div>
</section>

<section>
  <div class="wrap">
    <div class="wk-two">
      <div class="wk-card" data-reveal>
        <p class="wk-label">Language target<small>語言目標</small></p>
        <p>{e(w["language_target"])}</p>
      </div>
      <div class="wk-card" data-reveal>
        <p class="wk-label">Power vocabulary<small>核心字彙 · {len(w.get("vocabulary", []))} words</small></p>
        <ul class="wk-chips">{chips}</ul>
      </div>
    </div>
    <div class="wk-callout" data-reveal>
      <p class="wk-label">Seasonal / Taiwan connection<small>季節與台灣連結</small></p>
      <p>{e(w["taiwan_connection"])}</p>
    </div>
  </div>
</section>

<section style="background:var(--bg-soft)">
  <div class="wrap">
    <div class="section-head left" style="margin-bottom:18px" data-reveal>
      <p class="eyebrow">The lesson, minute by minute · 課堂流程</p>
      <h2>{e(d.get("duration", "60 minutes"))}, five moves</h2>
    </div>
    <ul class="wk-tl">
{timeline}
    </ul>
  </div>
</section>

<section>
  <div class="wrap">
    <div class="wk-two">
      <div class="wk-card" data-reveal>
        <p class="wk-label">Optional video / media plug-in<small>影片與媒體（選用）</small></p>
        <p>{e(w["media"])}</p>
      </div>
      <div class="wk-card" data-reveal>
        <p class="wk-label">Homework<small>回家作業 · due next week</small></p>
        <p>{e(w["homework"])}</p>
      </div>
    </div>
  </div>
</section>

<section style="background:var(--bg-soft)">
  <div class="wrap">
    <div class="section-head left" style="margin-bottom:18px" data-reveal>
      <p class="eyebrow">CEFR differentiation · 依程度分級</p>
      <h2>Same lesson, different output</h2>
      <p>One plan for a mixed class: what each level is asked to produce.<br>
        <span style="font-size:.95rem;color:var(--muted-2)">同一份教案帶混合程度的班：各級學生被要求產出的東西。</span></p>
    </div>
    <div data-reveal>{cefr_html(w["cefr"])}</div>
  </div>
</section>

<section>
  <div class="wrap">
    <div class="wk-card" data-reveal>
      <p class="wk-label">Next-week routine<small>下週例行</small></p>
      <p>{e(w["next_week"])}</p>
    </div>
{nav}
{principle}
  </div>
</section>

{FOOT}'''


def main():
    lib = json.load(open(os.path.join(ROOT, "data", "library.json"), encoding="utf-8"))
    plans = json.load(open(os.path.join(ROOT, "data", "lesson-plans.json"), encoding="utf-8"))

    n = sum(len(g["cards"]) for g in lib["groups"])
    print(f"  {'✓' if write('/library/', library_page(lib)) else '·'} /library/  "
          f"({n} collections in {len(lib['groups'])} groups)")

    weeks = sorted(plans.get("weeks", []), key=lambda w: w["n"])
    by_n = {w["n"]: w for w in weeks}
    live = [w for w in weeks if w.get("blocks")]
    print(f"  {'✓' if write(PLANS, plans_page(plans)) else '·'} {PLANS}  "
          f"({len(live)}/{plans.get('total_weeks', 46)} weeks live)")
    for w in live:
        changed = write(week_href(w["n"]), week_page(plans, w, by_n.get(w["n"] - 1), by_n.get(w["n"] + 1)))
        print(f"  {'✓' if changed else '·'} {week_href(w['n'])}  {w['title']}")
    print("  → re-run scripts/build_search.py to index new pages")


if __name__ == "__main__":
    main()
