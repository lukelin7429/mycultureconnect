#!/usr/bin/env python3
"""Build the page students study before THEY interview Dom.

    GEMINI_API_KEY=... python3 scripts/build_interview_prep.py

Some visits are not a lesson. At Huatan Junior High the students interview Dom,
show her their town and take her round their clubs. What they need beforehand
is not slides but material for good questions: who Dom is, the words they will
need, questions they could ask, follow-up phrases, and sentences for showing a
guest around. Each line has a speaker button.

One page per file in data/interviews/*.json, written to /preview/<slug>/.
The look, the speaker buttons, the stars and the listening game are the same as
the lesson preview pages (scripts/build_previews.py), which this reuses.
Recordings: Gemini, voice Leda (Azure's key stopped working on 2026-10-15).
"""
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_previews as bp  # noqa: E402

e = bp.e
bp.SPEAK_VOICE = 'gemini:Leda'


def rows(items, cls='pv-line', star=True, start=0):
    out = []
    for i, x in enumerate(items):
        sid = f' data-id="{cls}{start + i}"' if star else ''
        st = ('<button type="button" class="pv-star" aria-label="I can say it" aria-pressed="false">★</button>'
              if star else '')
        out.append(f'<li class="{cls} rv" style="--i:{i}"{sid}>{bp.speak_btn(x["en"])}'
                   f'<div><b>{e(x["en"])}</b><em>{e(x["zh"])}</em></div>{st}</li>')
    return ''.join(out)


EXTRA_CSS = '''
  .pv-facts { list-style:none; margin:0; padding:0; display:grid; gap:12px; grid-template-columns:repeat(auto-fill, minmax(170px, 1fr)); }
  .pv-fact { background:var(--card); border-radius:18px; padding:16px; box-shadow:0 8px 24px rgba(0,0,0,.06);
    border-top:5px solid var(--key); }
  .pv-fact b { display:block; font-size:2rem; line-height:1; color:var(--key2); }
  .pv-fact span { display:block; margin-top:6px; font-weight:700; line-height:1.3; }
  .pv-fact em { display:block; margin-top:2px; font-size:.92rem; opacity:.75; }
  .pv-qgroup { margin:22px 0 10px; font-size:1.08rem; color:var(--key2); }
  .pv-qgroup em { margin-left:8px; color:var(--ink); opacity:.7; font-size:.95rem; }
  .pv-tips { list-style:none; margin:0; padding:0; display:grid; gap:10px; counter-reset:t; }
  .pv-tips li { counter-increment:t; display:flex; gap:14px; align-items:flex-start; background:var(--card);
    border-radius:16px; padding:14px 16px; box-shadow:0 6px 18px rgba(0,0,0,.05); }
  .pv-tips li::before { content:counter(t); flex:none; width:30px; height:30px; border-radius:50%;
    background:var(--key); color:#fff; display:grid; place-content:center; font-weight:800; }
  .pv-tips b { display:block; font-weight:600; }
  .pv-tips em { display:block; opacity:.75; font-size:.95rem; }
'''


