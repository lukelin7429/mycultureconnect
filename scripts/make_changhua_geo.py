#!/usr/bin/env python3
"""One-off: turn national township boundaries into data/changhua-map.json.

Only needs re-running if the township outlines themselves have to change — the
committed JSON is what the site uses.

    curl -o twTown.geo.json \
      https://raw.githubusercontent.com/g0v/twgeojson/master/json/twTown1982.geo.json
    python3 scripts/make_changhua_geo.py        # reads ./twTown.geo.json

What it does: keeps the 26 Changhua townships, rebuilds the county outline from
the edges that belong to exactly one township, simplifies everything
(Douglas-Peucker, 0.8 px on a 1000-wide map: 17,406 points -> ~3,000) and
projects it equirectangularly at the county's mid-latitude. scripts/
build_tour_map.py runs school lat/lng through that same projection, which is why
the pins land where the schools actually are.

Source: g0v/twgeojson, from the Ministry of the Interior's township boundaries.
員林鎮 is relabelled 員林市 (upgraded to a city in 2015).
"""
import json, math, os

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   'data', 'changhua-map.json')

TOWN_EN = {
 "彰化市":"Changhua City","員林市":"Yuanlin City","和美鎮":"Hemei","鹿港鎮":"Lukang",
 "溪湖鎮":"Xihu","二林鎮":"Erlin","田中鎮":"Tianzhong","北斗鎮":"Beidou",
 "花壇鄉":"Huatan","芬園鄉":"Fenyuan","大村鄉":"Dacun","永靖鄉":"Yongjing",
 "伸港鄉":"Shengang","線西鄉":"Xianxi","福興鄉":"Fuxing","秀水鄉":"Xiushui",
 "埔心鄉":"Puxin","埔鹽鄉":"Puyan","大城鄉":"Dacheng","芳苑鄉":"Fangyuan",
 "竹塘鄉":"Zhutang","社頭鄉":"Shetou","二水鄉":"Ershui","田尾鄉":"Tianwei",
 "埤頭鄉":"Pitou","溪州鄉":"Xizhou",
}
RENAME = {"員林鎮":"員林市"}          # upgraded to a city in 2015

geo = json.load(open('twTown.geo.json'))
feats = [f for f in geo['features'] if f['properties']['COUNTYNAME'] == '彰化縣']

def rings_of(g):
    return [g['coordinates']] if g['type'] == 'Polygon' else g['coordinates']

# ---------- county outline: keep only edges that belong to exactly one township ----------
def key(a, b):
    ra = (round(a[0], 7), round(a[1], 7)); rb = (round(b[0], 7), round(b[1], 7))
    return (ra, rb) if ra <= rb else (rb, ra)

count = {}
for f in feats:
    for poly in rings_of(f['geometry']):
        for ring in poly:
            for i in range(len(ring) - 1):
                count[key(ring[i], ring[i + 1])] = count.get(key(ring[i], ring[i + 1]), 0) + 1
border = [k for k, v in count.items() if v == 1]
print('boundary segments:', len(border), 'of', len(count))

adj = {}
for a, b in border:
    adj.setdefault(a, []).append(b); adj.setdefault(b, []).append(a)
seen, outline = set(), []
for a, b in border:
    if (a, b) in seen: continue
    ring = [a, b]; seen.add((a, b)); seen.add((b, a))
    while True:
        cur, prev = ring[-1], ring[-2]
        nxt = [p for p in adj.get(cur, []) if p != prev and (cur, p) not in seen]
        if not nxt: break
        n = nxt[0]; seen.add((cur, n)); seen.add((n, cur)); ring.append(n)
        if n == ring[0]: break
    if len(ring) > 8: outline.append([list(p) for p in ring])
outline.sort(key=len, reverse=True)
print('outline rings:', [len(r) for r in outline[:6]])

# ---------- projection ----------
xs = [p[0] for f in feats for poly in rings_of(f['geometry']) for r in poly for p in r]
ys = [p[1] for f in feats for poly in rings_of(f['geometry']) for r in poly for p in r]
minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
K = math.cos(math.radians((miny + maxy) / 2))
W = 1000.0
H = round(W * (maxy - miny) / ((maxx - minx) * K), 2)
def proj(lon, lat):
    return ((lon - minx) * K / ((maxx - minx) * K) * W, (maxy - lat) / (maxy - miny) * H)

# ---------- Douglas–Peucker in projected px ----------
def dp(pts, tol):
    if len(pts) < 3: return pts
    keep = [False] * len(pts); keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        i, j = stack.pop()
        if j <= i + 1: continue
        (x1, y1), (x2, y2) = pts[i], pts[j]
        dx, dy = x2 - x1, y2 - y1
        L = math.hypot(dx, dy) or 1e-12
        best, bi = -1, -1
        degenerate = L < 1e-9        # closed ring: first point == last point
        for m in range(i + 1, j):
            x, y = pts[m]
            d = (math.hypot(x - x1, y - y1) if degenerate
                 else abs(dy * x - dx * y + x2 * y1 - y2 * x1) / L)
            if d > best: best, bi = d, m
        if best > tol:
            keep[bi] = True; stack += [(i, bi), (bi, j)]
    return [p for p, k in zip(pts, keep) if k]

TOL = 0.8          # px on a 1000-wide map
def path_of(rings, tol=TOL, minpts=4):
    out = []
    for ring in rings:
        pts = dp([proj(*p) for p in ring], tol)
        if len(pts) < minpts: continue
        out.append('M' + 'L'.join(f'{x:.1f} {y:.1f}' for x, y in pts) + 'Z')
    return ''.join(out)

towns, total_before, total_after = [], 0, 0
for f in feats:
    name = RENAME.get(f['properties']['TOWNNAME'], f['properties']['TOWNNAME'])
    rings = [r for poly in rings_of(f['geometry']) for r in poly]
    total_before += sum(len(r) for r in rings)
    d = path_of(rings)
    total_after += d.count('L') + d.count('M')
    # label anchor: centroid of the largest ring, pulled to a point inside it
    big = max(rings, key=len)
    px = [proj(*p) for p in big]
    cx = sum(p[0] for p in px) / len(px); cy = sum(p[1] for p in px) / len(px)
    towns.append({'zh': name, 'en': TOWN_EN[name], 'd': d,
                  'lx': round(cx, 1), 'ly': round(cy, 1)})

out = {
  'projection': {'minLon': minx, 'maxLon': maxx, 'minLat': miny, 'maxLat': maxy,
                 'k': K, 'width': W, 'height': H},
  'outline': [path_of([r], tol=TOL) for r in outline[:4]],
  'townships': sorted(towns, key=lambda t: t['zh']),
}
json.dump(out, open(OUT, 'w'), ensure_ascii=False, separators=(',', ':'))
print(f'viewBox 0 0 {W:.0f} {H}   points {total_before} -> {total_after}')
print('data/changhua-map.json', os.path.getsize(OUT) // 1024, 'KB')
