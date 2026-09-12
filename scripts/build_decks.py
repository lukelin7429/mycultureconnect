#!/usr/bin/env python3
"""
Build Dom Jones slide decks for mycultureconnect.org.

    python3 scripts/build_decks.py

Reads one JSON per deck from data/decks/ and writes:

    slides/index.html                 bilingual library (English first)
    slides/<slug>/index.html          the deck itself — no site chrome
    slides/<slug>/notes/index.html    Dom's English run sheet (phone / print)
    slides/<slug>/qr.svg              Padlet QR, generated locally

Deck pages carry no site navigation on purpose: you open one to project it in
a classroom. The run sheet is English-only — it is written for Dom.
"""
import html
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DECK_DIR = os.path.join(ROOT, "data", "decks")
OUT_DIR = os.path.join(ROOT, "slides")
LIB = "/slides/"


def load_decks():
    if not os.path.isdir(DECK_DIR):
        return []
    out = []
    for fn in sorted(os.listdir(DECK_DIR)):
        if fn.endswith(".json"):
            with open(os.path.join(DECK_DIR, fn), encoding="utf-8") as f:
                out.append(json.load(f))
    return out


def write(rel, content):
    path = os.path.join(ROOT, rel.strip("/"), "index.html")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


def e(s):
    return html.escape(str(s))


def bi(en, zh, cls=""):
    c = f" {cls}" if cls else ""
    return f'<div class="hs-bi{c}"><span class="hs-en">{en}</span><span class="hs-zh">{zh}</span></div>'


# ---------------------------------------------------------------- slide types
def t_title(s, d):
    chips = "".join(bi(e(c["en"]), e(c["zh"]), "hs-chip") for c in s.get("chips", []))
    strip = "".join(
        f'<div class="hs-stat"><b>{e(x["num"])}</b>'
        f'<span class="hs-en">{e(x["en"])}</span><span class="hs-zh">{e(x["zh"])}</span></div>'
        for x in s.get("strip", []))
    return f'''<div class="hs hs-title">
  <div class="hs-titlerow">
    <div class="hs-badge"><span>SDG</span><b>{e(d["sdg"])}</b></div>
    <div class="hs-titletext"><h2>{e(d["title_en"])}</h2><p class="hs-zh-big">{e(d["title"])}</p></div>
  </div>
  <div class="hs-rule"></div>
  {bi(e(s["eyebrow_en"]), e(s["eyebrow_zh"]), "hs-eyebrow")}
  <div class="hs-chips">{chips}</div>
  <div class="hs-strip">{strip}</div>
  <div class="hs-school">{e(d["school_en"])} {e(d["school"])} · {e(d["date"])}</div>
</div>'''


def t_intro(s, d):
    lines = "".join(bi(e(x["en"]), e(x["zh"]), "hs-line") for x in s["lines"])
    return f'''<div class="hs hs-intro">
  <h3 class="hs-head">{e(s["head_en"])}<span>{e(s["head_zh"])}</span></h3>
  <div class="hs-lines">{lines}</div>
  <div class="hs-ask">🙋 {bi(e(s["ask_en"]), e(s["ask_zh"]))}</div>
</div>'''


def t_video(s, d):
    return f'''<div class="hs hs-video">
  <h3 class="hs-head">{e(s["head_en"])}<span>{e(s["head_zh"])}</span></h3>
  <div class="hs-yt" data-yt="{e(s["yt"])}">
    <img src="https://i.ytimg.com/vi/{e(s["yt"])}/hqdefault.jpg" alt="">
    <button type="button" class="hs-play" aria-label="Play animation">▶</button>
  </div>
  <div class="hs-note">{bi(e(s["note_en"]), e(s["note_zh"]))}</div>
</div>'''


def t_standup(s, d):
    items = "".join(f'<li>{bi(e(x["en"]), e(x["zh"]))}</li>' for x in s["prompts"])
    return f'''<div class="hs hs-standup">
  <h3 class="hs-head">🙋 {e(s["head_en"])}<span>{e(s["head_zh"])}</span></h3>
  <ol class="hs-prompts">{items}</ol>
  <div class="hs-punch">{bi(e(s["punch_en"]), e(s["punch_zh"]))}</div>
</div>'''


