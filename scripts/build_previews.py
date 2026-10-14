#!/usr/bin/env python3
"""Build the "get ready" page a class can study BEFORE Dom's visit.

    AZURE_SPEECH_KEY=... python3 scripts/build_previews.py

A school often asks for the slides ahead of time so the students can prepare.
Handing over the deck gives away every quiz answer. This page is what goes out
instead: the words and sentences from the lesson, each with a speaker button,
and nothing that is a question with an answer.

A deck gets a page when its JSON has a "preview" key. Taken from the deck:
  words      every topic slide's keywords, plus preview.words (extra vocabulary)
  sentences  the "Say It With Me" slide
  think      the turn-and-talk question and its sentence frame
  big idea   the first topic slide's definition
Never taken: quizzes, true/false, sorting, big numbers, videos.

Audio is recorded once per sentence with Azure speech and kept in
assets/audio/preview/ (named by the text, so an unchanged sentence is never
recorded twice). Without AZURE_SPEECH_KEY the page is still built, and only
sentences that already have a recording get a speaker button.

Output: /preview/<deck slug>/index.html
"""
import glob
import hashlib
import html
import json
import os
import re
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIO = 'assets/audio/preview'
VOICE = 'en-US-JennyNeural'
REGION = 'eastasia'
KEY = os.environ.get('AZURE_SPEECH_KEY', '')

THEMES = {  # the deck's own colors, so the page and the lesson look like one thing
    'amber':  ('#e2620f', '#b8480a', '#fdf4e3', '#3a2a12'),
    'violet': ('#7a3fc4', '#5b2a9b', '#f5f0fb', '#2c1a48'),
    'sky':    ('#1183b8', '#0a6590', '#eaf6fd', '#0f2f46'),
    'leaf':   ('#2f7d3b', '#1f5e2b', '#eef6ec', '#17301c'),
    'teal':   ('#0f766e', '#0b5750', '#e9f6f4', '#0f2b28'),
}
e = html.escape


def spoken(text):
    """What the voice should say: a blank is a pause, not the word 'underscore'."""
    t = re.sub(r'_{3,}', ' <break time="700ms"/> ', e(text))
    return re.sub(r'\s+', ' ', t).strip()


def audio(text):
    """Path of the recording for this text, made now if it does not exist yet."""
    name = hashlib.sha1((VOICE + '|' + text).encode()).hexdigest()[:14] + '.mp3'
    rel = f'{AUDIO}/{name}'
    path = os.path.join(ROOT, rel)
    if os.path.exists(path):
        return '/' + rel
    if not KEY:
        return ''
    ssml = (f'<speak version="1.0" xml:lang="en-US"><voice name="{VOICE}">'
            f'<prosody rate="-10%">{spoken(text)}</prosody></voice></speak>')
    req = urllib.request.Request(
        f'https://{REGION}.tts.speech.microsoft.com/cognitiveservices/v1', data=ssml.encode('utf-8'),
        headers={'Ocp-Apim-Subscription-Key': KEY, 'Content-Type': 'application/ssml+xml',
                 'X-Microsoft-OutputFormat': 'audio-24khz-48kbitrate-mono-mp3', 'User-Agent': 'mcc-preview'})
    data = urllib.request.urlopen(req, timeout=60).read()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'wb') as f:
        f.write(data)
    print(f'    recorded  {text[:60]}')
    return '/' + rel


def collect(deck):
    words, seen = [], set()
    def add(w):
        k = w['en'].lower()
        if k not in seen:
            seen.add(k)
            words.append(w)
    idea = None
    sentences, think = [], None
    for s in deck['slides']:
        if s['type'] == 'topic':
            if idea is None:
                idea = {'head_en': s['head_en'], 'head_zh': s['head_zh'], 'en': s['body_en'], 'zh': s['body_zh']}
            for w in s.get('keywords', []):
                add(w)
        elif s['type'] == 'phrases':
            sentences += s['items']
        elif s['type'] == 'pairshare' and think is None:
            think = s
    for w in deck['preview'].get('words', []) if isinstance(deck['preview'], dict) else []:
        add(w)
    return words, sentences, think, idea


