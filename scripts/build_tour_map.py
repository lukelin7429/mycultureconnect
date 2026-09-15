#!/usr/bin/env python3
"""Build the "Where Dom has been" map section on dom-school-tour.html.

Inputs   data/changhua-map.json  — Changhua township outlines, already projected
                                   (regenerate with scripts/make_changhua_geo.py)
         data/tour-map.json      — one record per school: name, lat/lng, year, links
Output   the block between <!-- TOUR-MAP:START --> and <!-- TOUR-MAP:END -->
         inside dom-school-tour.html

Pin coordinates come from real lat/lng run through the same equirectangular
projection as the outlines, so a pin cannot drift off its township. Schools that
sit within a pin's width of each other (北斗國中/北斗國小 are 180 m apart) are
nudged apart by a relaxation pass and keep a hairline leader back to the true
spot.  Nothing here is hand-placed.
"""
import json, math, html, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'dom-school-tour.html')

MAP_PX   = 760      # reference css width of the map — sets how big a pin is in viewBox units
PIN_PX   = 26
MIN_SEP  = PIN_PX / MAP_PX * 1000 * 1.25
SPRING   = .10      # pull back toward the true location each iteration
LEADER   = 3.0      # draw a leader line once a pin has moved this far

YEARS = [
    ('115', '115 · 2026–2027', '115 學年度'),
    ('114', '114 · 2025–2026', '114 學年度'),
    ('earlier', 'Earlier', '更早的到訪'),
]
# label nudges in viewBox units, for townships whose centroid sits badly
NUDGE = {}


def load():
    with open(os.path.join(ROOT, 'data', 'changhua-map.json'), encoding='utf-8') as f:
        geo = json.load(f)
    with open(os.path.join(ROOT, 'data', 'tour-map.json'), encoding='utf-8') as f:
        schools = json.load(f)['schools']
    return geo, schools


def project(geo, lng, lat):
    p = geo['projection']
    x = (lng - p['minLon']) / (p['maxLon'] - p['minLon']) * p['width']
    y = (p['maxLat'] - lat) / (p['maxLat'] - p['minLat']) * p['height']
    return x, y


def relax(pts):
    """Push overlapping pins apart, springing each back toward its true point."""
    cur = [list(p) for p in pts]
    for _ in range(400):
        for i in range(len(cur)):
            for j in range(i + 1, len(cur)):
                dx, dy = cur[j][0] - cur[i][0], cur[j][1] - cur[i][1]
                d = math.hypot(dx, dy)
                if d >= MIN_SEP:
                    continue
                if d < 1e-6:
                    dx, dy, d = 1.0, 0.0, 1.0
                push = (MIN_SEP - d) / 2
                ux, uy = dx / d, dy / d
                cur[i][0] -= ux * push; cur[i][1] -= uy * push
                cur[j][0] += ux * push; cur[j][1] += uy * push
        for k, (ax, ay) in enumerate(pts):          # spring home
            cur[k][0] += (ax - cur[k][0]) * SPRING
            cur[k][1] += (ay - cur[k][1]) * SPRING
    return cur


def parse_path(d):
    """Our own output: 'M x y L x y ... Z' repeated. Read it back as rings."""
    rings = []
    for chunk in d.split('M')[1:]:
        pts = [tuple(float(v) for v in pair.split())
               for pair in chunk.rstrip('Z').split('L') if pair.strip()]
        if len(pts) > 2:
            rings.append(pts)
    return rings


def inside(x, y, rings):
    hit = False
    for r in rings:
        for i in range(len(r)):
            x1, y1 = r[i]; x2, y2 = r[(i + 1) % len(r)]
            if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
                hit = not hit
    return hit


def edge_dist(x, y, rings):
    best = 1e9
    for r in rings:
        for i in range(len(r)):
            x1, y1 = r[i]; x2, y2 = r[(i + 1) % len(r)]
            dx, dy = x2 - x1, y2 - y1
            L2 = dx * dx + dy * dy
            t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((x - x1) * dx + (y - y1) * dy) / L2))
            best = min(best, math.hypot(x - x1 - t * dx, y - y1 - t * dy))
    return best


def label_spot(rings, pins, fallback):
    """Roomiest interior point that also keeps clear of the pins sitting on it."""
    xs = [p[0] for r in rings for p in r]; ys = [p[1] for r in rings for p in r]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    best, score = fallback, -1e9
    for gx in range(1, 40):
        x = x0 + (x1 - x0) * gx / 40
        for gy in range(1, 40):
            y = y0 + (y1 - y0) * gy / 40
            if not inside(x, y, rings):
                continue
            e = edge_dist(x, y, rings)
            if e < 14:
                continue
            near = min((math.hypot(x - px, y - py) for px, py in pins), default=999)
            v = e + .85 * min(near, 85)
            if v > score:
                best, score = (x, y), v
    return best