def t_topic(s, d):
    kws = "".join(f'<span class="hs-kw"><b>{e(k["en"])}</b>{e(k["zh"])}</span>'
                  for k in s.get("keywords", []))
    return f'''<div class="hs hs-topic">
  <h3 class="hs-head">{e(s["head_en"])}<span>{e(s["head_zh"])}</span></h3>
  <p class="hs-body-en">{e(s["body_en"])}</p>
  <p class="hs-body-zh">{e(s["body_zh"])}</p>
  <div class="hs-kws">{kws}</div>
</div>'''


def t_quiz(s, d):
    letters = "ABCD"
    opts = "".join(
        f'<button type="button" class="hs-opt{" is-right" if i == s["answer"] else ""}">'
        f'<span class="hs-letter">{letters[i]}</span>'
        f'<span class="hs-en">{e(o["en"])}</span><span class="hs-zh">{e(o["zh"])}</span></button>'
        for i, o in enumerate(s["options"]))
    bonus = '<span class="hs-bonus">BONUS 加碼</span>' if s.get("bonus") else ""
    return f'''<div class="hs hs-quiz" data-reveal-group>
  <div class="hs-qbar"><span class="hs-qtag">🎮 Game Time! 遊戲時間</span>{bonus}
    <span class="hs-qn">Q{s["n"]}</span></div>
  <div class="hs-q">{bi(e(s["q_en"]), e(s["q_zh"]))}</div>
  <div class="hs-opts">{opts}</div>
  <div class="hs-explain">✅ {bi(e(s["explain_en"]), e(s["explain_zh"]))}</div>
  <div class="hs-tap">👆 Tap any option to reveal · 點任一選項公布答案</div>
</div>'''


def t_bigstat(s, d):
    return f'''<div class="hs hs-bigstat">
  <div class="hs-bignum">{e(s["num"])}</div>
  <h3 class="hs-bighead">{e(s["head_en"])}</h3>
  <p class="hs-bighead-zh">{e(s["head_zh"])}</p>
  <div class="hs-rule"></div>
  <div class="hs-lines">{bi(e(s["body_en"]), e(s["body_zh"]), "hs-line")}</div>
  <div class="hs-ask">❓ {bi(e(s["ask_en"]), e(s["ask_zh"]))}</div>
</div>'''


def t_truefalse(s, d):
    items = "".join(
        f'<button type="button" class="hs-tf">'
        f'<span class="hs-tfq">{bi(e(x["en"]), e(x["zh"]))}</span>'
        f'<span class="hs-tfa">{"⭕ TRUE" if x["answer"] else "❌ FALSE"}'
        f'<em>{e(x["note_en"])}<br>{e(x["note_zh"])}</em></span></button>'
        for x in s["items"])
    return f'''<div class="hs hs-tflist">
  <h3 class="hs-head">{e(s["head_en"])}<span>{e(s["head_zh"])}</span></h3>
  <div class="hs-tfs">{items}</div>
  <div class="hs-tap">👆 Tap each one to reveal · 點每一題公布答案</div>
</div>'''


def t_game(s, d):
    hints = "".join(f'<span class="hs-hint">{e(h)}</span>' for h in s.get("hints", []))
    bonus = '<span class="hs-bonus">BONUS 加碼</span>' if s.get("bonus") else ""
    return f'''<div class="hs hs-game">
  <h3 class="hs-head">{e(s.get("icon", "🎯"))} {e(s["head_en"])}<span>{e(s["head_zh"])}</span></h3>{bonus}
  <div class="hs-rule-box">{bi(e(s["rule_en"]), e(s["rule_zh"]))}</div>
  <div class="hs-hints">{hints}</div>
  <div class="hs-target">{bi(e(s["target_en"]), e(s["target_zh"]))}</div>
</div>'''


def t_pairshare(s, d):
    return f'''<div class="hs hs-pair">
  <h3 class="hs-head">👥 {e(s["head_en"])}<span>{e(s["head_zh"])}</span></h3>
  <div class="hs-prompt">{bi(e(s["prompt_en"]), e(s["prompt_zh"]))}</div>
  <div class="hs-sentence"><b>{e(s["sentence_en"])}</b><span>{e(s["sentence_zh"])}</span></div>
  <div class="hs-time">⏱ {bi(e(s["time_en"]), e(s["time_zh"]))}</div>
</div>'''


