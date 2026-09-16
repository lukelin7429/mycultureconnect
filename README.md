# My Culture Connect — website

Static website for **My Culture Connect (人師教育協會)**, a Taiwan-based nonprofit (est. 2009)
serving rural Changhua through free English education, TEFL/TESOL practicum, and school partnerships.

Rebuilt from the previous Wix site to plain HTML/CSS/JS for GitHub Pages hosting.
Design mirrors the original: Noticia Text + Questrial + Avenir, brand orange `#F58220`.

## Pages
- `index.html` — Home
- `team.html` — Founder, Advocacy Board, Teachers
- `partners.html` — Partner schools & organizations
- `opportunities.html` — Practicum & volunteer opportunities
- `programs.html` — Dom Jones Taiwan school tour (videos)
- `contact.html` — Contact info & form

## Build scripts

Everything generated lives under `data/` as JSON — edit the JSON, re-run the
script, never hand-edit the generated HTML.

| Command | Reads | Writes |
|---|---|---|
| `python3 scripts/build_decks.py` | `data/decks/*.json`, `data/decks-114.json`, `data/visits/*.json` | `slides/`, `visits/` |
| `python3 scripts/export_decks.py` | `slides/<slug>/index.html` | `slides/<slug>/<slug>.pdf` + `.pptx` — offline copies for the classroom PC |
| `python3 scripts/build_tour_map.py` | `data/tour-map.json`, `data/changhua-map.json` | the map section in `dom-school-tour.html` |
| `python3 scripts/build_search.py` | every site page | `search.json` + wires the search box in |
| `python3 scripts/make_changhua_geo.py` | a national township GeoJSON (see its docstring) | `data/changhua-map.json` — one-off |

**Adding a school to the tour map:** append a record to `data/tour-map.json`
(`en`, `zh`, `town_zh`, `town_en`, `lat`, `lng`, `dates`, `year`, `status`, and
optional `decks` / `visit` / `news` / `voices`) and re-run `build_tour_map.py`.
Coordinates come from OpenStreetMap; every pin is checked to fall inside the
township it claims.

**Offline copies:** classroom displays vary and a browser is one more thing that
can fail before an assembly, so every interactive deck also ships as a PDF and a
PPTX, linked from two buttons under the deck. Run `build_decks.py` first, then
`export_decks.py` (it skips decks already up to date; `--force` rebuilds all).
Slides with a hidden answer are exported twice — question page, then answer page
— so a click-to-reveal never turns into a printed answer.

The assembly decks under `slides/` and the itineraries under `visits/` are
projection pages: no site header, no footer, no search box. `build_search.py`
skips them on purpose.

## Notes
- Images in `assets/img/` were converted from HEIC/JPG and optimized for web.
- Contact form currently opens the visitor's mail app (mailto). Can be swapped to
  an Apps Script → Google Sheet endpoint later for direct collection.
- Custom domain (mycultureconnect.org) is **not** wired yet — review on the
  `lukelin7429.github.io/mycultureconnect/` URL first.
