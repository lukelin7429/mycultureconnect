#!/usr/bin/env python3
"""Build the "Dom School Visits 訪校行程表" page — the one place Luke and Dom look for
every school's run-of-day link.

    python3 scripts/build_visit_index.py /path/to/dom-visit-schedules.html

The page is a claude.ai Artifact, not part of this site, so this only writes the file;
publish it afterwards to the same Artifact URL (see the vault note
"00 — Dom 訪校簡報總覽" for the link). Everything comes from data/visits/*.json and
data/tour-map.json, so adding a visit page and re-running this is all an update takes.
Lunch never appears on this page.
"""
import os, re, sys, json, glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = 'https://mycultureconnect.org'


def visits():
    with open(os.path.join(ROOT, 'data', 'tour-map.json'), encoding='utf-8') as f:
        towns = {s['zh']: (s['town_zh'], s['town_en']) for s in json.load(f)['schools']}
    out = []
    for path in sorted(glob.glob(os.path.join(ROOT, 'data', 'visits', '*.json'))):
        with open(path, encoding='utf-8') as f:
            v = json.load(f)
        items = [i for i in v['items'] if i['label_en'].strip().lower() != 'lunch']
        times = re.findall(r'\d\d:\d\d', ' '.join(i['time'] for i in items))
        town_zh, town_en = towns[v['school']]
        out.append({
            'id': v['slug'], 'date': v['date'].replace('.', '-'),
            'school': v['school'], 'school_en': v['school_en'],
            'town': town_zh, 'town_en': town_en,
            'span': f'{times[0]}–{times[-1]}', 'url': f"{BASE}/visits/{v['slug']}/",
            'items': [{'t': i['time'].replace(' – ', '–'), 'c': i.get('class', ''),
                       'en': i['label_en'], 'zh': i['label_zh'],
                       'deck': f"{BASE}/slides/{i['deck']}/" if i.get('deck') else ''} for i in items],
        })
    return out


def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    with open(os.path.join(ROOT, 'scripts', 'visit_index_template.html'), encoding='utf-8') as f:
        tpl = f.read()
    marker = '/*VISITS*/[]'
    if tpl.count(marker) != 1:
        raise SystemExit('template must contain exactly one ' + marker)
    data = visits()
    # "</" inside a <script> block would end it early
    page = tpl.replace(marker, json.dumps(data, ensure_ascii=False, indent=1).replace('</', '<\\/'))
    with open(sys.argv[1], 'w', encoding='utf-8') as f:
        f.write(page)
    print(f'{len(data)} visits -> {sys.argv[1]}')


if __name__ == '__main__':
    main()