def t_rank(s, d):
    items = "".join(f'<div class="hs-rankitem"><b>{i+1}</b>{bi(e(x["en"]), e(x["zh"]))}</div>'
                    for i, x in enumerate(s["items"]))
    return f'''<div class="hs hs-rank" data-reveal-group>
  <h3 class="hs-head">✋ {e(s["head_en"])}<span>{e(s["head_zh"])}</span></h3>
  <div class="hs-sub">{bi(e(s["sub_en"]), e(s["sub_zh"]))}</div>
  <div class="hs-ranks">{items}</div>
  <button type="button" class="hs-revealbtn">Reveal 公布</button>
  <div class="hs-explain">{bi(e(s["reveal_en"]), e(s["reveal_zh"]))}</div>
</div>'''


def t_action(s, d):
    items = "".join(f'<div class="hs-act"><b>{e(x["num"])}</b>{bi(e(x["en"]), e(x["zh"]))}</div>'
                    for x in s["items"])
    return f'''<div class="hs hs-action">
  <h3 class="hs-head">{e(s["head_en"])}<span>{e(s["head_zh"])}</span></h3>
  <div class="hs-acts">{items}</div>
</div>'''


def t_phrases(s, d):
    items = "".join(f'<div class="hs-phrase"><b>{e(x["en"])}</b><span>{e(x["zh"])}</span></div>'
                    for x in s["items"])
    return f'''<div class="hs hs-phrases">
  <h3 class="hs-head">🗣 {e(s["head_en"])}<span>{e(s["head_zh"])}</span></h3>
  <div class="hs-phraselist">{items}</div>
</div>'''


def t_padlet(s, d):
    return f'''<div class="hs hs-padlet">
  <h3 class="hs-head">📱 {e(s["head_en"])}<span>{e(s["head_zh"])}</span></h3>
  <div class="hs-padletrow">
    <img class="hs-qr" src="qr.svg" alt="Padlet QR code">
    <div>
      <div class="hs-prompt">{bi(e(s["body_en"]), e(s["body_zh"]))}</div>
      <div class="hs-sentence"><b>{e(s["sentence_en"])}</b><span>{e(s["sentence_zh"])}</span></div>
    </div>
  </div>
</div>'''


def t_closing(s, d):
    return f'''<div class="hs hs-closing">
  <div class="hs-bigline">{s["big_en"]}</div>
  <div class="hs-bigline-zh">{e(s["big_zh"])}</div>
  <div class="hs-rule"></div>
  <div class="hs-sign">{e(s["sign_en"])}<span>{e(s["sign_zh"])}</span></div>
</div>'''


RENDER = {
    "title": t_title, "intro": t_intro, "video": t_video, "standup": t_standup,
    "topic": t_topic, "quiz": t_quiz, "bigstat": t_bigstat, "truefalse": t_truefalse,
    "game": t_game, "pairshare": t_pairshare, "rank": t_rank, "action": t_action,
    "phrases": t_phrases, "padlet": t_padlet, "closing": t_closing,
}


# -------------------------------------------------------------------- the QR
def write_qr(slug, url):
    try:
        import qrcode
        import qrcode.image.svg
    except ImportError:
        print("  ! qrcode not installed — skipping QR (pip install qrcode)")
        return
    out = os.path.join(OUT_DIR, slug, "qr.svg")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    qrcode.make(url, image_factory=qrcode.image.svg.SvgPathImage,
                box_size=10, border=2).save(out)


