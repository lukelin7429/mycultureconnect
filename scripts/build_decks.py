#!/usr/bin/env python3
"""
Build Dom Jones slide decks for mycultureconnect.org.

    python3 scripts/build_decks.py

Reads one JSON per deck from data/decks/ and writes:

    slides/index.html                 bilingual library (English first)
    slides/<slug>/index.html          the deck itself — no site chrome
    slides/<slug>/qr.svg              Padlet QR, generated locally

Deck pages carry no site navigation on purpose: you open one to project it in
a classroom, so the site menu would only be clutter.

Two kinds of deck live here: the 115 decks are built from typed slides (quiz,
game, video…) and are interactive; the 114 decks are the original pre-rendered
JPG sets and just page through their images.
"""
import html
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _asset_version():
    """Hash of the deck assets, appended to their URLs so a fix never reaches a
    classroom as a stale cached file."""
    import hashlib
    h = hashlib.sha1()
    for rel in ("assets/css/deck.css", "assets/js/deck.js"):
        try:
            with open(os.path.join(ROOT, rel), "rb") as f:
                h.update(f.read())
        except FileNotFoundError:
            pass
    return h.hexdigest()[:8]


ASSET_V = _asset_version()
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


IMG_DECKS_FILE = os.path.join(ROOT, "data", "decks-114.json")


def load_image_decks():
    """The 114 decks: one folder of NN.jpg per deck, described in decks-114.json."""
    if not os.path.isfile(IMG_DECKS_FILE):
        return []
    with open(IMG_DECKS_FILE, encoding="utf-8") as f:
        raw = json.load(f)
    out = []
    ls = raw.get("life_story")
    if ls:
        out.append({**ls, "kind": "image", "year": "story",
                    "sub": ls.get("title_zh", ""), "title_en": ls["title"]})
    for d in raw.get("schools", []):
        out.append({**d, "kind": "image", "year": "114",
                    "sub": f'{d["school"]} · {d["date"]}', "title_en": d["title"]})
    for d in raw.get("templates", []):
        out.append({**d, "kind": "image", "year": "template",
                    "sub": "Reusable template · 通用範本", "title_en": d["title"]})
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
<link rel="stylesheet" href="/assets/css/deck.css?v={ASSET_V}">
</head>
<body class="deck-body">
<div class="deck">
  <div class="deck-top">
    <a class="deck-back" href="{LIB}">← Slide Library</a>
    <div class="deck-heading"><h1>{e(d["title_en"])}</h1>
      <div class="sub">{e(d["school_en"])} {e(d["school"])} · {e(d["date"])}</div></div>
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
<script src="/assets/js/deck.js?v={ASSET_V}"></script>
</body>
</html>'''


def image_deck_page(d):
    n = int(d["count"])
    nl = "\n"
    slides = nl.join(
        f'<div class="deck-slide"><img src="{i:02d}.jpg" alt="{e(d["title"])} — slide {i}" '
        f'loading="{"eager" if i == 1 else "lazy"}"></div>' for i in range(1, n + 1))
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(d["title"])} · {e(d.get("school", "Dom Jones"))} — My Culture Connect</title>
<meta name="description" content="Dom Jones bilingual assembly deck: {e(d["title"])}.">
<link rel="icon" type="image/png" href="/assets/img/favicon.png">
<link rel="stylesheet" href="/assets/css/deck.css?v={ASSET_V}">
</head>
<body class="deck-body">
<div class="deck">
  <div class="deck-top">
    <a class="deck-back" href="{LIB}">← Slide Library</a>
    <div class="deck-heading"><h1>{e(d["title"])}</h1>
      <div class="sub">{e(d["sub"])}</div></div>
    <div class="deck-pos-wrap"><b class="deck-pos">1</b> / {n}</div>
  </div>
  <div class="deck-stage">
    <div class="deck-track">
{slides}
    </div>
    <button class="deck-arrow prev" aria-label="Previous">&lsaquo;</button>
    <button class="deck-arrow next" aria-label="Next">&rsaquo;</button>
  </div>
  <div class="deck-progress"><div class="bar"></div></div>
  <p class="deck-hint">Swipe or use ← → to change slides</p>
</div>
<script src="/assets/js/deck.js?v={ASSET_V}"></script>
</body>
</html>'''


