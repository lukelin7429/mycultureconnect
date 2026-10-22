#!/usr/bin/env python3
"""Build the "get ready" page a class can study BEFORE Dom's visit.

    AZURE_SPEECH_KEY=... python3 scripts/build_previews.py

A school often asks for the slides ahead of time so the students can prepare.
Handing over the deck gives away every quiz answer. This page is what goes out
instead: the words and sentences from the lesson, each with a speaker button,
and nothing that is a question with an answer.

A deck gets a page when its JSON has a "preview" key. Taken from the deck:
  words      every topic slide's keywords, plus preview.words (extra vocabulary)
  big idea   the first topic slide's definition
  meet Dom   the hello slide
  sentences  the "Say It With Me" slide; the class promise card
  stand up   the stand-up prompts (no answers in them: the answer is you)
  think      the turn-and-talk question and its sentence frame
  game words the 30-second challenge's word list
  plus, from preview: extra words, extra word groups, and a short text to read
A listening game (hear a word, tap its meaning) is made from the words.
Never taken: quizzes, true/false, sorting, big numbers, videos.

Audio is recorded once per sentence with Azure speech and kept in
assets/audio/preview/ (named by the text, so an unchanged sentence is never
recorded twice). Without AZURE_SPEECH_KEY the page is still built, and only
sentences that already have a recording get a speaker button.

Output: /preview/<deck slug>/index.html
"""
import base64
import glob
import hashlib
import html
import json
import os
import re
import subprocess
import sys
import time
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


GEMINI_KEY = os.environ.get('GEMINI_API_KEY', '')
GEMINI_MODEL = 'gemini-2.5-pro-preview-tts'   # the 3.x TTS models read the style line out loud
FFMPEG = next((p for p in ('/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg', '/opt/homebrew/bin/ffmpeg', '/usr/local/bin/ffmpeg')
               if os.path.exists(p)), 'ffmpeg')


def audio(text, voice=None):
    """Path of the recording for this text, made now if it does not exist yet.

    voice: an Azure voice name (the default, VOICE), or 'gemini:<Name>' for a
    Google voice. Azure's key stopped working on 2026-10-15; pages made since
    then use Gemini (Leda). A recording is named by voice + text, so an older
    page keeps finding the files it was built with."""
    voice = voice or VOICE
    name = hashlib.sha1((voice + '|' + text).encode()).hexdigest()[:14] + '.mp3'
    rel = f'{AUDIO}/{name}'
    path = os.path.join(ROOT, rel)
    if os.path.exists(path):
        return '/' + rel
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if voice.startswith('gemini:'):
        if not GEMINI_KEY:
            return ''
        said = re.sub(r'_{3,}', '...', text)
        body = json.dumps({
            'contents': [{'parts': [{'text': 'Say clearly and warmly, like a friendly teacher talking to junior high students: ' + said}]}],
            'generationConfig': {'responseModalities': ['AUDIO'], 'speechConfig': {
                'voiceConfig': {'prebuiltVoiceConfig': {'voiceName': voice.split(':', 1)[1]}}}}}).encode()
        req = urllib.request.Request(
            f'https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_KEY}',
            data=body, headers={'Content-Type': 'application/json'})
        for attempt in range(3):
            try:
                res = json.load(urllib.request.urlopen(req, timeout=120))
                pcm = base64.b64decode(res['candidates'][0]['content']['parts'][0]['inlineData']['data'])
                break
            except Exception as err:
                if attempt == 2:
                    raise
                time.sleep(4)
        subprocess.run([FFMPEG, '-v', 'error', '-y', '-f', 's16le', '-ar', '24000', '-ac', '1', '-i', '-',
                        '-af', 'silenceremove=start_periods=1:start_threshold=-50dB,areverse,silenceremove=start_periods=1:start_threshold=-50dB,areverse',
                        '-b:a', '64k', path], input=pcm, check=True)
    else:
        if not KEY:
            return ''
        ssml = (f'<speak version="1.0" xml:lang="en-US"><voice name="{voice}">'
                f'<prosody rate="-10%">{spoken(text)}</prosody></voice></speak>')
        req = urllib.request.Request(
            f'https://{REGION}.tts.speech.microsoft.com/cognitiveservices/v1', data=ssml.encode('utf-8'),
            headers={'Ocp-Apim-Subscription-Key': KEY, 'Content-Type': 'application/ssml+xml',
                     'X-Microsoft-OutputFormat': 'audio-24khz-48kbitrate-mono-mp3', 'User-Agent': 'mcc-preview'})
        with open(path, 'wb') as f:
            f.write(urllib.request.urlopen(req, timeout=60).read())
    print(f'    recorded  {text[:60]}')
    return '/' + rel