def page(d):
    key, key2, bg, ink = bp.THEMES.get(d.get('theme'), bp.THEMES['amber'])
    secs, nav, n = [], [], 0

    def sec(en, zh, lead_en, lead_zh, body, tools='', short=None):
        nonlocal n
        n += 1
        lead = f'<p class="pv-lead">{e(lead_en)}<em>{e(lead_zh)}</em></p>' if lead_en else ''
        secs.append(f'<section class="pv-sec rv" id="s{n}"><h2><span>{n}</span>{e(en)}<em>{e(zh)}</em></h2>{lead}{tools}{body}</section>')
        if short:
            nav.append((short[0], short[1], n))

    sec('Meet Teacher Dom', '認識 Dom 老師', 'Read and listen to Dom’s story. Knowing it helps you ask better questions.',
        '邊聽邊讀 Dom 的故事。先認識她，才問得出好問題。',
        f'<ol class="pv-read">{rows(d["bio"], cls="pv-rl", star=False)}</ol>',
        '<div class="pv-tools"><button type="button" class="pv-tool" id="story">▶ Play her story<em>播放整段</em></button></div>',
        ('Her Story', '她的故事'))
    facts = ''.join(f'<li class="pv-fact rv" style="--i:{i}"><b>{e(f["num"])}</b><span>{e(f["en"])}</span><em>{e(f["zh"])}</em></li>'
                    for i, f in enumerate(d['facts']))
    sec('Dom in Numbers', '數字看 Dom', '', '', f'<ul class="pv-facts">{facts}</ul>')

    wid, blocks = 0, []
    for g in d['groups']:
        cards = []
        for w in g['words']:
            cards.append(f'<li class="pv-word rv" style="--i:{len(cards)}" data-id="w{wid}" data-zh="{e(w["zh"])}" data-en="{e(w["en"])}">'
                         f'{bp.speak_btn(w["en"], "pv-say pv-say--card")}<b>{e(w["en"])}</b><em>{e(w["zh"])}</em>'
                         '<button type="button" class="pv-star" aria-label="I can say it" aria-pressed="false">★</button></li>')
            wid += 1
        blocks.append(f'<h3 class="pv-group">{e(g["en"])}<em>{e(g["zh"])}</em><small>{len(g["words"])}</small></h3>'
                      f'<ul class="pv-words">{"".join(cards)}</ul>')
    sec('Words', '單字', f'{wid} words you will need. Tap a card to hear it.', f'這次會用到的 {wid} 個字。點卡片聽發音。',
        ''.join(blocks),
        '<div class="pv-tools"><button type="button" class="pv-tool" id="all">▶ Play all<em>全部播放</em></button>'
        '<button type="button" class="pv-tool" id="slow" aria-pressed="false">🐢 Slow<em>慢速</em></button></div>',
        ('Words', '單字'))
    sec('Listening Game', '聽力小遊戲', 'Listen to a word. Tap what it means. Ten rounds — how many can you get?',
        '聽一個英文字，點出它的中文意思。一共十題，你能答對幾題？',
        '''<div class="pv-game" id="game">
  <div class="pv-game-top"><span id="g-round">Round 1 / 10</span><span id="g-score">★ 0</span></div>
  <button type="button" class="pv-game-play" id="g-play"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 9v6h4l5 4V5L8 9H4z"/><path d="M16 9.2a4 4 0 0 1 0 5.6" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><path d="M18.6 6.6a7.6 7.6 0 0 1 0 10.8" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg><span>Start<em>開始</em></span></button>
  <div class="pv-game-opts" id="g-opts"></div>
  <p class="pv-game-msg" id="g-msg" aria-live="polite"></p>
</div>''', short=('Game', '遊戲'))

    qs, k = [], 0
    for g in d['questions']:
        qs.append(f'<h3 class="pv-qgroup">{e(g["en"])}<em>{e(g["zh"])}</em></h3><ul class="pv-lines">{rows(g["items"], start=k)}</ul>')
        k += len(g['items'])
    sec('Questions You Can Ask', '可以問的問題', 'Pick the questions you like, practice them, and tap the star when you can say one smoothly. You can also write your own!',
        '挑你喜歡的問題來練習，唸順了就點星星。也可以自己想新的問題！', ''.join(qs), short=('Questions', '問題'))
    sec('Keep the Conversation Going', '接著追問', 'A great interviewer listens, then asks one more question.',
        '好的採訪者會先聽，再追問一題。', f'<ul class="pv-lines">{rows(d["followups"], start=100)}</ul>')
    sec('Show Dom Huatan', '帶 Dom 認識花壇', 'In the next class you will show Dom your school and share a local snack. Fill in the blanks with your own words.',
        '下一節你們要帶 Dom 認識學校、請她吃在地點心。空格填上你們自己的內容。',
        f'<ul class="pv-lines">{rows(d["huatan"], start=200)}</ul>', short=('Huatan', '花壇'))
    tips = ''.join(f'<li class="rv" style="--i:{i}"><div><b>{e(t["en"])}</b><em>{e(t["zh"])}</em></div></li>' for i, t in enumerate(d['tips']))
    sec('Interview Tips', '採訪小技巧', '', '', f'<ol class="pv-tips">{tips}</ol>')
    t = d['think']
    sec('Your Question', '你的問題', '', '',
        f'<div class="pv-think"><p class="q">{e(t["prompt_en"])}<em>{e(t["prompt_zh"])}</em></p>'
        f'<div class="frame">{bp.speak_btn(t["sentence_en"])}<div><b>{e(t["sentence_en"])}</b><em>{e(t["sentence_zh"])}</em></div></div></div>')

    navhtml = ''.join(f'<a href="#s{i}">{e(a)}<em>{e(b)}</em></a>' for a, b, i in nav)
    css = bp.CSS.replace('KEY2', key2).replace('KEY', key).replace('BG', bg).replace('INK', ink) + EXTRA_CSS
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(d["title"])} · {e(d["school_en"])} — My Culture Connect</title>
<meta name="description" content="Get ready to interview Teacher Dom: her story, words, questions and phrases, with audio.">
<meta name="robots" content="noindex">
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="icon" type="image/png" sizes="32x32" href="/assets/img/icon-32.png">
<link rel="icon" type="image/png" sizes="192x192" href="/assets/img/icon-192.png">
<link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png">
<style>{css}</style>
</head>
<body>
<header class="pv-hero"><div class="wrap">
  <span class="pv-tag">Get Ready<em>課前預習</em></span>
  <h1>{e(d["title"])}</h1>
  <div class="zh">{e(d["title_zh"])}</div>
  <div class="pv-meta">{e(d["school_en"])} {e(d["school"])} · {e(d["date"])}
    <em>{e(d["lead_zh"])}</em></div>
  <ul class="pv-how">
    <li>🔊 Tap to listen<em>點一下，聽發音</em></li>
    <li>🗣 Say it out loud<em>跟著大聲唸</em></li>
    <li>★ Tap the star when you can say it<em>會唸了，就點星星</em></li>
  </ul>
</div></header>

<div class="pv-bar"><div class="wrap">
  <span class="pv-count"><span id="n">0</span> / <span id="t">0</span> ★<em>我會唸了</em></span>
  <div class="pv-track"><div class="pv-fill" id="fill"></div></div>
</div><nav class="pv-nav wrap">{navhtml}</nav></div>

<main class="wrap">
{"".join(secs)}
<div class="pv-done rv"><b>See you on December 8!</b><em>12 月 8 日見！</em></div>
</main>

<footer class="pv-foot wrap">Made for {e(d["school_en"])} by <a href="/">My Culture Connect</a> 人師教育協會 · Dom's story from <a href="/dom-jones.html">her page on our site</a></footer>
<script>{bp.JS.replace("SLUG", d["slug"])}</script>
</body>
</html>
'''


def main():
    for path in sorted(glob.glob(os.path.join(bp.ROOT, 'data', 'interviews', '*.json'))):
        with open(path, encoding='utf-8') as f:
            d = json.load(f)
        print(f'  {d["slug"]}')
        out = os.path.join(bp.ROOT, 'preview', d['slug'], 'index.html')
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, 'w', encoding='utf-8') as f:
            f.write(page(d))
    if not bp.GEMINI_KEY:
        print('  (GEMINI_API_KEY not set: no new recordings were made)', file=sys.stderr)


if __name__ == '__main__':
    main()