def deck_chip(d):
    """Short chip label: the SDG number when there is one, else a trimmed title."""
    m = (re.search(r'SDG\s*([\d][\d·]*)', d['title_en'])
         or re.search(r'SDG\s*([\d][\d·]*)', d['title']))
    if m:
        return 'SDG ' + m.group(1)
    base = re.sub(r'\s*\(.*?\)', '', d['title_en']).strip()
    trimmed = re.sub(r'\s+Education$', '', base)
    if len(trimmed) >= 8:                      # "Character", not "Eco"
        base = trimmed
    return base if len(base) <= 25 else base[:24].rstrip() + '…'


def esc(s):
    return html.escape(s or '', quote=True)


def build():
    geo, schools = load()
    p = geo['projection']
    W, H = p['width'], p['height']

    anchors = [project(geo, s['lng'], s['lat']) for s in schools]
    placed = relax(anchors)

    visited_towns = {s['town_zh'] for s in schools}
    counts = {y: sum(1 for s in schools if s['year'] == y) for y, _, _ in YEARS}

    # ---------- svg: townships, county outline, labels, leaders ----------
    towns = []
    for t in geo['townships']:
        on = ' is-on' if t['zh'] in visited_towns else ''
        towns.append(f'<path class="tm-town{on}" d="{t["d"]}"><title>{esc(t["en"])} {esc(t["zh"])}</title></path>')

    labels = []
    for t in geo['townships']:
        if t['zh'] not in visited_towns:
            continue
        x, y = label_spot(parse_path(t['d']), placed, (t['lx'], t['ly']))
        dx, dy = NUDGE.get(t['zh'], (0, 0))
        x, y = x + dx, y + dy
        labels.append(
            f'<text class="tm-lab" x="{x:.1f}" y="{y:.1f}">'
            f'<tspan x="{x:.1f}" dy="-5">{esc(t["en"])}</tspan>'
            f'<tspan class="zh" x="{x:.1f}" dy="13">{esc(t["zh"])}</tspan></text>')

    leaders = []
    for (ax, ay), (px, py) in zip(anchors, placed):
        if math.hypot(px - ax, py - ay) < LEADER:
            continue
        leaders.append(f'<line class="tm-leader" x1="{px:.1f}" y1="{py:.1f}" x2="{ax:.1f}" y2="{ay:.1f}"/>'
                       f'<circle class="tm-anchor" cx="{ax:.1f}" cy="{ay:.1f}" r="3.2"/>')

    # ---------- pins + list, in visit order ----------
    pins, rows = [], []
    for i, (s, (px, py)) in enumerate(zip(schools, placed)):
        left, top = px / W * 100, py / H * 100
        side = ' is-l' if left < 26 else (' is-r' if left > 74 else '')
        below = ' is-below' if top < 17 else ''
        kind = 'upcoming' if s.get('status') == 'upcoming' else s['year']
        when = ' · '.join(s['dates']) if s['dates'] else esc(s.get('note_en', ''))
        year_label = next(z for y, _, z in YEARS if y == s['year'])

        bits = []
        if s.get('decks'):
            n = len(s['decks'])
            bits.append(f'📑 {n} deck{"s" if n > 1 else ""} 簡報')
        if s.get('visit'):
            bits.append('🗓 Itinerary 行程')
        if s.get('voices'):
            bits.append('🎙 Principal 校長專訪')
        if s.get('news'):
            bits.append('📹 Campus news 校園新聞')
        if s.get('status') == 'upcoming':
            bits.insert(0, '⏳ Upcoming 即將前往')

        aria = f"{s['en']} {s['zh']}, {s['town_en']} {s['town_zh']}" + (f", {when}" if when else '')
        pins.append(
            f'<button class="tm-pin tm-pin--{kind}{side}{below}" type="button" '
            f'style="--x:{left:.3f}%;--y:{top:.3f}%;--i:{i}" '
            f'data-year="{s["year"]}" data-i="{i}" aria-label="{esc(aria)}">'
            f'<span class="tm-dot" aria-hidden="true"></span>'
            f'<span class="tm-card" aria-hidden="true">'
            f'<span class="tm-c-en">{esc(s["en"])}</span>'
            f'<span class="tm-c-zh">{esc(s["zh"])}</span>'
            f'<span class="tm-c-town">{esc(s["town_en"])} {esc(s["town_zh"])}</span>'
            + (f'<span class="tm-c-when">{esc(when)}'
               f'<span class="tm-c-year">{esc(year_label)}</span></span>' if when else '')
            + (f'<span class="tm-c-bits">{esc(" · ".join(bits))}</span>' if bits else '')
            + '</span></button>')

        chips = [deck_chip(d) for d in s.get('decks', [])]
        dupes = {c for c in chips if chips.count(c) > 1}   # two SDG 14 decks at one school
        for n, c in enumerate(chips):
            q = re.search(r'\(([^)\s]+)', s['decks'][n]['title_en']) if c in dupes else None
            if q:
                chips[n] = f'{c} · {q.group(1)}'
        links = []
        for d, c in zip(s.get('decks', []), chips):
            links.append(f'<a href="slides/{esc(d["slug"])}/" '
                         f'title="{esc(d["title_en"])} · {esc(d["title"])}">📑 {esc(c)}</a>')
        if s.get('visit'):
            links.append(f'<a href="visits/{esc(s["visit"])}/">🗓 Itinerary</a>')
        if s.get('news'):
            links.append(f'<button class="tm-jump" type="button" data-school="{esc(s["en"])}">📹 Video</button>')

        rows.append(
            f'<li class="tm-row tm-row--{kind}" data-year="{s["year"]}" data-i="{i}">'
            f'<button class="tm-row-btn" type="button">'
            f'<span class="tm-row-dot" aria-hidden="true"></span>'
            f'<span class="tm-row-main">'
            f'<span class="tm-r-en">{esc(s["en"])}</span>'
            f'<span class="tm-r-zh">{esc(s["zh"])}</span>'
            f'<span class="tm-r-meta">{esc(s["town_en"])} {esc(s["town_zh"])}'
            + (f' · {esc(when)}' if when else '') + '</span></span></button>'
            + (f'<span class="tm-row-links">{"".join(links)}</span>' if links else '')
            + '</li>')

    switch = ''.join(
        f'<button class="vlib-tab{" is-on" if i == 0 else ""}" role="tab" '
        f'aria-selected="{"true" if i == 0 else "false"}" data-y="{y}">'
        f'<span class="ico" aria-hidden="true">{ico}</span>'
        f'<span class="en">{en}</span><span class="en-short">{short}</span>'
        f'<span class="zh">{zh}</span><span class="n">{n}</span></button>'
        for i, (y, en, zh, ico, short, n) in enumerate([
            ('all', 'All', '全部', '🗺', 'All', len(schools)),
            ('115', '115', '學年度 2026–27', '📍', '115', counts['115']),
            ('114', '114', '學年度 2025–26', '🗂', '114', counts['114']),
            ('earlier', 'Earlier', '更早的到訪', '🕰', 'Earlier', counts['earlier']),
        ]))

    stats = [(len(schools), 'Campuses', '所學校'),
             (len(visited_towns), 'Townships', '個鄉鎮市'),
             (len({d['slug'] for s in schools for d in s.get('decks', [])}), 'Slide decks', '套簡報')]

    return render(
        viewbox=f'0 0 {W:.0f} {H}',
        towns=''.join(towns), outline=''.join(
            f'<path class="tm-outline" d="{d}"/>' for d in geo['outline']),
        labels=''.join(labels), leaders=''.join(leaders),
        pins=''.join(pins), rows=''.join(rows), switch=switch,
        n_schools=len(schools), n_towns=len(visited_towns),
        stats=''.join(f'<div class="tm-stat"><b>{n}</b><span>{en}</span><i>{zh}</i></div>'
                      for n, en, zh in stats),
    )


def render(**kw):
    tpl = open(os.path.join(ROOT, 'scripts', 'tour_map_template.html'), encoding='utf-8').read()
    for k, v in kw.items():
        tpl = tpl.replace('{{%s}}' % k, str(v))
    left = re.findall(r'\{\{(\w+)\}\}', tpl)
    if left:
        raise SystemExit('template placeholder never filled: ' + ', '.join(sorted(set(left))))
    return tpl


def main():
    block = '<!-- TOUR-MAP:START -->\n' + build() + '\n<!-- TOUR-MAP:END -->'
    page = open(PAGE, encoding='utf-8').read()
    if '<!-- TOUR-MAP:START -->' in page:
        page = re.sub(r'<!-- TOUR-MAP:START -->.*?<!-- TOUR-MAP:END -->', lambda m: block,
                      page, flags=re.S)
    else:                                   # first run — drop it in front of the video library
        marker = '<section class="soft vlib" id="videos">'
        page = page.replace(marker, block + '\n\n' + marker, 1)
    open(PAGE, 'w', encoding='utf-8').write(page)
    print(f'dom-school-tour.html updated — map block {len(block) // 1024} KB')


if __name__ == '__main__':
    main()