def collect(deck):
    """Everything on the page, taken from the deck. Never a question with its answer."""
    pv = deck['preview'] if isinstance(deck['preview'], dict) else {}
    seen, groups = set(), []

    def group(title_en, title_zh, items):
        out = []
        for w in items:
            k = w['en'].lower()
            if k not in seen:
                seen.add(k)
                out.append(w)
        if out:
            groups.append({'en': title_en, 'zh': title_zh, 'words': out})

    c = {'intro': None, 'idea': None, 'sentences': [], 'think': None, 'standup': None,
         'promise': None, 'read': pv.get('read', []), 'groups': groups}
    key = []
    for s in deck['slides']:
        t = s['type']
        if t == 'intro' and not c['intro']:
            c['intro'] = s
        elif t == 'topic':
            if not c['idea']:
                c['idea'] = {'head_en': s['head_en'], 'head_zh': s['head_zh'], 'en': s['body_en'], 'zh': s['body_zh']}
            key += s.get('keywords', [])
        elif t == 'phrases':
            c['sentences'] += s['items']
        elif t == 'pairshare' and not c['think']:
            c['think'] = s
        elif t == 'standup' and not c['standup']:
            c['standup'] = s
        elif t == 'card' and not c['promise']:
            c['promise'] = s
    group('Key Words', '關鍵字', key)
    group('More Words', '更多單字', pv.get('words', []))
    for g in pv.get('groups', []):
        group(g['en'], g['zh'], g['words'])
    # the 30-second challenge: knowing the words first is exactly the head start a class wants
    for s in deck['slides']:
        if s['type'] == 'game' and not s.get('bonus') and s.get('hints') and isinstance(s['hints'][0], str):
            pairs = []
            for h in s['hints']:
                m = re.match(r'(.+?)\s+([\u3400-\u9fff].*)$', h)
                if m:
                    pairs.append({'en': m.group(1), 'zh': m.group(2)})
            group(s['head_en'] + ' Words', s['head_zh'] + '會用到的字', pairs)
    return c


SPEAK_VOICE = None   # set by a page builder that records with another voice


def speak_btn(text, cls='pv-say'):
    src = audio(text, SPEAK_VOICE)
    # No recording (no working speech key when the page was built): the button
    # asks the browser to read the text instead. Re-running the build once a key
    # works replaces these with recordings.
    data = f'data-src="{src}"' if src else f'data-say="{e(re.sub(r"_{3,}", "blank", text))}"'
    return (f'<button type="button" class="{cls}" {data} aria-label="Listen: {e(text)}">'
            '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 9v6h4l5 4V5L8 9H4z"/>'
            '<path class="w1" d="M16 9.2a4 4 0 0 1 0 5.6"/><path class="w2" d="M18.6 6.6a7.6 7.6 0 0 1 0 10.8"/></svg></button>')