# ----------------------------------------------------------------- the pages
def deck_page(d):
    slides = []
    for s in d["slides"]:
        fn = RENDER.get(s["type"])
        if not fn:
            sys.exit(f"unknown slide type {s['type']!r} in {d['slug']}")
        slides.append(
            f'<div class="deck-slide"><div class="hs-canvas" data-theme="{d.get("theme","amber")}">'
            f'{fn(s, d)}<div class="hs-foot">{e(d["footer"])}</div></div></div>')
    n = len(slides)
    nl = "\n"
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(d["title_en"])} · {e(d["school_en"])} — My Culture Connect</title>
<meta name="description" content="Dom Jones bilingual assembly deck for {e(d["school_en"])} ({e(d["date"])}).">
<link rel="icon" type="image/png" href="/assets/img/favicon.png">
<link rel="stylesheet" href="/assets/css/deck.css">
</head>
<body class="deck-body">
<div class="deck">
  <div class="deck-top">
    <a class="deck-back" href="{LIB}">← Slide Library</a>
    <div class="deck-heading"><h1>{e(d["title_en"])}</h1>
      <div class="sub">{e(d["school_en"])} {e(d["school"])} · {e(d["date"])}</div></div>
    <a class="deck-notes-link" href="notes/">📋 Teaching notes</a>
    <div class="deck-pos-wrap"><b class="deck-pos">1</b> / {n}</div>
  </div>
  <div class="deck-stage">
    <div class="deck-track">
{nl.join(slides)}
    </div>
    <button class="deck-arrow prev" aria-label="Previous">&lsaquo;</button>
    <button class="deck-arrow next" aria-label="Next">&rsaquo;</button>
  </div>
  <div class="deck-progress"><div class="bar"></div></div>
  <p class="deck-hint">Swipe or use ← → to change slides · tap a question to reveal the answer</p>
</div>
<script src="/assets/js/deck.js"></script>
</body>
</html>'''


def notes_page(d):
    """Dom's run sheet. English only — it is written for her."""
    rows = []
    running = 0.0
    for i, s in enumerate(d["slides"], 1):
        t = float(s.get("t", 0))
        running += 0 if s.get("bonus") else t
        tag = '<span class="bonus">BONUS · skip if short</span>' if s.get("bonus") else ""
        mark = "—" if s.get("bonus") else f"{running:.0f} min"
        rows.append(f'''<tr{' class="is-bonus"' if s.get("bonus") else ''}>
  <td class="n">{i}</td>
  <td class="t">{t:g} min<span class="run">{mark}</span></td>
  <td><b>{e(slide_label(s, d))}</b>{tag}<p>{e(s.get("say",""))}</p></td>
</tr>''')
    p = d.get("pacing", {})
    nl = "\n"
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Teaching notes · {e(d["title_en"])} — {e(d["school_en"])}</title>
<meta name="robots" content="noindex">
<link rel="icon" type="image/png" href="/assets/img/favicon.png">
<style>
  :root {{ --ink:#1b2321; --muted:#5d6b67; --key:#e2620f; --line:#e6e2d8; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; padding:26px 18px 70px; background:#fbf9f4; color:var(--ink);
    font:16px/1.6 -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Helvetica Neue', Arial, sans-serif; }}
  .wrap {{ max-width:760px; margin:0 auto; }}
  a.back {{ color:var(--key); font-weight:700; text-decoration:none; font-size:.92rem; }}
  h1 {{ font-size:1.6rem; margin:.5em 0 .1em; line-height:1.2; }}
  .sub {{ color:var(--muted); margin-bottom:1.2em; }}
  .box {{ background:#fff; border:1px solid var(--line); border-left:5px solid var(--key);
    border-radius:12px; padding:16px 20px; margin-bottom:1.6em; }}
  .box b {{ display:block; margin-bottom:.3em; }}
  table {{ width:100%; border-collapse:collapse; }}
  td {{ vertical-align:top; border-top:1px solid var(--line); padding:14px 6px; }}
  td.n {{ width:34px; color:var(--muted); font-weight:700; }}
  td.t {{ width:96px; color:var(--key); font-weight:700; white-space:nowrap; }}
  td.t .run {{ display:block; color:var(--muted); font-weight:400; font-size:.82rem; }}
  td p {{ margin:.35em 0 0; color:var(--muted); }}
  tr.is-bonus {{ background:#fdf6ec; }}
  .bonus {{ display:inline-block; margin-left:8px; background:var(--key); color:#fff;
    border-radius:999px; padding:2px 10px; font-size:.7rem; font-weight:700; vertical-align:2px; }}
  @media print {{ body {{ background:#fff; padding:0; }} a.back {{ display:none; }} }}
</style>
</head>
<body>
<div class="wrap">
  <a class="back" href="../">← Back to the slides</a>
  <h1>Teaching notes</h1>
  <div class="sub">{e(d["title_en"])} · {e(d["school_en"])} {e(d["school"])} ·
    {e(d["date"])} · classes {e(d.get("classes",""))}</div>

  <div class="box">
    <b>Pacing — you have {p.get("period_min",45)} minutes</b>
    The core lesson is about {p.get("core_min","?")} minutes and the bonus slides add
    another {p.get("bonus_min","?")}. That is deliberately more than one period: if you
    finish the core early, go to the BONUS slides rather than filling time. The slowest
    slides on purpose are the True/False round and the two games — stretch those.
  </div>

  <div class="box">
    <b>How the slides work</b>
    Quiz slides: take a show-of-hands vote first, then tap any option and the correct
    answer lights up with an explanation. True/False: tap each row separately. The
    animation on slide 3 plays when you click the thumbnail. Nothing is timed — you
    control every reveal.
  </div>

  <table>
{nl.join(rows)}
  </table>
</div>
</body>
</html>'''