def speak_btn(text, cls='pv-say'):
    src = audio(text)
    if not src:
        return ''
    return (f'<button type="button" class="{cls}" data-src="{src}" aria-label="Listen: {e(text)}">'
            '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 9v6h4l5 4V5L8 9H4z"/>'
            '<path class="w1" d="M16 9.2a4 4 0 0 1 0 5.6"/><path class="w2" d="M18.6 6.6a7.6 7.6 0 0 1 0 10.8"/></svg></button>')


def page(deck):
    key, key2, bg, ink = THEMES.get(deck.get('theme'), THEMES['amber'])
    words, sentences, think, idea = collect(deck)
    title = next(s for s in deck['slides'] if s['type'] == 'title')
    chips = ''.join(f'<li><b>{e(c["en"])}</b><em>{e(c["zh"])}</em></li>' for c in title.get('chips', []))

    cards = ''.join(
        f'<li class="pv-word rv" style="--i:{i}" data-id="w{i}">{speak_btn(w["en"], "pv-say pv-say--card")}'
        f'<b>{e(w["en"])}</b><em>{e(w["zh"])}</em>'
        f'<button type="button" class="pv-star" aria-label="I can say it" aria-pressed="false">★</button></li>'
        for i, w in enumerate(words))
    rows = ''.join(
        f'<li class="pv-line rv" style="--i:{i}" data-id="s{i}">{speak_btn(x["en"])}'
        f'<div><b>{e(x["en"])}</b><em>{e(x["zh"])}</em></div>'
        f'<button type="button" class="pv-star" aria-label="I can say it" aria-pressed="false">★</button></li>'
        for i, x in enumerate(sentences))
    idea_html = (f'''<section class="pv-sec rv">
  <h2><span>1</span>The Big Idea<em>今天的主題</em></h2>
  <div class="pv-idea">{speak_btn(idea["en"])}<div><h3>{e(idea["head_en"])}<em>{e(idea["head_zh"])}</em></h3>
    <p>{e(idea["en"])}</p><p class="zh">{e(idea["zh"])}</p></div></div>
</section>''' if idea else '')
    think_html = (f'''<section class="pv-sec rv">
  <h2><span>4</span>Think About It<em>先想一想</em></h2>
  <p class="pv-lead">Dom will ask you this in class. You do not need to write anything — just think of your answer.
    <em>Dom 上課時會問這個問題。不用寫下來，先想好你的答案就可以了。</em></p>
  <div class="pv-think"><p class="q">{e(think["prompt_en"])}<em>{e(think["prompt_zh"])}</em></p>
    <div class="frame">{speak_btn(think["sentence_en"])}<div><b>{e(think["sentence_en"])}</b><em>{e(think["sentence_zh"])}</em></div></div></div>
</section>''' if think else '')

    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Get Ready: {e(deck["title_en"])} · {e(deck["school_en"])} — My Culture Connect</title>