CSS = r"""  :root { --key:KEY; --key2:KEY2; --bg:BG; --ink:INK; --card:#fff; --line:rgba(0,0,0,.09);
    --zh:'PingFang TC','Apple LiGothic Medium','Microsoft JhengHei',sans-serif; }
  * { box-sizing:border-box; }
  html { scroll-behavior:smooth; }
  body { margin:0; background:var(--bg); color:var(--ink);
    font:17px/1.55 -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Helvetica Neue', Arial, sans-serif; }
  em { font-style:normal; font-family:var(--zh); font-weight:400; }
  button { font:inherit; cursor:pointer; -webkit-tap-highlight-color:transparent; }
  .wrap { max-width:860px; margin:0 auto; padding:0 18px; }

  .pv-hero { background:linear-gradient(140deg, var(--key), var(--key2)); color:#fff; padding:34px 0 30px;
    position:relative; overflow:hidden; }
  .pv-hero::before, .pv-hero::after { content:""; position:absolute; border-radius:50%; background:rgba(255,255,255,.1); }
  .pv-hero::before { width:340px; height:340px; right:-110px; top:-130px; animation:drift 9s ease-in-out infinite alternate; }
  .pv-hero::after { width:190px; height:190px; right:120px; bottom:-120px; animation:drift 11s ease-in-out infinite alternate-reverse; }
  @keyframes drift { to { transform:translate(-22px, 18px) scale(1.08); } }
  .pv-hero .wrap { position:relative; z-index:1; }
  .pv-tag { display:inline-block; background:rgba(255,255,255,.2); border-radius:999px; padding:5px 14px;
    font-size:.82rem; font-weight:800; letter-spacing:.06em; text-transform:uppercase; }
  .pv-tag em { margin-left:8px; letter-spacing:0; }
  .pv-hero h1 { margin:14px 0 2px; font-size:clamp(2.3rem, 8vw, 3.6rem); line-height:1.04; letter-spacing:-.01em; }
  .pv-hero .zh { font-family:var(--zh); font-size:clamp(1.25rem, 4.2vw, 1.7rem); opacity:.95; }
  .pv-meta { margin-top:14px; font-weight:700; opacity:.95; }
  .pv-meta em { margin-left:6px; }
  .pv-how { margin:18px 0 0; padding:0; list-style:none; display:flex; flex-wrap:wrap; gap:8px 10px; }
  .pv-how li { background:rgba(0,0,0,.16); border-radius:12px; padding:8px 13px; font-size:.92rem; font-weight:700; }
  .pv-how li em { display:block; font-size:.82rem; opacity:.9; }

  .pv-bar { position:sticky; top:0; z-index:5; background:rgba(255,255,255,.94); backdrop-filter:blur(8px);
    border-bottom:1px solid var(--line); }
  .pv-bar .wrap { display:flex; align-items:center; gap:14px; padding-top:10px; padding-bottom:10px; }
  .pv-count { font-weight:800; color:var(--key2); white-space:nowrap; font-size:.95rem; }
  .pv-count em { margin-left:6px; color:var(--ink); opacity:.7; }
  .pv-track { flex:1; height:10px; border-radius:999px; background:var(--line); overflow:hidden; }
  .pv-fill { height:100%; width:0; border-radius:999px; background:var(--key); transition:width .5s cubic-bezier(.2,.8,.2,1); }

  .pv-sec { padding:34px 0 6px; }
  .pv-sec h2 { margin:0 0 4px; font-size:1.5rem; display:flex; align-items:center; gap:12px; flex-wrap:wrap; }
  .pv-sec h2 span { flex:none; width:36px; height:36px; border-radius:50%; background:var(--key); color:#fff;
    display:grid; place-content:center; font-size:1.05rem; }
  .pv-sec h2 em { font-size:1.05rem; opacity:.7; }
  .pv-lead { margin:6px 0 16px; opacity:.85; }
  .pv-lead em { display:block; font-size:.93rem; }

  .pv-say { flex:none; width:52px; height:52px; border-radius:50%; border:0; background:var(--key); color:#fff;
    display:grid; place-content:center; box-shadow:0 5px 14px rgba(0,0,0,.16); transition:transform .15s, background .2s; }
  .pv-say svg { width:27px; height:27px; fill:currentColor; }
  .pv-say svg .w1, .pv-say svg .w2 { fill:none; stroke:currentColor; stroke-width:2; stroke-linecap:round; opacity:.55; }
  .pv-say:hover { transform:scale(1.07); background:var(--key2); }
  .pv-say:active { transform:scale(.94); }
  .is-playing > .pv-say, .pv-say.is-playing { background:var(--key2); animation:pulse 1s ease-in-out infinite; }
  .is-playing .w1, .pv-say.is-playing .w1 { animation:wave .9s ease-in-out infinite; }
  .is-playing .w2, .pv-say.is-playing .w2 { animation:wave .9s ease-in-out .18s infinite; }
  @keyframes pulse { 50% { box-shadow:0 0 0 11px color-mix(in srgb, var(--key) 22%, transparent); } }
  @keyframes wave { 50% { opacity:1; } }

  .pv-idea, .pv-think .frame { display:flex; gap:16px; align-items:flex-start; background:var(--card);
    border-radius:20px; padding:20px; box-shadow:0 8px 26px rgba(0,0,0,.06); }
  .pv-idea h3 { margin:0 0 6px; font-size:1.2rem; color:var(--key2); }
  .pv-idea h3 em { margin-left:8px; font-size:1rem; color:var(--ink); opacity:.7; }
  .pv-idea p { margin:0; font-size:1.2rem; font-weight:600; line-height:1.45; }
  .pv-idea p.zh { font-family:var(--zh); font-weight:400; font-size:1.02rem; margin-top:6px; opacity:.8; }

  .pv-tools { display:flex; flex-wrap:wrap; gap:10px; margin:0 0 16px; }
  .pv-tool { border:2px solid var(--key); background:transparent; color:var(--key2); border-radius:999px;
    padding:8px 16px; font-weight:800; font-size:.93rem; transition:background .2s, color .2s; }
  .pv-tool em { margin-left:6px; }
  .pv-tool:hover, .pv-tool[aria-pressed="true"] { background:var(--key); color:#fff; }

  .pv-words { list-style:none; margin:0; padding:0; display:grid; gap:14px; grid-template-columns:repeat(auto-fill, minmax(178px, 1fr)); }
  .pv-word { position:relative; background:var(--card); border-radius:20px; padding:18px 14px 16px; text-align:center;
    box-shadow:0 8px 24px rgba(0,0,0,.06); cursor:pointer; border:2px solid transparent;
    transition:transform .18s, border-color .2s, box-shadow .2s; }
  .pv-word:hover { transform:translateY(-4px); box-shadow:0 14px 30px rgba(0,0,0,.1); }
  .pv-word.is-playing { border-color:var(--key); }
  .pv-word .pv-say { margin:0 auto 10px; }
  .pv-word b { display:block; font-size:1.5rem; line-height:1.15; }
  .pv-word em { display:block; margin-top:3px; font-size:1.05rem; opacity:.75; }

  .pv-lines { list-style:none; margin:0; padding:0; display:grid; gap:12px; }
  .pv-line { display:flex; align-items:center; gap:16px; background:var(--card); border-radius:18px; padding:14px 16px;
    box-shadow:0 8px 24px rgba(0,0,0,.06); border:2px solid transparent; transition:border-color .2s; }
  .pv-line.is-playing { border-color:var(--key); }
  .pv-line > div, .pv-think .frame > div { flex:1; min-width:0; }
  .pv-line b, .pv-think .frame b { display:block; font-size:1.28rem; line-height:1.3; }
  .pv-line em, .pv-think .frame em { display:block; font-size:1rem; opacity:.75; }

  .pv-star { flex:none; width:42px; height:42px; border-radius:50%; border:2px solid var(--line); background:transparent;
    color:rgba(0,0,0,.2); font-size:1.25rem; line-height:1; transition:transform .2s, color .2s, border-color .2s, background .2s; }
  .pv-word .pv-star { position:absolute; top:8px; right:8px; width:34px; height:34px; font-size:1.05rem; }
  .pv-star:hover { transform:scale(1.12); }
  .pv-star[aria-pressed="true"] { color:#fff; background:#f5b301; border-color:#f5b301; animation:pop .4s cubic-bezier(.2,1.6,.4,1); }
  @keyframes pop { 0% { transform:scale(.6) rotate(-30deg); } }

  .pv-think .q { margin:0 0 14px; font-size:1.35rem; font-weight:700; line-height:1.35; }
  .pv-think .q em { display:block; font-size:1.05rem; opacity:.75; margin-top:4px; }

  .pv-done { margin:38px 0 0; background:var(--key); color:#fff; border-radius:22px; padding:26px 22px; text-align:center; }
  .pv-done b { display:block; font-size:1.5rem; }
  .pv-done em { display:block; margin-top:4px; opacity:.95; }
  .pv-foot { padding:26px 0 46px; font-size:.86rem; opacity:.65; text-align:center; }
  .pv-foot a { color:inherit; }

  .rv { opacity:0; transform:translateY(18px); transition:opacity .55s ease, transform .55s cubic-bezier(.2,.8,.2,1);
    transition-delay:calc(var(--i, 0) * 45ms); }
  .rv.in { opacity:1; transform:none; }
  @media (prefers-reduced-motion: reduce) {
    .rv { opacity:1; transform:none; transition:none; }
    .pv-hero::before, .pv-hero::after, .pv-say { animation:none !important; }
  }
  @media (max-width:520px) {
    body { font-size:16px; }
    .pv-words { grid-template-columns:repeat(2, 1fr); gap:10px; }
    .pv-word b { font-size:1.25rem; }
    .pv-line { gap:12px; padding:12px; }
    .pv-line b, .pv-think .frame b { font-size:1.12rem; }
    .pv-idea { flex-direction:column; }
  }

  .pv-nav { display:flex; gap:8px; overflow-x:auto; padding-bottom:10px; scrollbar-width:none; }
  .pv-nav::-webkit-scrollbar { display:none; }
  .pv-nav a { flex:none; text-decoration:none; color:var(--key2); background:var(--bg); border-radius:999px;
    padding:5px 13px; font-size:.85rem; font-weight:800; transition:background .2s, color .2s; }
  .pv-nav a em { margin-left:5px; font-weight:400; }
  .pv-nav a:hover { background:var(--key); color:#fff; }
  .pv-sec { scroll-margin-top:96px; }
  .pv-group { margin:22px 0 12px; font-size:1.08rem; display:flex; align-items:baseline; gap:8px; color:var(--key2); }
  .pv-group em { color:var(--ink); opacity:.7; font-size:.95rem; }
  .pv-group small { margin-left:auto; background:var(--key); color:#fff; border-radius:999px; padding:1px 10px; font-size:.8rem; }
  .pv-lines--plain .pv-line, .pv-lines--plain li { box-shadow:none; background:rgba(255,255,255,.7); }
  .pv-lines--plain li { display:flex; align-items:center; gap:16px; border-radius:18px; padding:12px 16px; border:2px solid transparent; }
  .pv-lines--plain li > div { flex:1; min-width:0; }
  .pv-lines--plain b { display:block; font-size:1.2rem; line-height:1.3; }
  .pv-lines--plain em { display:block; opacity:.75; }
  .pv-lines--plain li.is-playing { border-color:var(--key); }
  .pv-read { list-style:none; counter-reset:r; margin:0; padding:22px; background:var(--card); border-radius:22px;
    box-shadow:0 8px 26px rgba(0,0,0,.06); display:grid; gap:6px; }
  .pv-rl { display:flex; align-items:center; gap:14px; padding:8px; border-radius:14px; transition:background .25s; }
  .pv-rl .pv-say { width:40px; height:40px; }
  .pv-rl .pv-say svg { width:21px; height:21px; }
  .pv-rl > div { flex:1; min-width:0; }
  .pv-rl b { display:block; font-size:1.18rem; line-height:1.35; font-weight:600; }
  .pv-rl em { display:block; font-size:.95rem; opacity:.7; }
  .pv-rl.is-playing { background:var(--bg); }
  .pv-rl.is-playing b { color:var(--key2); }

  .pv-game { background:var(--card); border-radius:24px; padding:22px; box-shadow:0 10px 30px rgba(0,0,0,.07); text-align:center; }
  .pv-game-top { display:flex; justify-content:space-between; font-weight:800; color:var(--key2); margin-bottom:14px; }
  .pv-game-play { border:0; background:var(--key); color:#fff; border-radius:999px; padding:14px 28px 14px 22px;
    display:inline-flex; align-items:center; gap:12px; font-weight:800; font-size:1.15rem; box-shadow:0 8px 20px rgba(0,0,0,.15);
    transition:transform .15s, background .2s; }
  .pv-game-play svg { width:30px; height:30px; fill:currentColor; }
  .pv-game-play em { margin-left:6px; font-weight:400; }
  .pv-game-play:hover { transform:scale(1.05); background:var(--key2); }
  .pv-game-play.is-playing { animation:pulse 1s ease-in-out infinite; }
  .pv-game-opts { display:grid; grid-template-columns:repeat(2, 1fr); gap:12px; margin-top:18px; }
  .pv-game-opts button { border:2px solid var(--line); background:var(--bg); color:var(--ink); border-radius:16px;
    padding:16px 10px; font-family:var(--zh); font-size:1.25rem; transition:transform .15s, border-color .2s, background .2s; }
  .pv-game-opts button:hover { transform:translateY(-2px); border-color:var(--key); }
  .pv-game-opts button.right { background:#2f9e5b; border-color:#2f9e5b; color:#fff; animation:pop .35s; }
  .pv-game-opts button.wrong { background:#d64545; border-color:#d64545; color:#fff; animation:shake .35s; }
  .pv-game-opts button small { display:block; font-family:inherit; font-size:.85rem; opacity:.9; margin-top:2px; }
  @keyframes shake { 25% { transform:translateX(-6px); } 75% { transform:translateX(6px); } }
  .pv-game-msg { min-height:1.6em; margin:14px 0 0; font-weight:800; font-size:1.1rem; }
"""

