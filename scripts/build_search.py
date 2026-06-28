#!/usr/bin/env python3
"""Build the site-wide search index (/search.json) and wire the search box
into every HTML page (search.css + search.js). Idempotent — re-run after
adding or changing pages:  python3 scripts/build_search.py
"""
import os, re, json, html as _html

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP_DIRS = {'.git', 'assets', 'scripts', 'node_modules', 'vendor', '_site',
             '_layouts', '_includes', 'apps-script', 'data'}

CSS_LINK = '<link rel="stylesheet" href="/assets/css/search.css">'
JS_TAG   = '<script defer src="/assets/js/search.js"></script>'

TAG_RE    = re.compile(r'<[^>]+>')
SCRIPT_RE = re.compile(r'<(script|style|svg)\b.*?</\1>', re.S | re.I)
BLOCK_RE  = re.compile(r'<(header|footer|nav)\b.*?</\1>', re.S | re.I)
WS_RE     = re.compile(r'\s+')
TITLE_RE  = re.compile(r'<title>(.*?)</title>', re.S | re.I)
DESC_RE   = re.compile(r'<meta[^>]+name=["\']description["\'][^>]*content=["\'](.*?)["\']', re.S | re.I)
BODY_RE   = re.compile(r'<body\b[^>]*>(.*?)</body>', re.S | re.I)


def clean(text, limit=300):
    text = _html.unescape(WS_RE.sub(' ', text)).strip()
    return text[:limit].rstrip() + ('…' if len(text) > limit else '')


def strip_title_suffix(t):
    t = _html.unescape(t).strip()
    for sep in ('｜', ' — ', ' | ', ' · ', ' – ', '—', '–'):
        if sep in t:
            t = t.split(sep)[0].strip()
            break
    return t


def url_for(rel):
    rel = rel.replace(os.sep, '/')
    if rel == 'index.html':
        return '/'
    if rel.endswith('/index.html'):
        return '/' + rel[:-len('index.html')]
    return '/' + rel


def body_text(raw):
    m = BODY_RE.search(raw)
    chunk = m.group(1) if m else raw
    chunk = SCRIPT_RE.sub(' ', chunk)
    chunk = BLOCK_RE.sub(' ', chunk)
    return TAG_RE.sub(' ', chunk)


def walk_html():
    for dp, dns, fns in os.walk(ROOT):
        dns[:] = [d for d in dns if d not in SKIP_DIRS and not d.startswith('.')]
        for fn in fns:
            if fn.endswith('.html'):
                yield os.path.join(dp, fn)


entries = []
for full in walk_html():
    rel = os.path.relpath(full, ROOT)
    raw = open(full, encoding='utf-8').read()
    mt = TITLE_RE.search(raw)
    title = strip_title_suffix(mt.group(1)) if mt else None
    if not title:
        continue
    md = DESC_RE.search(raw)
    desc = (md.group(1) + ' ') if md else ''
    entries.append({'title': title, 'url': url_for(rel),
                    'body': clean(desc + body_text(raw))})

seen, uniq = set(), []
for e in sorted(entries, key=lambda e: e['url']):
    if e['url'] in seen:
        continue
    seen.add(e['url'])
    uniq.append(e)

with open(os.path.join(ROOT, 'search.json'), 'w', encoding='utf-8') as f:
    json.dump(uniq, f, ensure_ascii=False, indent=0, separators=(',', ':'))
    f.write('\n')
print('search.json: %d pages indexed' % len(uniq))

injected = 0
for full in walk_html():
    raw = open(full, encoding='utf-8').read()
    new = raw
    if CSS_LINK not in new and '</head>' in new:
        new = new.replace('</head>', '  ' + CSS_LINK + '\n</head>', 1)
    if JS_TAG not in new and '</body>' in new:
        new = new.replace('</body>', '  ' + JS_TAG + '\n</body>', 1)
    if new != raw:
        open(full, 'w', encoding='utf-8').write(new)
        injected += 1
print('search assets wired into %d pages' % injected)