<meta name="description" content="Words and sentences to practice before Teacher Dom's lesson on {e(deck["title_en"])}.">
<meta name="robots" content="noindex">
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="icon" type="image/png" sizes="32x32" href="/assets/img/icon-32.png">
<link rel="icon" type="image/png" sizes="192x192" href="/assets/img/icon-192.png">
<link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png">
<style>
  :root {{ --key:{key}; --key2:{key2}; --bg:{bg}; --ink:{ink}; --card:#fff; --line:rgba(0,0,0,.09);
    --zh:'PingFang TC','Apple LiGothic Medium','Microsoft JhengHei',sans-serif; }}
  * {{ box-sizing:border-box; }}
  html {{ scroll-behavior:smooth; }}
  body {{ margin:0; background:var(--bg); color:var(--ink);
    font:17px/1.55 -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Helvetica Neue', Arial, sans-serif; }}
  em {{ font-style:normal; font-family:var(--zh); font-weight:400; }}
  button {{ font:inherit; cursor:pointer; -webkit-tap-highlight-color:transparent; }}
  .wrap {{ max-width:860px; margin:0 auto; padding:0 18px; }}

  .pv-hero {{ background:linear-gradient(140deg, var(--key), var(--key2)); color:#fff; padding:34px 0 30px;
    position:relative; overflow:hidden; }}
  .pv-hero::before, .pv-hero::after {{ content:""; position:absolute; border-radius:50%; background:rgba(255,255,255,.1); }}
  .pv-hero::before {{ width:340px; height:340px; right:-110px; top:-130px; animation:drift 9s ease-in-out infinite alternate; }}
  .pv-hero::after {{ width:190px; height:190px; right:120px; bottom:-120px; animation:drift 11s ease-in-out infinite alternate-reverse; }}
  @keyframes drift {{ to {{ transform:translate(-22px, 18px) scale(1.08); }} }}
  .pv-hero .wrap {{ position:relative; z-index:1; }}
  .pv-tag {{ display:inline-block; background:rgba(255,255,255,.2); border-radius:999px; padding:5px 14px;
    font-size:.82rem; font-weight:800; letter-spacing:.06em; text-transform:uppercase; }}
  .pv-tag em {{ margin-left:8px; letter-spacing:0; }}
  .pv-hero h1 {{ margin:14px 0 2px; font-size:clamp(2.3rem, 8vw, 3.6rem); line-height:1.04; letter-spacing:-.01em; }}
  .pv-hero .zh {{ font-family:var(--zh); font-size:clamp(1.25rem, 4.2vw, 1.7rem); opacity:.95; }}
  .pv-meta {{ margin-top:14px; font-weight:700; opacity:.95; }}
  .pv-meta em {{ margin-left:6px; }}
  .pv-how {{ margin:18px 0 0; padding:0; list-style:none; display:flex; flex-wrap:wrap; gap:8px 10px; }}
  .pv-how li {{ background:rgba(0,0,0,.16); border-radius:12px; padding:8px 13px; font-size:.92rem; font-weight:700; }}
  .pv-how li em {{ display:block; font-size:.82rem; opacity:.9; }}

  .pv-bar {{ position:sticky; top:0; z-index:5; background:rgba(255,255,255,.94); backdrop-filter:blur(8px);
    border-bottom:1px solid var(--line); }}
  .pv-bar .wrap {{ display:flex; align-items:center; gap:14px; padding-top:10px; padding-bottom:10px; }}
  .pv-count {{ font-weight:800; color:var(--key2); white-space:nowrap; font-size:.95rem; }}
  .pv-count em {{ margin-left:6px; color:var(--ink); opacity:.7; }}
  .pv-track {{ flex:1; height:10px; border-radius:999px; background:var(--line); overflow:hidden; }}
  .pv-fill {{ height:100%; width:0; border-radius:999px; background:var(--key); transition:width .5s cubic-bezier(.2,.8,.2,1); }}

  .pv-sec {{ padding:34px 0 6px; }}
  .pv-sec h2 {{ margin:0 0 4px; font-size:1.5rem; display:flex; align-items:center; gap:12px; flex-wrap:wrap; }}
  .pv-sec h2 span {{ flex:none; width:36px; height:36px; border-radius:50%; background:var(--key); color:#fff;
    display:grid; place-content:center; font-size:1.05rem; }}
  .pv-sec h2 em {{ font-size:1.05rem; opacity:.7; }}
  .pv-lead {{ margin:6px 0 16px; opacity:.85; }}
  .pv-lead em {{ display:block; font-size:.93rem; }}

  .pv-say {{ flex:none; width:52px; height:52px; border-radius:50%; border:0; background:var(--key); color:#fff;
    display:grid; place-content:center; box-shadow:0 5px 14px rgba(0,0,0,.16); transition:transform .15s, background .2s; }}
  .pv-say svg {{ width:27px; height:27px; fill:currentColor; }}
  .pv-say svg .w1, .pv-say svg .w2 {{ fill:none; stroke:currentColor; stroke-width:2; stroke-linecap:round; opacity:.55; }}
  .pv-say:hover {{ transform:scale(1.07); background:var(--key2); }}
  .pv-say:active {{ transform:scale(.94); }}
  .is-playing > .pv-say, .pv-say.is-playing {{ background:var(--key2); animation:pulse 1s ease-in-out infinite; }}
  .is-playing .w1, .pv-say.is-playing .w1 {{ animation:wave .9s ease-in-out infinite; }}
  .is-playing .w2, .pv-say.is-playing .w2 {{ animation:wave .9s ease-in-out .18s infinite; }}
  @keyframes pulse {{ 50% {{ box-shadow:0 0 0 11px color-mix(in srgb, var(--key) 22%, transparent); }} }}
  @keyframes wave {{ 50% {{ opacity:1; }} }}

  .pv-idea, .pv-think .frame {{ display:flex; gap:16px; align-items:flex-start; background:var(--card);
    border-radius:20px; padding:20px; box-shadow:0 8px 26px rgba(0,0,0,.06); }}
  .pv-idea h3 {{ margin:0 0 6px; font-size:1.2rem; color:var(--key2); }}
  .pv-idea h3 em {{ margin-left:8px; font-size:1rem; color:var(--ink); opacity:.7; }}
  .pv-idea p {{ margin:0; font-size:1.2rem; font-weight:600; line-height:1.45; }}
  .pv-idea p.zh {{ font-family:var(--zh); font-weight:400; font-size:1.02rem; margin-top:6px; opacity:.8; }}

  .pv-tools {{ display:flex; flex-wrap:wrap; gap:10px; margin:0 0 16px; }}
  .pv-tool {{ border:2px solid var(--key); background:transparent; color:var(--key2); border-radius:999px;
    padding:8px 16px; font-weight:800; font-size:.93rem; transition:background .2s, color .2s; }}
  .pv-tool em {{ margin-left:6px; }}
  .pv-tool:hover, .pv-tool[aria-pressed="true"] {{ background:var(--key); color:#fff; }}

  .pv-words {{ list-style:none; margin:0; padding:0; display:grid; gap:14px; grid-template-columns:repeat(auto-fill, minmax(178px, 1fr)); }}
  .pv-word {{ position:relative; background:var(--card); border-radius:20px; padding:18px 14px 16px; text-align:center;
    box-shadow:0 8px 24px rgba(0,0,0,.06); cursor:pointer; border:2px solid transparent;
    transition:transform .18s, border-color .2s, box-shadow .2s; }}
  .pv-word:hover {{ transform:translateY(-4px); box-shadow:0 14px 30px rgba(0,0,0,.1); }}
  .pv-word.is-playing {{ border-color:var(--key); }}
  .pv-word .pv-say {{ margin:0 auto 10px; }}
  .pv-word b {{ display:block; font-size:1.5rem; line-height:1.15; }}
  .pv-word em {{ display:block; margin-top:3px; font-size:1.05rem; opacity:.75; }}

  .pv-lines {{ list-style:none; margin:0; padding:0; display:grid; gap:12px; }}
  .pv-line {{ display:flex; align-items:center; gap:16px; background:var(--card); border-radius:18px; padding:14px 16px;
    box-shadow:0 8px 24px rgba(0,0,0,.06); border:2px solid transparent; transition:border-color .2s; }}
  .pv-line.is-playing {{ border-color:var(--key); }}
  .pv-line > div, .pv-think .frame > div {{ flex:1; min-width:0; }}
  .pv-line b, .pv-think .frame b {{ display:block; font-size:1.28rem; line-height:1.3; }}
  .pv-line em, .pv-think .frame em {{ display:block; font-size:1rem; opacity:.75; }}

  .pv-star {{ flex:none; width:42px; height:42px; border-radius:50%; border:2px solid var(--line); background:transparent;
    color:rgba(0,0,0,.2); font-size:1.25rem; line-height:1; transition:transform .2s, color .2s, border-color .2s, background .2s; }}
  .pv-word .pv-star {{ position:absolute; top:8px; right:8px; width:34px; height:34px; font-size:1.05rem; }}
  .pv-star:hover {{ transform:scale(1.12); }}
  .pv-star[aria-pressed="true"] {{ color:#fff; background:#f5b301; border-color:#f5b301; animation:pop .4s cubic-bezier(.2,1.6,.4,1); }}
  @keyframes pop {{ 0% {{ transform:scale(.6) rotate(-30deg); }} }}

  .pv-think .q {{ margin:0 0 14px; font-size:1.35rem; font-weight:700; line-height:1.35; }}
  .pv-think .q em {{ display:block; font-size:1.05rem; opacity:.75; margin-top:4px; }}

  .pv-done {{ margin:38px 0 0; background:var(--key); color:#fff; border-radius:22px; padding:26px 22px; text-align:center; }}
  .pv-done b {{ display:block; font-size:1.5rem; }}
  .pv-done em {{ display:block; margin-top:4px; opacity:.95; }}
  .pv-foot {{ padding:26px 0 46px; font-size:.86rem; opacity:.65; text-align:center; }}
  .pv-foot a {{ color:inherit; }}

  .rv {{ opacity:0; transform:translateY(18px); transition:opacity .55s ease, transform .55s cubic-bezier(.2,.8,.2,1);
    transition-delay:calc(var(--i, 0) * 45ms); }}
  .rv.in {{ opacity:1; transform:none; }}
  @media (prefers-reduced-motion: reduce) {{
    .rv {{ opacity:1; transform:none; transition:none; }}
    .pv-hero::before, .pv-hero::after, .pv-say {{ animation:none !important; }}
  }}
  @media (max-width:520px) {{
    body {{ font-size:16px; }}
    .pv-words {{ grid-template-columns:repeat(2, 1fr); gap:10px; }}
    .pv-word b {{ font-size:1.25rem; }}
    .pv-line {{ gap:12px; padding:12px; }}
    .pv-line b, .pv-think .frame b {{ font-size:1.12rem; }}
    .pv-idea {{ flex-direction:column; }}
  }}
</style>
</head>
<body>
<header class="pv-hero"><div class="wrap">
  <span class="pv-tag">Get Ready<em>課前預習</em></span>
  <h1>{e(deck["title_en"])}</h1>
  <div class="zh">{e(deck["title"])}</div>
  <div class="pv-meta">{e(deck["school_en"])} {e(deck["school"])} · {e(deck["classes"])} · {e(deck["date"])}
    <em>Teacher Dom 來上課之前，先練習這些字和句子。</em></div>
  <ul class="pv-how">
    <li>🔊 Tap to listen<em>點一下，聽發音</em></li>
    <li>🗣 Say it out loud<em>跟著大聲唸</em></li>
    <li>★ Tap the star when you can say it<em>會唸了，就點星星</em></li>
  </ul>
</div></header>

<div class="pv-bar"><div class="wrap">
  <span class="pv-count"><span id="n">0</span> / <span id="t">0</span> ★<em>我會唸了</em></span>
  <div class="pv-track"><div class="pv-fill" id="fill"></div></div>
</div></div>

<main class="wrap">
{idea_html}
<section class="pv-sec rv">
  <h2><span>2</span>Words<em>單字</em></h2>
  <p class="pv-lead">Tap a card to hear the word. Say it three times.<em>點卡片聽發音，跟著唸三次。</em></p>
  <div class="pv-tools">
    <button type="button" class="pv-tool" id="all">▶ Play all<em>全部播放</em></button>
    <button type="button" class="pv-tool" id="slow" aria-pressed="false">🐢 Slow<em>慢速</em></button>
  </div>
  <ul class="pv-words">{cards}</ul>
</section>

<section class="pv-sec rv">
  <h2><span>3</span>Sentences<em>句子</em></h2>
  <p class="pv-lead">You will say these with Dom. Listen, then repeat.<em>上課時會跟 Dom 一起唸。先聽，再跟著唸。</em></p>
  <ul class="pv-lines">{rows}</ul>
</section>
{think_html}
<div class="pv-done rv"><b>See you in class!</b><em>我們教室見！</em></div>
</main>

<footer class="pv-foot wrap">Made for {e(deck["school_en"])} by <a href="/">My Culture Connect</a> 人師教育協會</footer>

<script>
(function () {{
  var KEY = 'pv:{deck["slug"]}';
  var done = {{}};
  try {{ done = JSON.parse(localStorage.getItem(KEY) || '{{}}'); }} catch (err) {{}}
  var items = [].slice.call(document.querySelectorAll('[data-id]'));
  var slow = false, player = new Audio(), current = null, queue = [];

  function paint() {{
    var n = 0;
    items.forEach(function (el) {{
      var on = !!done[el.dataset.id]; if (on) n++;
      el.querySelector('.pv-star').setAttribute('aria-pressed', on);
    }});
    document.getElementById('n').textContent = n;
    document.getElementById('t').textContent = items.length;
    document.getElementById('fill').style.width = (items.length ? n / items.length * 100 : 0) + '%';
  }}
  function stop() {{
    if (current) current.classList.remove('is-playing');
    current = null; player.pause();
  }}
  function play(btn) {{
    stop();
    current = btn.closest('[data-id]') || btn;
    current.classList.add('is-playing');
    player.src = btn.dataset.src;
    player.playbackRate = slow ? 0.7 : 1;
    player.preservesPitch = true;
    player.play().catch(stop);
  }}
  player.addEventListener('ended', function () {{
    stop();
    if (queue.length) setTimeout(function () {{ if (queue.length) play(queue.shift()); }}, 500);
  }});

  document.addEventListener('click', function (ev) {{
    var star = ev.target.closest('.pv-star');
    if (star) {{
      var id = star.closest('[data-id]').dataset.id;
      if (done[id]) delete done[id]; else done[id] = 1;
      try {{ localStorage.setItem(KEY, JSON.stringify(done)); }} catch (err) {{}}
      paint(); return;
    }}
    var btn = ev.target.closest('.pv-say') || (ev.target.closest('.pv-word') || document.createElement('i')).querySelector('.pv-say');
    if (btn) {{ queue = []; play(btn); }}
  }});
  document.getElementById('slow').addEventListener('click', function () {{
    slow = !slow; this.setAttribute('aria-pressed', slow);
  }});
  document.getElementById('all').addEventListener('click', function () {{
    queue = [].slice.call(document.querySelectorAll('.pv-word .pv-say'));
    if (queue.length) play(queue.shift());
  }});

  var io = 'IntersectionObserver' in window ? new IntersectionObserver(function (es) {{
    es.forEach(function (x) {{ if (x.isIntersecting) {{ x.target.classList.add('in'); io.unobserve(x.target); }} }});
  }}, {{ threshold: 0.08 }}) : null;
  [].forEach.call(document.querySelectorAll('.rv'), function (el) {{ io ? io.observe(el) : el.classList.add('in'); }});
  paint();
}})();
</script>
</body>
</html>
'''


def main():
    built = 0
    for path in sorted(glob.glob(os.path.join(ROOT, 'data', 'decks', '*.json'))):
        with open(path, encoding='utf-8') as f:
            deck = json.load(f)
        if not deck.get('preview'):
            continue
        print(f'  {deck["slug"]}')
        out = os.path.join(ROOT, 'preview', deck['slug'], 'index.html')
        os.makedirs(os.path.dirname(out), exist_ok=True)
        content = page(deck)
        with open(out, 'w', encoding='utf-8') as f:
            f.write(content)
        built += 1
    print(f'{built} preview page(s) -> /preview/<slug>/')
    if not KEY:
        print('  (AZURE_SPEECH_KEY not set: no new recordings were made)', file=sys.stderr)


if __name__ == '__main__':
    main()