JS = r"""(function () {
  var KEY = 'pv:SLUG';
  var done = {};
  try { done = JSON.parse(localStorage.getItem(KEY) || '{}'); } catch (err) {}
  var items = [].slice.call(document.querySelectorAll('[data-id]'));
  var slow = false, player = new Audio(), current = null, queue = [];

  function paint() {
    var n = 0;
    items.forEach(function (el) {
      var on = !!done[el.dataset.id]; if (on) n++;
      el.querySelector('.pv-star').setAttribute('aria-pressed', on);
    });
    document.getElementById('n').textContent = n;
    document.getElementById('t').textContent = items.length;
    document.getElementById('fill').style.width = (items.length ? n / items.length * 100 : 0) + '%';
  }
  var synth = window.speechSynthesis, voice = null;
  function pickVoice() {
    if (!synth || voice) return voice;
    var vs = synth.getVoices().filter(function (v) { return /^en[-_]US/i.test(v.lang); });
    var like = ['Google US English', 'Samantha', 'Microsoft Aria', 'Microsoft Jenny', 'Microsoft Zira'];
    for (var i = 0; i < like.length && !voice; i++)
      voice = vs.filter(function (v) { return v.name.indexOf(like[i]) === 0; })[0] || null;
    return voice || vs[0] || null;
  }
  if (synth) synth.onvoiceschanged = function () { voice = null; pickVoice(); };
  function stop() {
    if (current) current.classList.remove('is-playing');
    current = null; player.pause();
    if (synth) synth.cancel();
  }
  function ended() {
    stop();
    if (queue.length) setTimeout(function () { if (queue.length) play(queue.shift()); }, 500);
  }
  function play(btn) {
    stop();
    current = btn.closest('[data-id], .pv-rl, .pv-lines--plain li') || btn;
    current.classList.add('is-playing');
    if (btn.dataset.src) {
      player.src = btn.dataset.src;
      player.playbackRate = slow ? 0.7 : 1;
      player.preservesPitch = true;
      player.play().catch(stop);
    } else if (synth) {
      var u = new SpeechSynthesisUtterance(btn.dataset.say);
      u.lang = 'en-US'; u.rate = slow ? 0.6 : 0.88;
      var v = pickVoice(); if (v) u.voice = v;
      u.onend = ended; u.onerror = stop;
      synth.speak(u);
    } else stop();
  }
  player.addEventListener('ended', ended);

  document.addEventListener('click', function (ev) {
    var star = ev.target.closest('.pv-star');
    if (star) {
      var id = star.closest('[data-id]').dataset.id;
      if (done[id]) delete done[id]; else done[id] = 1;
      try { localStorage.setItem(KEY, JSON.stringify(done)); } catch (err) {}
      paint(); return;
    }
    var btn = ev.target.closest('.pv-say') || (ev.target.closest('.pv-word') || document.createElement('i')).querySelector('.pv-say');
    if (btn) { queue = []; play(btn); }
  });
  var slowBtn = document.getElementById('slow'); if (slowBtn) slowBtn.addEventListener('click', function () {
    slow = !slow; this.setAttribute('aria-pressed', slow);
  });
  var allBtn = document.getElementById('all'); if (allBtn) allBtn.addEventListener('click', function () {
    queue = [].slice.call(document.querySelectorAll('.pv-word .pv-say'));
    if (queue.length) play(queue.shift());
  });

  var storyBtn = document.getElementById('story');
  if (storyBtn) storyBtn.addEventListener('click', function () {
    queue = [].slice.call(document.querySelectorAll('.pv-rl .pv-say'));
    if (queue.length) play(queue.shift());
  });

  /* listening game: hear an English word, tap its meaning */
  var cards = [].slice.call(document.querySelectorAll('.pv-word')).filter(function (c) { return c.querySelector('.pv-say'); });
  var gPlay = document.getElementById('g-play');
  if (gPlay && cards.length >= 4) {
    var ROUNDS = Math.min(10, cards.length), round = 0, score = 0, answer = null, order = [];
    var opts = document.getElementById('g-opts'), msg = document.getElementById('g-msg');
    function shuffle(a) { for (var i = a.length - 1; i > 0; i--) { var j = Math.floor(Math.random() * (i + 1)); var t = a[i]; a[i] = a[j]; a[j] = t; } return a; }
    function hear() { if (answer) play(answer.querySelector('.pv-say')); }
    function next() {
      if (round >= ROUNDS) {
        msg.textContent = 'Done! ' + score + ' / ' + ROUNDS + '  ' + (score >= ROUNDS - 1 ? '太厲害了！' : '再玩一次會更好！');
        gPlay.querySelector('span').innerHTML = 'Play again<em>再玩一次</em>'; answer = null; round = 0; return;
      }
      answer = order[round]; round++;
      document.getElementById('g-round').textContent = 'Round ' + round + ' / ' + ROUNDS;
      var pick = shuffle(cards.filter(function (c) { return c !== answer; })).slice(0, 3).concat([answer]);
      opts.innerHTML = '';
      shuffle(pick).forEach(function (c) {
        var b = document.createElement('button'); b.type = 'button'; b.textContent = c.dataset.zh;
        b.addEventListener('click', function () {
          if (!answer || opts.dataset.lock) return;
          opts.dataset.lock = 1;
          var ok = c === answer;
          b.classList.add(ok ? 'right' : 'wrong');
          if (!ok) [].forEach.call(opts.children, function (x) { if (x.textContent === answer.dataset.zh) x.classList.add('right'); });
          if (ok) score++;
          document.getElementById('g-score').textContent = '★ ' + score;
          msg.textContent = (ok ? 'Yes! ' : 'It is: ') + answer.dataset.en + ' — ' + answer.dataset.zh;
          setTimeout(function () { delete opts.dataset.lock; msg.textContent = ''; next(); hear(); }, ok ? 1100 : 1900);
        });
        opts.appendChild(b);
      });
    }
    gPlay.addEventListener('click', function () {
      if (!answer) {
        order = shuffle(cards.slice()).slice(0, ROUNDS); score = 0;
        document.getElementById('g-score').textContent = '★ 0';
        gPlay.querySelector('span').innerHTML = 'Listen again<em>再聽一次</em>';
        msg.textContent = ''; next();
      }
      hear();
    });
  } else if (gPlay) { document.getElementById('game').closest('section').remove(); }

  var io = 'IntersectionObserver' in window ? new IntersectionObserver(function (es) {
    es.forEach(function (x) { if (x.isIntersecting) { x.target.classList.add('in'); io.unobserve(x.target); } });
  }, { threshold: 0.08 }) : null;
  [].forEach.call(document.querySelectorAll('.rv'), function (el) { io ? io.observe(el) : el.classList.add('in'); });
  paint();
})();
"""