def slide_label(s, d):
    t = s["type"]
    if t == "quiz":
        return f'Q{s["n"]}: {s["q_en"]}'
    for k in ("head_en", "big_en", "eyebrow_en"):
        if k in s:
            return s[k].replace("<br>", " ")
    return t


def library_page(decks):
    def card(d):
        return f'''<a class="dcard" href="{LIB}{d["slug"]}/">
  <span class="dc-cover" data-theme="{d.get("theme","amber")}">
    <span class="dc-sdg">SDG {e(d["sdg"])}</span>
    <span class="dc-en">{e(d["title_en"])}</span>
    <span class="dc-zh">{e(d["title"])}</span>
  </span>
  <span class="dc-body">
    <b>{e(d["title_en"])}</b>
    <span class="dc-sub">{e(d["school_en"])} {e(d["school"])} · {e(d["date"])}</span>
    <span class="dc-cnt">{len(d["slides"])} slides · interactive →</span>
  </span>
</a>'''

    by_year = {}
    for d in decks:
        by_year.setdefault(str(d.get("year", "—")), []).append(d)
    groups = []
    for y in sorted(by_year, reverse=True):
        label = {"115": "2026–2027 · 115 學年度"}.get(y, y)
        groups.append(f'''<section class="dgroup">
  <h2>{label}</h2>
  <div class="dgrid">{"".join(card(d) for d in by_year[y])}</div>
</section>''')

    nl = "\n"
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Slide Library — Dom Jones School Tour · My Culture Connect</title>
<meta name="description" content="The bilingual slide decks Dom Jones presents at each school assembly in Changhua County.">
<link rel="icon" type="image/png" href="/assets/img/favicon.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noticia+Text:wght@400;700&family=Questrial&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/assets/css/style.css">
<style>
  .dgroup {{ margin-bottom:56px; }}
  .dgroup h2 {{ font-size:1.5rem; margin-bottom:22px; }}
  .dgrid {{ display:grid; grid-template-columns:repeat(3,1fr); gap:26px; }}
  .dcard {{ display:flex; flex-direction:column; background:#fff; border:1px solid #e7e7e7;
    border-radius:16px; overflow:hidden; text-decoration:none; color:var(--ink);
    box-shadow:0 8px 26px rgba(20,20,20,.07); transition:transform .28s, box-shadow .28s; }}
  .dcard:hover {{ transform:translateY(-6px); box-shadow:0 24px 50px rgba(245,130,32,.18);
    text-decoration:none; }}
  .dc-cover {{ aspect-ratio:16/9; display:flex; flex-direction:column; justify-content:center;
    gap:6px; padding:22px 24px; background:var(--c-bg); }}
  .dc-cover[data-theme="amber"]  {{ --c-bg:#fdf4e3; --c-key:#e2620f; --c-key2:#b8480a; --c-ink:#3a2a12; }}
  .dc-cover[data-theme="teal"]   {{ --c-bg:#093a4a; --c-key:#16a394; --c-key2:#8fd8d0; --c-ink:#eaf6f8; }}
  .dc-cover[data-theme="violet"] {{ --c-bg:#f5f0fb; --c-key:#7a3fc4; --c-key2:#5b2a9b; --c-ink:#2c1a48; }}
  .dc-sdg {{ align-self:flex-start; background:var(--c-key); color:#fff; border-radius:999px;
    padding:5px 15px; font-size:.78rem; font-weight:800; font-family:var(--eyebrow); }}
  .dc-en {{ font-family:var(--serif); font-size:1.55rem; color:var(--c-key2); line-height:1.1; }}
  .dc-zh {{ font-size:.98rem; color:var(--c-ink); opacity:.8; }}
  .dc-body {{ padding:22px 24px; display:flex; flex-direction:column; gap:5px; }}
  .dc-body b {{ font-family:var(--serif); font-weight:400; font-size:1.2rem; }}
  .dc-sub {{ color:var(--muted-2); font-size:.94rem; }}
  .dc-cnt {{ margin-top:8px; font-family:var(--eyebrow); color:var(--orange-dark);
    font-weight:700; font-size:.92rem; }}
  .archive {{ background:var(--bg-soft); border:1px solid var(--line); border-radius:16px;
    padding:26px 30px; }}
  .archive h3 {{ margin:0 0 .4em; }}
  @media(max-width:880px) {{ .dgrid {{ grid-template-columns:1fr; }} }}
</style>
</head>
<body>
<header class="site-header"><div class="wrap">
  <a class="brand" href="/index.html">
    <img src="/assets/img/logo.png" alt="My Culture Connect logo">
    <span><b>My Culture Connect</b><span>Renshi · 人師教育協會</span></span>
  </a>
  <button class="nav-toggle" aria-label="Menu" aria-expanded="false"><span></span><span></span><span></span></button>
  <nav class="main">
    <a href="/index.html">Home</a>
    <a href="/team.html">Team</a>
    <a href="/partners.html">Partners</a>
    <a href="/opportunities.html">Opportunities</a>
    <a href="/school-tour.html" class="active">School Tour</a>
    <a href="/contact.html">Contact</a>
  </nav>
</div></header>

<section class="page-hero">
  <div class="wrap">
    <a class="backlink" href="/dom-school-tour.html">← Dom Jones School Tour</a>
    <p class="eyebrow">Slide Library · 簡報庫</p>
    <h1>The decks Dom presents, slide by slide</h1>
    <p class="lead">Every bilingual deck Dom Jones uses in a Changhua classroom — swipe through
      on any device. Questions reveal their answers when you tap them.</p>
    <p class="lead bi-en" style="color:var(--muted-2);font-size:1rem">
      Dom 在彰化每一場集會實際使用的雙語簡報，手機電腦都能左右滑動瀏覽，題目點一下就公布答案。</p>
  </div>
</section>

<section>
  <div class="wrap">
{nl.join(groups)}

    <div class="archive">
      <h3>2025–2026 · 114 學年度</h3>
      <p class="muted">The first 21 school decks from Dom's Spring 2026 tour are still on the
        Chinese site while we move them across.<br>
        <span style="font-family:var(--body)">114 學年度的 21 支簡報目前仍在中文站，搬移中。</span></p>
      <p><a class="btn ghost" href="https://www.twrses.org/media/dom-jones/slides/" target="_blank" rel="noopener">
        Browse the 114 archive →</a></p>
    </div>
  </div>
</section>

<footer class="site-footer"><div class="wrap">
  <div class="cb-credit">
    © <span id="yr"></span> My Culture Connect · 人師教育協會. All rights reserved.<br>
    No. 136, Sec. 1, Wenyuan Rd., Beidou Township, Changhua County 521, Taiwan (R.O.C.)
  </div>
</div></footer>
<script src="/assets/js/main.js"></script>
</body>
</html>'''


def main():
    decks = load_decks()
    if not decks:
        sys.exit("no decks found in data/decks/")
    for d in decks:
        write(f"{LIB}{d['slug']}/", deck_page(d))
        write(f"{LIB}{d['slug']}/notes/", notes_page(d))
        if d.get("padlet"):
            write_qr(d["slug"], d["padlet"])
        print(f"  ✓ {d['slug']}  ({len(d['slides'])} slides + notes)")
    write(LIB, library_page(decks))
    print(f"  ✓ {LIB} (library, {len(decks)} deck(s))")


if __name__ == "__main__":
    main()