def library_page(decks):
    def card(d):
        interactive = d.get("kind") != "image"
        if interactive:
            cover = (f'<span class="dc-cover" data-theme="{d.get("theme","amber")}">'
                     f'<span class="dc-sdg">SDG {e(d["sdg"])}</span>'
                     f'<span class="dc-en">{e(d["title_en"])}</span>'
                     f'<span class="dc-zh">{e(d["title"])}</span></span>')
            sub = f'{e(d["school_en"])} {e(d["school"])} · {e(d["date"])}'
            cnt = f'{len(d["slides"])} slides · interactive →'
        else:
            cover = (f'<span class="dc-cover dc-photo">'
                     f'<img loading="lazy" src="{LIB}{d["slug"]}/01.jpg" alt="{e(d["title"])}"></span>')
            sub = e(d["sub"])
            cnt = f'{d["count"]} slides →'
        anchor = f' id="deck-{e(d["group"])}"' if d.get("group") else ""
        return f'''<a class="dcard" href="{LIB}{d["slug"]}/"{anchor}>
  {cover}
  <span class="dc-body"><b>{e(d["title_en"])}</b>
    <span class="dc-sub">{sub}</span><span class="dc-cnt">{cnt}</span></span>
</a>'''

    order = ["115", "114", "story", "template"]
    labels = {
        "115": ("2026–2027 · 115 學年度", "Interactive decks — questions reveal their answers when you tap them."),
        "114": ("2025–2026 · 114 學年度", "The first school tour across Changhua County."),
        "story": ("Dom's Own Story · Dom 的故事", ""),
        "template": ("Reusable Templates · 通用範本", ""),
    }
    by = {}
    for d in decks:
        by.setdefault(str(d.get("year", "114")), []).append(d)

    groups = []
    for y in order:
        if not by.get(y):
            continue
        title, blurb = labels[y]
        note = f'<p class="muted" style="margin-top:-.6em">{blurb}</p>' if blurb else ""
        groups.append(f'''<section class="dgroup">
  <h2>{title}</h2>{note}
  <div class="dgrid">{"".join(card(d) for d in by[y])}</div>
</section>''')

    nl = "\n"
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Slide Library — Dom Jones School Tour · My Culture Connect</title>
<meta name="description" content="Every bilingual slide deck Dom Jones presents at school assemblies across Changhua County.">
<link rel="icon" type="image/png" href="/assets/img/favicon.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noticia+Text:wght@400;700&family=Questrial&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/assets/css/style.css">
<style>
  .dgroup {{ margin-bottom:60px; }}
  .dgroup h2 {{ font-size:1.5rem; margin-bottom:.5em; }}
  .dgrid {{ display:grid; grid-template-columns:repeat(3,1fr); gap:26px; margin-top:24px; }}
  .dcard {{ display:flex; flex-direction:column; background:#fff; border:1px solid #e7e7e7;
    border-radius:16px; overflow:hidden; text-decoration:none; color:var(--ink);
    box-shadow:0 8px 26px rgba(20,20,20,.07); transition:transform .28s, box-shadow .28s;
    scroll-margin-top:100px; }}
  .dcard:hover {{ transform:translateY(-6px); box-shadow:0 24px 50px rgba(245,130,32,.18);
    text-decoration:none; }}
  .dc-cover {{ aspect-ratio:16/9; display:flex; flex-direction:column; justify-content:center;
    gap:6px; padding:22px 24px; background:var(--c-bg); }}
  .dc-cover[data-theme="amber"]  {{ --c-bg:#fdf4e3; --c-key:#e2620f; --c-key2:#b8480a; --c-ink:#3a2a12; }}
  .dc-cover[data-theme="teal"]   {{ --c-bg:#093a4a; --c-key:#16a394; --c-key2:#8fd8d0; --c-ink:#eaf6f8; }}
  .dc-cover[data-theme="violet"] {{ --c-bg:#f5f0fb; --c-key:#7a3fc4; --c-key2:#5b2a9b; --c-ink:#2c1a48; }}
  .dc-photo {{ padding:0; background:#eee; }}
  .dc-photo img {{ width:100%; height:100%; object-fit:cover; display:block; }}
  .dc-sdg {{ align-self:flex-start; background:var(--c-key); color:#fff; border-radius:999px;
    padding:5px 15px; font-size:.78rem; font-weight:800; font-family:var(--eyebrow); }}
  .dc-en {{ font-family:var(--serif); font-size:1.55rem; color:var(--c-key2); line-height:1.1; }}
  .dc-zh {{ font-size:.98rem; color:var(--c-ink); opacity:.8; }}
  .dc-body {{ padding:22px 24px; display:flex; flex-direction:column; gap:5px; }}
  .dc-body b {{ font-family:var(--serif); font-weight:400; font-size:1.2rem; line-height:1.2; }}
  .dc-sub {{ color:var(--muted-2); font-size:.94rem; }}
  .dc-cnt {{ margin-top:8px; font-family:var(--eyebrow); color:var(--orange-dark);
    font-weight:700; font-size:.92rem; }}
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
      on any device.</p>
    <p class="lead" style="color:var(--muted-2);font-size:1rem">
      Dom 在彰化每一場集會實際使用的雙語簡報，手機電腦都能左右滑動瀏覽。</p>
  </div>
</section>

<section>
  <div class="wrap">
{nl.join(groups)}
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
    for d in decks:
        write(f"{LIB}{d['slug']}/", deck_page(d))
        if d.get("padlet"):
            write_qr(d["slug"], d["padlet"])
        print(f"  ✓ {d['slug']}  ({len(d['slides'])} slides, interactive)")

    img = load_image_decks()
    for d in img:
        write(f"{LIB}{d['slug']}/", image_deck_page(d))
    print(f"  ✓ {len(img)} image deck(s) from 114")

    alld = decks + img
    if not alld:
        sys.exit("no decks found")
    write(LIB, library_page(alld))
    print(f"  ✓ {LIB} (library, {len(alld)} decks)")


if __name__ == "__main__":
    main()