def line_rows(items, start=0, star=True, cls='pv-line'):
    out = []
    for i, x in enumerate(items):
        sid = f'{cls}{start + i}'
        st = ('<button type="button" class="pv-star" aria-label="I can say it" aria-pressed="false">★</button>'
              if star else '')
        out.append(f'<li class="{cls} rv" style="--i:{i}"{f" data-id={chr(34)}{sid}{chr(34)}" if star else ""}>'
                   f'{speak_btn(x["en"])}<div><b>{e(x["en"])}</b><em>{e(x["zh"])}</em></div>{st}</li>')
    return ''.join(out)


def page(deck):
    key, key2, bg, ink = THEMES.get(deck.get('theme'), THEMES['amber'])
    c = collect(deck)
    title = next(s for s in deck['slides'] if s['type'] == 'title')
    secs, n = [], 0

    def sec(en, zh, lead_en, lead_zh, body, extra=''):
        nonlocal n
        n += 1
        lead = f'<p class="pv-lead">{e(lead_en)}<em>{e(lead_zh)}</em></p>' if lead_en else ''
        secs.append(f'<section class="pv-sec rv" id="s{n}"><h2><span>{n}</span>{e(en)}<em>{e(zh)}</em></h2>'
                    f'{lead}{extra}{body}</section>')
        return n

    nav = []
    if c['intro']:
        s = c['intro']
        lines = [l for l in s['lines']]
        sec('Meet Teacher Dom', '認識 Dom 老師', 'This is how Dom will say hello in class. Listen and read along.',
            '這是 Dom 上課時的自我介紹。邊聽邊看。',
            f'<ul class="pv-lines pv-lines--plain">{line_rows(lines, star=False)}</ul>')
        nav.append(('Meet Dom', '認識 Dom', n))
    if c['idea']:
        i = c['idea']
        sec('The Big Idea', '今天的主題', '', '',
            f'<div class="pv-idea">{speak_btn(i["en"])}<div><h3>{e(i["head_en"])}<em>{e(i["head_zh"])}</em></h3>'
            f'<p>{e(i["en"])}</p><p class="zh">{e(i["zh"])}</p></div></div>')
        nav.append(('Big Idea', '主題', n))

    wid = 0
    blocks = []
    for g in c['groups']:
        cards = []
        for w in g['words']:
            cards.append(f'<li class="pv-word rv" style="--i:{len(cards)}" data-id="w{wid}" data-zh="{e(w["zh"])}" data-en="{e(w["en"])}">'
                         f'{speak_btn(w["en"], "pv-say pv-say--card")}<b>{e(w["en"])}</b><em>{e(w["zh"])}</em>'
                         '<button type="button" class="pv-star" aria-label="I can say it" aria-pressed="false">★</button></li>')
            wid += 1
        blocks.append(f'<h3 class="pv-group">{e(g["en"])}<em>{e(g["zh"])}</em><small>{len(g["words"])}</small></h3>'
                      f'<ul class="pv-words">{"".join(cards)}</ul>')
    if blocks:
        tools = ('<div class="pv-tools"><button type="button" class="pv-tool" id="all">▶ Play all<em>全部播放</em></button>'
                 '<button type="button" class="pv-tool" id="slow" aria-pressed="false">🐢 Slow<em>慢速</em></button></div>')
        sec('Words', '單字', f'{wid} words from the lesson. Tap a card to hear it, then say it three times.',
            f'上課會用到的 {wid} 個字。點卡片聽發音，跟著唸三次。', ''.join(blocks), tools)
        nav.append(('Words', '單字', n))
        sec('Listening Game', '聽力小遊戲', 'Listen to a word. Tap what it means. Ten rounds — how many can you get?',
            '聽一個英文字，點出它的中文意思。一共十題，你能答對幾題？',
            '''<div class="pv-game" id="game">
  <div class="pv-game-top"><span id="g-round">Round 1 / 10</span><span id="g-score">★ 0</span></div>
  <button type="button" class="pv-game-play" id="g-play"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 9v6h4l5 4V5L8 9H4z"/><path d="M16 9.2a4 4 0 0 1 0 5.6" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><path d="M18.6 6.6a7.6 7.6 0 0 1 0 10.8" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg><span>Start<em>開始</em></span></button>
  <div class="pv-game-opts" id="g-opts"></div>
  <p class="pv-game-msg" id="g-msg" aria-live="polite"></p>
</div>''')
        nav.append(('Game', '遊戲', n))

    if c['sentences']:
        sec('Sentences', '句子', 'You will say these with Dom. Listen, then repeat.', '上課時會跟 Dom 一起唸。先聽，再跟著唸。',
            f'<ul class="pv-lines">{line_rows(c["sentences"], cls="pv-line")}</ul>')
        nav.append(('Sentences', '句子', n))
    if c['read']:
        sec('Read and Listen', '聽一段短文', 'Tap “Play the story” and follow the words. Then try reading it yourself.',
            '按「播放整段」，眼睛跟著字走。然後自己試著唸一遍。',
            f'<ol class="pv-read">{line_rows(c["read"], star=False, cls="pv-rl")}</ol>',
            '<div class="pv-tools"><button type="button" class="pv-tool" id="story">▶ Play the story<em>播放整段</em></button></div>')
        nav.append(('Story', '短文', n))
    if c['standup']:
        s = c['standup']
        sec('Get Ready to Stand Up', '準備站起來', 'In class, Dom will read these. If it is true for you, stand up! Think about your answers now.',
            '上課時 Dom 會唸這幾句，如果說的是你，就站起來！現在先想想看。',
            f'<ul class="pv-lines pv-lines--plain">{line_rows(s["prompts"], star=False)}</ul>')
    if c['promise']:
        s = c['promise']
        sec(s['head_en'], s['head_zh'], 'The whole class will read this together. Practice it now so you can say it loud and clear!',
            '全班會一起大聲唸。先練習，到時候就能唸得又大聲又清楚！',
            f'<ul class="pv-lines">{line_rows(s["lines"], start=100, cls="pv-line")}</ul>')
    if c['think']:
        t = c['think']
        sec('Think About It', '先想一想', 'Dom will ask you this in class. You do not need to write anything — just think of your answer.',
            'Dom 上課時會問這個問題。不用寫下來，先想好你的答案就可以了。',
            f'<div class="pv-think"><p class="q">{e(t["prompt_en"])}<em>{e(t["prompt_zh"])}</em></p>'
            f'<div class="frame">{speak_btn(t["sentence_en"])}<div><b>{e(t["sentence_en"])}</b><em>{e(t["sentence_zh"])}</em></div></div></div>')

    navhtml = ''.join(f'<a href="#s{k}">{e(en)}<em>{e(zh)}</em></a>' for en, zh, k in nav)
    css = CSS.replace('KEY2', key2).replace('KEY', key).replace('BG', bg).replace('INK', ink)
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
<style>{css}</style>
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
</div><nav class="pv-nav wrap">{navhtml}</nav></div>

<main class="wrap">
{"".join(secs)}
<div class="pv-done rv"><b>See you in class!</b><em>我們教室見！</em></div>
</main>

<footer class="pv-foot wrap">Made for {e(deck["school_en"])} by <a href="/">My Culture Connect</a> 人師教育協會</footer>
<script>{JS.replace("SLUG", deck["slug"])}</script>
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
